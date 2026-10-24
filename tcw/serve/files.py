"""An item's files: documents, rounds, handoffs and the declaration file.

Only the paths the layout names are files here, and only for enabled stages
whose record is kept in the item folder. Everything else in the folder is
the backend's storage or not part of the model, and is not found.
"""

from __future__ import annotations

import dataclasses
import hashlib
from http import HTTPStatus
from pathlib import Path
from typing import Any

import yaml

from tcw.errors import TcwError
from tcw.serve.records import checked
from tcw.serve.server import ApiError, Request, not_found, route, usage
from tcw.store.base import StaleRevision
from tcw.store.fs import _atomic_write_all
from tcw.validate import ValidationTarget
from tcw.work.gates import (Invalid, Present, Unchecked, parse_declarations,
                             project_reader)
from tcw.work.layout import CAPABILITIES_FILE, HANDOFF_NAME, ROUND_NAME, Layout, round_verdict
from tcw.work.model import (
    DOCUMENT, NO_ARTIFACT, ROUNDS, STAGES, Slug, check_encodable, is_stage,
    stage as table_stage,
)


def revision(path: Path) -> str | None:
    """The SHA-256 of the file's bytes, or None when there is no file."""
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except (FileNotFoundError, IsADirectoryError, NotADirectoryError):
        return None


def file_stages(context) -> list:
    """The stage rows whose files live in the item folder: enabled, with an
    artifact, and not kept by the backend. In table order."""
    return [row for row in STAGES
            if row.name in context.config.enabled and row.artifact != NO_ARTIFACT
            and row.name not in context.backend.external_stages]


class _ItemOnly(Layout):
    """The layout with only the rounds that resolve inside their item folder:
    the viewer reads no other file (`inside_item`), so it lists and judges
    verdicts by these alone."""

    def rounds(self, slug: Slug, stage: str) -> list[tuple[int, Path]]:
        item_dir = self.item_dir(slug)
        return [(number, path) for number, path in super().rounds(slug, stage)
                if contained(item_dir, path)]


def _item_only(layout: Layout) -> _ItemOnly:
    return _ItemOnly(**{f.name: getattr(layout, f.name)
                        for f in dataclasses.fields(layout) if f.init})


def _handoffs(item_dir: Path, folder: Path) -> list[Path]:
    if not folder.is_dir():
        return []
    return sorted((e for e in folder.iterdir()
                   if HANDOFF_NAME.match(e.name) and e.is_file()
                   and contained(item_dir, e)),
                  key=lambda e: e.name)


def _entry(item_dir: Path, path: Path) -> dict[str, Any]:
    return {"path": path.relative_to(item_dir).as_posix(),
            "revision": revision(path) if contained(item_dir, path) else None}


def _present(item_dir: Path, path: Path) -> bool:
    return path.is_file() and contained(item_dir, path)


def listing(context, slug: Slug) -> list[dict[str, Any]]:
    """Every file the item may have, read from disk alone: per stage its
    document or its rounds, and its handoffs; then the declaration file.
    Needs no backend read, so it answers while the backend cannot. A file
    reached through a link that leads outside the item folder is not one of
    its files: a document or the declaration is shown as not written yet, and
    a round or handoff is left out."""
    layout = _item_only(context.layout)
    item_dir = layout.item_dir(slug)
    found: list[dict[str, Any]] = []
    for row in file_stages(context):
        entry: dict[str, Any] = {"stage": row.name, "artifact": row.artifact,
                                 "verdict": row.verdict}
        if row.artifact == DOCUMENT:
            document = layout.document(slug, row.name)
            entry["document"] = {**_entry(item_dir, document),
                                 "present": _present(item_dir, document)}
        elif row.artifact == ROUNDS:
            rounds = []
            for number, path in reversed(layout.rounds(slug, row.name)):
                one = {**_entry(item_dir, path), "number": number}
                if row.verdict:
                    one["verdict"] = round_verdict(path).state
                rounds.append(one)
            entry["rounds"] = rounds
        entry["handoffs"] = [_entry(item_dir, p) for p in reversed(
            _handoffs(item_dir, layout.stage_dir(slug, row.name)))]
        found.append(entry)
    declaration = layout.capabilities_file(slug)
    found.append({"stage": None, "artifact": "declaration",
                  "document": {**_entry(item_dir, declaration),
                               "present": _present(item_dir, declaration)}})
    return found


def verdicts(context, slug: Slug) -> list[dict[str, str]]:
    """`current_verdict` for each verdict stage whose rounds are on disk,
    judged by the rounds inside the item folder alone."""
    layout = _item_only(context.layout)
    return [{"stage": row.name, "verdict": layout.current_verdict(slug, row.name)}
            for row in file_stages(context) if row.verdict]


# -- which paths are files ------------------------------------------------------------------


def file_path(context, slug: Slug, path: str) -> Path:
    """The file `path` names in the item folder, when the layout names it for
    an enabled stage kept on disk: `<stage>/<stage>.md` for a document stage,
    `<stage>/round-N.md` for a rounds stage, `<stage>/handoff-<stamp>.md` for
    either, and the declaration file. Anything else is not found."""
    item_dir = context.layout.item_dir(slug)
    if path == CAPABILITIES_FILE:
        return inside_item(item_dir, item_dir / CAPABILITIES_FILE, path)
    parts = path.split("/")
    if len(parts) == 2 and is_stage(parts[0]):
        name, file = parts
        row = table_stage(name)
        if row in file_stages(context):
            if (row.artifact == DOCUMENT and file == f"{name}.md") or \
                    (row.artifact == ROUNDS and ROUND_NAME.fullmatch(file)) or \
                    HANDOFF_NAME.fullmatch(file):
                return inside_item(item_dir, item_dir / name / file, path)
    raise not_found(f"{path} is not one of this item's files")


def inside_item(item_dir: Path, path: Path, shown: str) -> Path:
    """`path`, when it resolves inside the item folder's resolved path. A
    symbolic link, the stage folder or the file itself, that leads outside
    the item folder makes it not one of the item's files, so it is neither
    read nor written. Both sides are resolved, so a work path that is itself
    a link is unaffected; a file not written yet is judged by where it would
    go."""
    if not contained(item_dir, path):
        raise not_found(f"{shown} is not one of this item's files")
    return path


def contained(item_dir: Path, path: Path) -> bool:
    """Whether `path` resolves inside the item folder's resolved path."""
    try:
        return path.resolve().is_relative_to(item_dir.resolve())
    except (OSError, RuntimeError):             # a loop of links
        return False


def _target(request: Request):
    from tcw.serve.work import context, item_folder
    ctx = context(request)
    folder = item_folder(ctx, request.param(1))
    return ctx, folder, ctx.slug(folder)


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        raise not_found(f"{path.name} has not been written yet") from None
    except (OSError, UnicodeDecodeError) as error:
        raise ApiError(HTTPStatus.INTERNAL_SERVER_ERROR, "error",
                       f"cannot read {path.name}: {error}") from None


def write_checked(request: Request, path: Path, content: str,
                  expected: str | None) -> str:
    """Write `content` whole, holding the write lock, when the file's current
    revision is `expected` (None: the file must not exist yet). The enabled
    stage's folder is made for a new file; the temporary file sits beside the
    target, so the rename that puts it in place is atomic."""
    check_encodable(content, "the content")
    with request.lock:
        current = revision(path)
        if current != expected:
            raise StaleRevision(
                f"{path.name} already exists" if expected is None and current
                else f"{path.name} changed since it was loaded")
        path.parent.mkdir(exist_ok=True)
        _atomic_write_all([(path, content)])
        return revision(path) or ""


def saved(request: Request, ctx, folder: str, response: dict) -> dict:
    """`response` with the item's validation findings, checked offline.
    When the backend owns the record, no item is read: that read may need
    the network, and a file save must answer while the backend cannot, so
    the checks that need the item are skipped. Otherwise the checks use the
    item as the backend gives it now, or skip when it cannot be read."""
    from tcw.serve.work import BACKEND
    item = None
    if ctx.owner != BACKEND:
        try:
            item = ctx.backend.read(folder)
        except Exception:
            item = None
    return checked(response, request, ValidationTarget("work", folder, item))


def _expected(request: Request) -> str | None:
    if "revision" not in request.body:
        raise usage("revision is required: the file's revision, or null for a new file")
    return request.field("revision", required=False)


# -- documents, rounds and handoffs ---------------------------------------------------------


def get_file(request: Request):
    ctx, folder, slug = _target(request)
    path = file_path(ctx, slug, request.param(2))
    content = _read(path)
    return HTTPStatus.OK, {"content": content, "revision": revision(path)}


def put_file(request: Request):
    ctx, folder, slug = _target(request)
    path = file_path(ctx, slug, request.param(2))
    content = request.field("content")
    new = write_checked(request, path, content, _expected(request))
    return HTTPStatus.OK, saved(request, ctx, folder, {"revision": new})


KINDS = {"document": DOCUMENT, "round": ROUNDS, "handoff": None}


def new_file(request: Request):
    """Where a new document, round or handoff goes, and its starting text.
    Nothing is written: the `PUT` that follows creates it."""
    ctx, folder, slug = _target(request)
    name, kind = request.field("stage"), request.field("kind")
    if kind not in KINDS:
        raise usage(f"kind must be one of {', '.join(KINDS)}")
    row = table_stage(name)
    if row not in file_stages(ctx):
        raise usage(f"{name} has no files in this item's folder")
    if KINDS[kind] is not None and row.artifact != KINDS[kind]:
        raise usage(f"{name} keeps {'one document' if row.artifact == DOCUMENT else 'rounds'}"
                    f", not a {kind}")
    try:
        path = ctx.layout.path(slug, name, next=kind == "round", handoff=kind == "handoff")
    except TcwError as error:
        if kind == "handoff":
            raise
        raise usage(str(error)) from None
    template = ""
    if kind == "round" and row.verdict:
        judged = ROUND_NAME.match(ctx.layout.next_round(slug, row.on_reject).name)
        template = f"---\njudges: {int(judged.group(1)) - 1}\nverdict:\n---\n"
    relative = path.relative_to(ctx.layout.item_dir(slug)).as_posix()
    return HTTPStatus.OK, {"path": relative, "template": template}


# -- the declaration file ---------------------------------------------------------------------

LISTS = ("new", "changed", "removed")
MUST_EXIST = ("changed", "removed")


def _lists(declared) -> dict[str, Any]:
    return {"capabilities": {k: list(getattr(declared, k)) for k in LISTS},
            "taxonomy": {k: list(getattr(declared, f"term_{k}")) for k in LISTS}}


def get_declaration(request: Request):
    """The six lists, or, for a file the parser rejects, its message and the
    text, so the file can be fixed as plain text."""
    ctx, folder, slug = _target(request)
    path = inside_item(ctx.layout.item_dir(slug), ctx.layout.capabilities_file(slug),
                       CAPABILITIES_FILE)
    declared = parse_declarations(path)
    answer: dict[str, Any] = {"revision": revision(path), "present": path.is_file()}
    if isinstance(declared, str):
        answer.update(problem=f"{CAPABILITIES_FILE}: {declared}",
                      content=path.read_text(encoding="utf-8", errors="replace"))
    else:
        answer.update(problem=None, **_lists(declared))
    return HTTPStatus.OK, answer


def _sent_lists(request: Request) -> dict[str, dict[str, list[str]]]:
    """The six lists as sent, each entry written as a full identifier
    (TCW-110 Design 5.3): an id-path names this project's own record."""
    from tcw.ids import FullId, IdError, sort_input
    from tcw.locate import Locator
    project_id = None

    def stored(value: str, namespace: str) -> str:
        nonlocal project_id
        try:
            found = sort_input(value, namespace)
        except IdError as error:
            raise usage(str(error)) from None
        if found.form != "d":
            return str(found.full_id)
        project_id = project_id or Locator.of(request.root).project_id
        return str(FullId(project_id, namespace, found.id_path))

    sent: dict[str, dict[str, list[str]]] = {}
    for axis in ("capabilities", "taxonomy"):
        group = request.field(axis, dict, required=False, default={})
        unknown = sorted(set(group) - set(LISTS))
        if unknown:
            raise usage(f"{axis} has unknown list(s): {', '.join(unknown)}")
        sent[axis] = {}
        for kind in LISTS:
            values = group.get(kind) or []
            if not isinstance(values, list) or not all(
                    isinstance(v, str) and v.strip() for v in values):
                raise usage(f"{axis}.{kind} must be a list of non-empty names")
            sent[axis][kind] = list(dict.fromkeys(stored(v.strip(), axis) for v in values))
    return sent


def _check_existing(request: Request, sent, before) -> None:
    """A `changed` or `removed` entry the save adds must name something that
    exists, inherited entries included. Entries already in the file are not
    checked again, so a record removed mid-work leaves the file savable."""
    from tcw.store.project import FsProjectRegistry
    reader = None
    for axis, ask in (("capabilities", "capability"), ("taxonomy", "term")):
        for kind in MUST_EXIST:
            for name in sent[axis][kind]:
                if name in before[axis][kind]:
                    continue
                reader = reader or project_reader(request.root,
                                                  FsProjectRegistry.open(request.root))
                answer = getattr(reader, ask)(name)
                if isinstance(answer, (Invalid, Unchecked)):
                    raise usage(f"{axis}.{kind}: {name}: {answer.reason}")
                if not isinstance(answer, Present):
                    raise usage(f"{axis}.{kind}: {name} does not exist")


def _yaml(sent) -> str:
    """The lists in schema order, empty ones left out."""
    document: dict[str, Any] = {k: v for k, v in sent["capabilities"].items() if v}
    taxonomy = {k: v for k, v in sent["taxonomy"].items() if v}
    if taxonomy:
        document["taxonomy"] = taxonomy
    return yaml.safe_dump(document, sort_keys=False) if document else ""


def put_declaration(request: Request):
    ctx, folder, slug = _target(request)
    path = inside_item(ctx.layout.item_dir(slug), ctx.layout.capabilities_file(slug),
                       CAPABILITIES_FILE)
    expected = _expected(request)
    sent = _sent_lists(request)
    current = parse_declarations(path)
    before = _lists(current) if not isinstance(current, str) else \
        {axis: {k: [] for k in LISTS} for axis in ("capabilities", "taxonomy")}
    _check_existing(request, sent, before)
    new = write_checked(request, path, _yaml(sent), expected)
    return HTTPStatus.OK, saved(request, ctx, folder, {"revision": new})


def written_item(request: Request):
    """The item the route's path names, as the work routes answer it."""
    from tcw.serve.work import written_item as item
    return item(request)


ITEM = r"/api/work/([^/]+)"
ROUTES = [
    route("GET", ITEM + r"/files/(.+)", get_file),
    route("PUT", ITEM + r"/files/(.+)", put_file, writes=written_item),
    route("POST", ITEM + r"/files", new_file, writes=written_item),
    route("GET", ITEM + r"/declaration", get_declaration),
    route("PUT", ITEM + r"/declaration", put_declaration, writes=written_item),
]
