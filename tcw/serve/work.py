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

from dataclasses import dataclass, replace
from datetime import timezone
from http import HTTPStatus
from pathlib import Path
from typing import Any, Callable

from tcw.errors import BackendError, NotFound, TcwError, Unreachable
from tcw.ids import FullId, MalformedId, identity, sort_input
from tcw.serve import files as item_files
from tcw.serve.records import checked
from tcw.serve.server import (Request, Written, creates, not_found, read_only, route,
                              usage)
from tcw.store.base import (
    CAP_LIFECYCLES, CAP_PRIORITIES, CAP_STATUSES, StaleRevision, normalize_tag,
)
from tcw.validate import ValidationTarget
from tcw.work.backend import Query
from tcw.work.config import WorkConfig
from tcw.work.jira.backend import KEY
from tcw.work.layout import Layout
from tcw.work.model import (
    PRIORITIES, SIZES, STAGES, UNSET, Changes, Item, Slug, inbox_stage, start_stage,
)
from tcw.work.open import name_item, read_work_config, work_path
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


def item_folders(ctx: WorkContext) -> list[str]:
    """The item folders under the work path, by the backend's own rule for
    recognizing one; a folder anything else left there is not an item. Reads
    only the work path, so it answers while the backend cannot."""
    return [f for f in ctx.layout.item_folders() if ctx.backend.is_item_folder(f)]


def unavailable(error: Exception) -> dict[str, str]:
    return {"unavailable": str(error)}


def _registered_tags(ctx: WorkContext) -> "list[str] | dict[str, str]":
    """The project's tags, or, when a parent that is not here may set them or
    passes them with a problem, `{"unavailable": <why>}`, so the summary still
    answers (TCW-109 Design 3.4). `ctx.config.tags or []` is not a safe test:
    using the value raises."""
    from tcw.config import Withheld
    if isinstance(ctx.config.tags, Withheld):
        return unavailable(ctx.config.tags.error())
    return list(ctx.config.tags)


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
        "tags": _registered_tags(ctx),
        "scales": {"priority": list(PRIORITIES), "size": list(SIZES)},
        "capabilityScales": {"status": sorted(CAP_STATUSES),
                             "priority": sorted(CAP_PRIORITIES),
                             "lifecycle": sorted(CAP_LIFECYCLES)},
        "createFields": fields,
        "user": user,
        "people": people(request, ctx, [user]),
        "axes": _axes(ctx.root),
    }


# -- the board ---------------------------------------------------------------------------


def _tag(value: str) -> str:
    """A tag as the stores hold it. Normalized here, so a name that is not a
    tag is the request's fault (400), not the backend's (500)."""
    try:
        return normalize_tag(value)
    except ValueError:
        raise usage(f"{value!r} is not a tag") from None


def _tags(request: Request) -> frozenset[str] | None:
    given = [_tag(t) for t in request.query.get("tag", []) if t]
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
            "items": [{**identity(ctx.slug(folder)),
                       "path": str(ctx.layout.item_dir(ctx.slug(folder)))}
                      for folder in item_folders(ctx)],
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
    folders = item_folders(ctx)
    if name in folders:
        return name
    found = ctx.backend.lookup(name)
    if found and found in folders:
        return found
    raise not_found(f"no work item {Slug(ctx.backend.project, name)}")


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
        return item

    record = degrading(ctx, read_item)
    warnings: list[str] = []
    if item is not None:
        # `blocks` and `children` come from every other item; when those
        # cannot be read, the item still shows, and the page says why the
        # two lists may be short.
        siblings = degrading(ctx, lambda: readable(ctx.backend))
        if isinstance(siblings, dict):
            siblings, warnings = ([], []), [f"every other item ({siblings['unavailable']})"]
        else:
            warnings = siblings[1]
        record = item_record(item, siblings[0], ctx.layout)
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


# -- writes --------------------------------------------------------------------------------
#
# Every write to the item record is refused before any backend call when the
# backend owns the record: in that mode the viewer edits only the files.


def writable(ctx: WorkContext) -> None:
    if ctx.owner == BACKEND:
        raise read_only("this project's backend keeps the item's request, comments, "
                        "stage and properties; change them there")


SCALES = {"priority": PRIORITIES, "effort": SIZES, "complexity": SIZES}
SCALAR = ("title", "priority", "effort", "complexity", "assignee", "parent")
LISTED = {"tags": ("add_tags", "remove_tags"),
          "blocked-by": ("add_blocked_by", "remove_blocked_by")}


def _strings(value: Any, name: str) -> tuple[str, ...]:
    if value is None:
        return ()
    if not isinstance(value, list) or not all(isinstance(v, str) for v in value):
        raise usage(f"{name} must be a list of names")
    return tuple(value)


def parse_changes(sent: Any) -> Changes:
    """TCW-69's `Changes` from JSON: a scalar property present is set, and
    null clears it; `tags` and `blocked-by` each take `add` and `remove`."""
    if not isinstance(sent, dict):
        raise usage("changes must be an object")
    unknown = sorted(set(sent) - set(SCALAR) - set(LISTED))
    if unknown:
        raise usage(f"changes has unknown properties: {', '.join(unknown)}")
    values: dict[str, Any] = {}
    for name in SCALAR:
        if name in sent:
            value = sent[name]
            if value is not None and not isinstance(value, str):
                raise usage(f"{name} must be text or null")
            values[name] = None if value == "" and name != "title" else value
    if "title" in values and not (values["title"] or "").strip():
        raise usage("a title must not be empty")
    for name, scale in SCALES.items():
        if values.get(name) is not None and values[name] not in scale:
            raise usage(f"{name} must be one of {', '.join(scale)}; got {values[name]!r}")
    for name, (add, remove) in LISTED.items():
        if name in sent:
            pair = sent[name]
            if not isinstance(pair, dict) or set(pair) - {"add", "remove"}:
                raise usage(f"{name} takes add and remove lists")
            values[add] = _strings(pair.get("add"), f"{name}.add")
            values[remove] = _strings(pair.get("remove"), f"{name}.remove")
            if name == "tags":
                values[add] = tuple(_tag(t) for t in values[add])
                values[remove] = tuple(_tag(t) for t in values[remove])
    return Changes(**values)


def checked_reference(ctx: WorkContext, what: str, text: str
                      ) -> tuple[Slug, dict | None]:
    """The item a `parent` or `blocked-by` a write adds names, as the full
    identifier to store however it was typed (TCW-110 Design 3.3), and a
    warning when it is another project's item, which is kept unchecked here.
    An item of this project that is not here is refused."""
    slug = name_item(text, lambda: ctx.backend, ctx.root)
    if slug.project != ctx.backend.project:
        return slug, {"severity": "warning", "where": what,
                      "message": f"{slug} is in project '{slug.project}', which this "
                                 f"page does not check; make sure it exists"}
    if slug.folder not in item_folders(ctx):
        raise usage(f"{what}: {text} is not an item of this project")
    return slug, None


def references(ctx: WorkContext, changes: Changes) -> tuple[Changes, list[dict]]:
    """`changes` with each item it adds named by full identifier, and the
    warnings about the ones this page cannot check."""
    notes = []
    parent = changes.parent
    if parent is not UNSET and parent is not None:
        parent, note = checked_reference(ctx, "parent", parent)
        notes.append(note)
    blockers = []
    for blocker in changes.add_blocked_by:
        slug, note = checked_reference(ctx, "blocked-by", blocker)
        blockers.append(slug)
        notes.append(note)
    removed = tuple(name_item(t, lambda: ctx.backend, ctx.root)
                    for t in changes.remove_blocked_by)
    resolved = replace(changes, parent=parent, add_blocked_by=tuple(blockers),
                       remove_blocked_by=removed)
    return resolved, [n for n in notes if n]


def _changed(changes: Changes) -> list[str]:
    names = [n for n in SCALAR if getattr(changes, n) is not UNSET]
    return names + [n for n, (add, remove) in LISTED.items()
                    if getattr(changes, add) or getattr(changes, remove)]


def _same(loaded: Any, now: Any) -> bool:
    if isinstance(now, list):
        return isinstance(loaded, list) and sorted(map(str, loaded)) == sorted(now)
    return loaded == now


def edit(request: Request):
    """`backend.update`, after checking each property the form changes still
    holds the value the form loaded (`expected`)."""
    ctx = context(request)
    writable(ctx)
    folder = item_folder(ctx, request.param(1))
    changes = parse_changes(request.field("changes", dict))
    expected = request.field("expected", dict, required=False, default={})
    changed = _changed(changes)
    if not changed:
        raise usage("nothing to change")
    missing = [n for n in changed if n not in expected]
    if missing:
        raise usage(f"expected must hold the loaded value of {', '.join(missing)}")
    changes, notes = references(ctx, changes)
    with request.lock:
        record = item_record(ctx.backend.read(folder), [], ctx.layout)
        stale = [n for n in changed if not _same(expected[n], record[n])]
        if stale:
            raise StaleRevision(f"{', '.join(stale)} changed since the page loaded it")
        item = ctx.backend.update(folder, changes)
    siblings, _ = readable(ctx.backend)
    answer = checked({"item": item_record(item, siblings, ctx.layout)}, request,
                     ValidationTarget("work", folder, item))
    if notes:
        answer["warnings"] = notes + answer.get("warnings", [])
    return HTTPStatus.OK, answer


def add_comment(request: Request):
    ctx = context(request)
    writable(ctx)
    folder = item_folder(ctx, request.param(1))
    text = request.field("text")
    if not text.strip():
        raise usage("a comment needs text")
    with request.lock:
        ctx.backend.comment(folder, text)
    return HTTPStatus.CREATED, {"folder": folder}


CREATE_PROPERTIES = ("priority", "effort", "complexity", "tags", "assignee", "parent",
                     "blocked-by")


def create(request: Request):
    """`new` in this project. Answers what the CLI prints: the new item's
    full identifier. An item is created only in its own project (TCW-114
    Design 2.3): another project's is made there, with `tcw -C`."""
    from tcw.work.cli import new_item
    ctx = context(request)
    target = request.field("project", required=False)
    if target and target != ctx.backend.project:
        raise usage(f"an item is created only in its own project; create it in "
                    f"'{target}' with tcw -C tcw://{target}.path/ work new \"<title>\" "
                    f"--parent <full id>")
    title = request.field("title")
    if not title.strip():
        raise usage("a title must not be empty")
    text = request.field("requestText", required=False)
    text = text if isinstance(text, str) and text.strip() else None
    props = request.field("properties", dict, required=False, default={})
    unknown = sorted(set(props) - set(CREATE_PROPERTIES))
    if unknown:
        raise usage(f"properties has unknown entries: {', '.join(unknown)}")
    # Inside the parent's folder (TCW-111 Design 5), refused with no parent
    # before anything is made, as `tcw work new --nest` is.
    nest = request.field("nest", bool, required=False, default=False)
    if nest and not props.get("parent"):
        raise usage("nest puts the item's folder inside its parent's; give the parent")
    changes = parse_changes({
        **{k: props[k] for k in ("priority", "effort", "complexity", "assignee",
                                 "parent") if props.get(k)},
        "tags": {"add": props.get("tags") or []},
        "blocked-by": {"add": props.get("blocked-by") or []}})
    changes, notes = references(ctx, changes)
    if ctx.owner == BACKEND:
        # A parent in another project is the backend's to accept or refuse (a
        # ticket on the same site can be one); a blocker must be an item here.
        if any(n["where"] == "blocked-by" for n in notes):
            raise usage("blocked-by: in this project an item can be blocked only by "
                        "another item of this project")
        assignee = changes.assignee
        if assignee not in (UNSET, None) and \
                not request.services.is_assignable(ctx.backend, assignee):
            raise usage(f"assignee: {assignee} is not the account id of anyone "
                        f"assignable in this project; choose one from the suggestions")
    with request.lock:
        item = new_item(ctx.backend, title, changes,
                        stage=request.field("stage", required=False), request=text,
                        nest=nest)
    answer: dict[str, Any] = {"full-id": str(item.slug)}
    if notes:
        answer["warnings"] = notes
    return HTTPStatus.CREATED, answer


# -- Jira inbox tickets ----------------------------------------------------------------------


def tickets(request: Request):
    ctx = context(request)
    found, query = request.services.inbox(ctx.backend)
    return HTTPStatus.OK, {"tickets": found, "query": query}


def adopt(request: Request):
    """`tcw work tickets adopt`: the ticket becomes an item, and the request
    stage's post hooks run, as they do under the CLI. A hook that fails does
    not undo the item; what it reported is `problem`, for the page to show."""
    ctx = context(request)
    with request.lock:
        slug, code, problem = request.services.adopt(ctx.backend, request.param(1),
                                                     ctx.root)
    return HTTPStatus.CREATED, {"full-id": slug, "code": code, "problem": problem}


# -- suggestions the client cannot compute ------------------------------------------------

SUGGESTIONS = 10


def _other_items(request: Request, ctx: WorkContext, text: str) -> list[dict]:
    """Items of connected filesystem-mode projects found on this machine.
    A Jira-mode project is not asked: that would need its credentials and
    the network for a suggestion. A project that cannot be read is skipped."""
    from tcw.projects_cli import connected
    from tcw.store.project import FsProjectRegistry
    registry = FsProjectRegistry.open(ctx.root)
    wanted = text.lower()
    found: list[dict] = []
    for row in connected(ctx.root):
        if row["relation"] == "current" or not row["present"]:
            continue
        try:
            locator = Path(registry.get(row["id"]).locator)
            if read_work_config(locator, personal=False,
                                registry=registry).backend != "filesystem":
                continue
            items = request.services.open_project(row["id"], ctx.root).list(Query(all=True))
        except (TcwError, ValueError, OSError):
            continue
        for item in items:
            if wanted in str(item.slug).lower() or wanted in item.title.lower():
                found.append({"full-id": str(item.slug), "title": item.title,
                              "stage": item.stage, "project": row["id"]})
    return found[:SUGGESTIONS]


def options(request: Request):
    ctx = context(request)
    field = request.param(1)
    text = request.query.get("q", [""])[-1]
    if field == "assignee":
        found = request.services.assignable_users(ctx.backend, text, SUGGESTIONS)
        return HTTPStatus.OK, [{"id": i, "name": n} for i, n in found]
    if field == "work":
        return HTTPStatus.OK, _other_items(request, ctx, text)
    raise not_found(f"no suggestions for {field}")


def written_item(request: Request) -> list[Written]:
    """The `writes` of a route that changes the item its path names
    (TCW-114 Design 1.4): a full identifier as written, so another
    project's item is refused before any backend is opened; any other key
    names an item of the served project, whose own it is, so it is not
    looked up here; the handler finds it."""
    from tcw.ownership import active_project_id
    key = request.param(1)
    try:
        found = sort_input(key, "work", KEY)
    except MalformedId:
        return []                       # the handler's own lookup answers it
    if found.form in ("a", "c"):
        return [Written(found.full_id)]
    return [Written(FullId(active_project_id(request.root), "work",
                           found.id_path or found.key))]


ONE = r"/([^/]+)"
ROUTES = [
    route("GET", r"/api/project", project),
    route("GET", r"/api/work", board),
    route("POST", r"/api/work", create, writes=creates),
    route("GET", r"/api/work" + ONE, detail),
    route("PATCH", r"/api/work" + ONE, edit, writes=written_item),
    route("POST", r"/api/work" + ONE + r"/comments", add_comment, writes=written_item),
    route("GET", r"/api/tickets", tickets),
    route("POST", r"/api/tickets" + ONE + r"/adopt", adopt, writes=creates),
    route("GET", r"/api/options" + ONE, options),
]
