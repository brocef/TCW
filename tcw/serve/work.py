"""Work routes: the project, the board and one item.

Each read is one of the backend's operations, and each item is the CLI's own
item record (`tcw/work/record.py`), inside an envelope that is the API's.

Who owns the item record is a viewer rule inferred from one declared backend
fact: when the first stage with a document is kept by the backend
(`external_stages`), the whole record (request, comments, stage and
properties) is the backend's and is read-only here. Then a backend read that
fails because the backend cannot answer degrades to its own field, so the
files on disk stay usable; otherwise every failure is an error.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timezone
from http import HTTPStatus
from pathlib import Path
from typing import Any, Callable

from tcw.errors import BackendError, NotFound, Unreachable
from tcw.serve import files as item_files
from tcw.serve.server import Request, not_found, route
from tcw.store.base import CAP_LIFECYCLES, CAP_PRIORITIES, CAP_STATUSES
from tcw.work.backend import Query
from tcw.work.config import WorkConfig
from tcw.work.layout import Layout
from tcw.work.model import (
    PRIORITIES, SIZES, STAGES, Item, Slug, inbox_stage, start_stage,
)
from tcw.work.open import read_work_config, work_path
from tcw.work.record import item_record, readable

LOCAL, BACKEND = "local", "backend"
# At most this many comments per item page; the page says when it got them all.
COMMENT_LIMIT = 200
# The properties a create form may offer, in the form's order.
SIZE_PROPERTIES = ("priority", "effort", "complexity")
# What a backend raises when it cannot answer at all, rather than refusing.
CANNOT_ANSWER = (Unreachable, BackendError)


@dataclass
class WorkContext:
    """One request's view of the project: its configuration and backend,
    read again for every request so a change made while serving is seen."""

    root: Path
    config: WorkConfig
    backend: Any
    layout: Layout

    @property
    def owner(self) -> str:
        return BACKEND if start_stage() in self.backend.external_stages else LOCAL

    def slug(self, folder: str) -> Slug:
        return Slug(self.backend.project, folder)


def context(request: Request) -> WorkContext:
    root = request.root
    config = read_work_config(root)
    backend = request.services.open_backend(root)
    layout = Layout(work_path(root), config.enabled, backend.external_stages)
    return WorkContext(root, config, backend, layout)


def unavailable(error: Exception) -> dict[str, str]:
    return {"unavailable": str(error)}


def degrading(ctx: WorkContext, read: Callable[[], Any],
              shape: Callable[[Any], Any] = lambda v: v) -> Any:
    """`read()`'s value shaped, or, when the backend owns the record and
    cannot answer, `{"unavailable": <its message>}`."""
    try:
        value = read()
    except CANNOT_ANSWER as error:
        if ctx.owner != BACKEND or isinstance(error, NotFound):
            raise
        return unavailable(error)
    return shape(value)


def people(request: Request, ctx: WorkContext, ids) -> dict[str, str]:
    """Display names for the people a response mentions, when the backend
    owns the record (a person is then an account ID). An ID with no name, or
    a name that cannot be read now, is left out: the page shows the ID."""
    if ctx.owner != BACKEND:
        return {}
    names: dict[str, str] = {}
    for person in sorted({i for i in ids if isinstance(i, str) and i}):
        try:
            name = request.services.user_name(ctx.backend, person)
        except Exception:
            continue
        if name:
            names[person] = name
    return names


def _stamp(at) -> str:
    return at.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# -- the project --------------------------------------------------------------------------


def _stage_row(row, ctx: WorkContext) -> dict[str, Any]:
    return {"name": row.name, "kind": row.kind, "artifact": row.artifact,
            "verdict": row.verdict, "onReject": row.on_reject,
            "external": row.name in ctx.backend.external_stages,
            "completion": row.completion, "discard": row.discard}


def _axes(root: Path) -> dict[str, bool]:
    """Which axes this project keeps: a store whose folder is there."""
    from tcw.store.fs import FsCapabilitiesStore, FsTaxonomyStore, WorkLocation
    kept = {}
    for name, opener in (("taxonomy", FsTaxonomyStore.open),
                         ("capabilities", FsCapabilitiesStore.open),
                         ("work", WorkLocation.open)):
        try:
            kept[name] = Path(opener(root).root).is_dir()
        except ValueError:
            kept[name] = False
    return kept


def _projects(root: Path) -> list[dict[str, Any]]:
    """The projects this one is connected to, as `tcw projects list` names
    them, for the create form's target."""
    from tcw.projects_cli import connected
    return [{"id": row["id"], "relation": row["relation"], "present": row["present"],
             "upstream": row["relation"] == "upstream"}
            for row in connected(root) if row["relation"] != "current"]


def project(request: Request):
    ctx = context(request)
    try:
        user = ctx.backend.current_user()
    except Exception:
        user = None
    if ctx.owner == BACKEND:
        try:
            fields: Any = list(request.services.create_fields(ctx.backend))
        except CANNOT_ANSWER as error:
            fields = unavailable(error)
    else:
        fields = list(SIZE_PROPERTIES)
    return HTTPStatus.OK, {
        "id": ctx.backend.project,
        "recordOwner": ctx.owner,
        "stages": [_stage_row(row, ctx) for row in STAGES
                   if row.name in ctx.config.enabled],
        "inboxStage": inbox_stage(),
        "startStage": start_stage(),
        "inboxItems": bool(ctx.backend.inbox_items),
        "tags": list(ctx.config.tags),
        "scales": {"priority": list(PRIORITIES), "size": list(SIZES)},
        "capabilityScales": {"status": sorted(CAP_STATUSES),
                             "priority": sorted(CAP_PRIORITIES),
                             "lifecycle": sorted(CAP_LIFECYCLES)},
        "createFields": fields,
        "user": user,
        "people": people(request, ctx, [user]),
        "projects": _projects(ctx.root),
        "axes": _axes(ctx.root),
    }


# -- the board ---------------------------------------------------------------------------


def _tags(request: Request) -> frozenset[str] | None:
    given = [t for t in request.query.get("tag", []) if t]
    return frozenset(given) if given else None


def board(request: Request):
    """`items` is exactly what `tcw work list [--all] [--tag …] --json` prints
    under `items`. Without tags the board is one backend read: the default
    board is taken from the full list by the model's own rule, and `blocks`
    and `children` come from that same read."""
    ctx = context(request)
    tags = _tags(request)
    every = request.query.get("all", [""])[-1] in ("1", "true")
    try:
        if tags is None:
            siblings = ctx.backend.list(Query(all=True))
            default = Query()
            items = [i for i in siblings if every or default.matches(i)]
        else:
            items = ctx.backend.list(Query(all=every, tags=tags))
            siblings, _ = readable(ctx.backend)
    except CANNOT_ANSWER as error:
        if ctx.owner != BACKEND or isinstance(error, NotFound):
            raise
        return HTTPStatus.OK, {
            "items": [{"slug": str(ctx.slug(folder)),
                       "path": str(ctx.layout.item_dir(ctx.slug(folder)))}
                      for folder in ctx.layout.item_folders()],
            "people": {}, "fallback": True, "unavailable": str(error)}
    return HTTPStatus.OK, {
        "items": [item_record(i, siblings, ctx.layout) for i in items],
        "people": people(request, ctx, [i.assignee for i in items]),
        "fallback": False,
    }


# -- one item ------------------------------------------------------------------------------


def item_folder(ctx: WorkContext, name: str) -> str:
    """The item folder `name` names: one under the work path, or, for a name
    the backend knows another way (a Jira key), the folder it gives."""
    folders = ctx.layout.item_folders()
    if name in folders:
        return name
    found = ctx.backend.lookup(name)
    if found and found in folders:
        return found
    raise not_found(f"no work item {ctx.backend.project}/{name}")


def _comments(found) -> list[dict[str, Any]]:
    return [{"at": _stamp(c.at), "author": c.author, "text": c.text}
            for c in sorted(found, key=lambda c: c.at)]


def detail(request: Request):
    ctx = context(request)
    folder = item_folder(ctx, request.param(1))
    slug = ctx.slug(folder)
    item: Item | None = None
    mentioned: list[Any] = []

    def read_item():
        nonlocal item
        item = ctx.backend.read(folder)
        siblings, bad = readable(ctx.backend)
        return item_record(item, siblings, ctx.layout), bad

    record = degrading(ctx, read_item)
    warnings: list[str] = []
    if item is not None:
        record, warnings = record
        mentioned.append(item.assignee)
    answer: dict[str, Any] = {"folder": folder, "item": record}
    if start_stage() in ctx.backend.external_stages:
        answer["requestText"] = degrading(
            ctx, lambda: ctx.backend.read_request(folder))
    found: list = []

    def read_comments():
        found.extend(ctx.backend.read_comments(folder, COMMENT_LIMIT))
        return found

    answer["comments"] = degrading(ctx, read_comments, _comments)
    answer["commentsLimited"] = len(found) >= COMMENT_LIMIT
    mentioned += [c.author for c in found]
    answer["people"] = people(request, ctx, mentioned)
    answer["link"] = None
    if ctx.owner == BACKEND:
        try:
            label, url = request.services.ticket_link(ctx.backend, folder)
            answer["link"] = {"label": label, "url": url}
        except Exception:
            pass
    answer["files"] = item_files.listing(ctx, slug)
    answer["verdicts"] = item_files.verdicts(ctx, slug)
    answer["warnings"] = warnings
    return HTTPStatus.OK, answer


ONE = r"/([^/]+)"
ROUTES = [
    route("GET", r"/api/project", project),
    route("GET", r"/api/work", board),
    route("GET", r"/api/work" + ONE, detail),
]
