"""The `tcw work` item commands on the 3.0 model (TCW-70 Design 7).

Every stdout line is a full slug, a stage, a path or a record, so a script can
read it; everything said to a person goes to stderr. A failure is a `TcwError`
carrying its exit code, which `run` (and `tcw.cli.main`) turn into
`tcw: <message>` on stderr.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from tcw import exit as codes
from tcw.errors import BackendError, NotFound, Refused, TcwError, UsageError
from tcw.store.base import normalize_tag
from tcw.store.fs import FsProjectRegistry, find_node_root
from tcw.stdin import read_piped_stdin
from tcw.work.advance import advance as advance_item, discard as discard_item
from tcw.work.backend import Query, WorkBackend
from tcw.work.fs_backend import FsWorkBackend, read_all
from tcw.work.gates import project_reader
from tcw.work.model import UNSET, Changes, Slug, inbox_stage, start_stage
from tcw.work.open import delegate, open_backend, open_for_update, open_project
from tcw.work.record import item_record

NAME = "work"
SUBCOMMANDS = {"new", "list", "show", "path", "edit", "advance", "discard",
               "comment", "rename"}
DEFAULT_SUBCOMMAND = None


# -- finding the project and the item ---------------------------------------------


def project_root(here: Path | None = None) -> Path:
    root = find_node_root(here or Path.cwd())
    if root is None:
        raise BackendError("no tcw project here — run `tcw init` in the project "
                           "folder")
    return root


def resolve_item(arg: str, here: Path | None = None
                 ) -> tuple[Slug, WorkBackend, Path]:
    """The slug `arg` names, the backend that holds it, and this project's
    root. A full slug or a bare folder name, matched exactly; another
    project's slug opens that project for reading."""
    root = project_root(here)
    backend = open_backend(root)
    slug = Slug.parse(arg, backend.project)
    if slug.project != backend.project:
        backend = open_project(slug.project, root)
    return slug, backend, root


def _own(slug: Slug, backend: WorkBackend, root: Path) -> WorkBackend:
    """Refuse a write to another project's item."""
    if slug.project != open_backend(root).project:
        raise Refused(f"{slug} belongs to project '{slug.project}'; run the "
                      f"command in that project")
    return backend


# -- flag values ---------------------------------------------------------------------------


def _tags(value: str) -> list[str]:
    """One tag value is a comma-separated list, normalized as 2.8 normalizes it."""
    try:
        tags = [normalize_tag(t) for t in (p.strip() for p in value.split(","))
                if t]
    except ValueError as error:
        raise argparse.ArgumentTypeError(str(error))
    if not tags:
        raise argparse.ArgumentTypeError(f"invalid tag {value!r}: names no tag")
    return tags


def _nonempty(value: str) -> str:
    if not value.strip():
        raise argparse.ArgumentTypeError("title must be non-empty")
    return value


def _optional(value):
    """A flag not given leaves the property alone; an empty value clears it."""
    if value is None:
        return UNSET
    return None if value == "" else value


def _say(line: str) -> None:
    print(line, file=sys.stderr)


def _layout(backend: WorkBackend):
    return backend.layout


def _readable(backend: WorkBackend) -> list:
    """Every readable item, with one warning naming the unreadable ones."""
    if isinstance(backend, FsWorkBackend):
        items, bad = read_all(backend.work_path, backend.project, backend.enabled)
        if bad:
            _say("warning: these items could not be read, so blocks and children "
                 "may be incomplete: " + ", ".join(str(b.path) for b in bad))
        return items
    return backend.list(Query(all=True))


# -- commands ----------------------------------------------------------------------------


PROPERTY_FLAGS = ("effort", "complexity", "tag", "assignee", "parent", "blocked_by")


def _new(args) -> int:
    root = project_root()
    stage = args.stage or start_stage()
    if stage != inbox_stage() and args.stage is not None:
        raise UsageError(f"--stage accepts only {inbox_stage()}")
    request = read_piped_stdin()
    request = request if request.strip() else None
    if args.project:
        given = [f for f in PROPERTY_FLAGS if getattr(args, f)]
        if given:
            flag = "--" + given[0].replace("_", "-")
            raise UsageError(f"{flag} cannot be used with --project; only "
                             f"--priority can. Set it in that project afterwards")
        print(delegate(args.project, args.title, request, args.priority,
                       here=root, report=_say))
        return codes.OK
    backend = open_backend(root)
    changes = Changes(
        priority=_optional(args.priority), effort=_optional(args.effort),
        complexity=_optional(args.complexity), assignee=_optional(args.assignee),
        parent=_optional(args.parent), add_tags=tuple(args.tag or ()),
        add_blocked_by=tuple(args.blocked_by or ()))
    item = backend.create(args.title, changes, stage=stage, request=request)
    print(item.slug)
    return codes.OK


def _list(args) -> int:
    root = project_root()
    backend = open_backend(root)
    tags = frozenset(args.tag) if args.tag else None
    for tag in sorted(tags or ()):
        if tag not in backend.config.tags:
            _say(f"warning: tag '{tag}' is not in this project's registry")
    parent = Slug.parse(args.parent, backend.project) if args.parent else None
    query = Query(stages=frozenset(args.stage) if args.stage else None,
                  parent=parent, assignee=args.assignee, tags=tags,
                  all=args.all)
    items = backend.list(query)
    if args.json:
        every = _readable(backend)
        print(json.dumps([item_record(i, every, _layout(backend)) for i in items],
                         indent=2))
        return codes.OK
    for item in items:
        print(item.slug)
    return codes.OK


def _show(args) -> int:
    slug, backend, _ = resolve_item(args.slug)
    item = backend.read(slug.folder)
    record = item_record(item, _readable(backend), _layout(backend))
    if args.json:
        print(json.dumps(record, indent=2))
        return codes.OK
    for key, value in record.items():
        if isinstance(value, list):
            value = ", ".join(map(str, value))
        print(f"{key}: {'' if value is None else value}")
    return codes.OK


def _path(args) -> int:
    if args.slug is None:
        if args.stage or args.next or args.handoff:
            raise UsageError("name an item first")
        backend = open_backend(project_root())
        print(backend.work_path)
        return codes.OK
    slug, backend, _ = resolve_item(args.slug)
    backend.read(slug.folder)
    print(_layout(backend).path(slug, args.stage, next=args.next,
                                handoff=args.handoff))
    return codes.OK


def _edit(args) -> int:
    slug, backend, root = resolve_item(args.slug)
    changes = Changes(
        title=_optional(args.title), priority=_optional(args.priority),
        effort=_optional(args.effort), complexity=_optional(args.complexity),
        assignee=_optional(args.assignee), parent=_optional(args.parent),
        add_tags=tuple(args.tag or ()), remove_tags=tuple(args.untag or ()),
        add_blocked_by=tuple(args.blocked_by or ()),
        remove_blocked_by=tuple(args.unblocked_by or ()))
    targets = [Slug.parse(t, slug.project) for t in args.blocks or ()]
    if changes != Changes():
        _own(slug, backend, root).update(slug.folder, changes)
    elif not targets:
        raise UsageError("nothing to change; give at least one property flag")
    if targets:
        _own(slug, backend, root).read(slug.folder)
    for target in targets:
        other = backend if target.project == slug.project else \
            open_for_update(target.project, root)
        other.update(target.folder, Changes(add_blocked_by=(slug,)))
    return codes.OK


def _move(args, *, to=None, force=False, reason=None, dry_run=False) -> int:
    slug, backend, root = resolve_item(args.slug)
    _own(slug, backend, root)
    reader = project_reader(root, FsProjectRegistry.open(root))
    outcome = advance_item(backend, backend.config, _layout(backend), reader, root,
                           slug, to=to, force=force, reason=reason,
                           dry_run=dry_run)
    return _report(outcome)


def _report(outcome) -> int:
    for line in outcome.overridden:
        _say(f"forced past: {line}")
    for line in outcome.messages:
        _say(line)
    if outcome.code in (codes.OK, codes.MOVED_WITH_PROBLEM) and outcome.stage:
        print(outcome.stage)
    return outcome.code


def _advance(args) -> int:
    return _move(args, to=args.to, force=args.force, reason=args.reason,
                 dry_run=args.dry_run)


def _discard(args) -> int:
    slug, backend, root = resolve_item(args.slug)
    _own(slug, backend, root)
    reader = project_reader(root, FsProjectRegistry.open(root))
    return _report(discard_item(backend, backend.config, _layout(backend), reader,
                                root, slug, args.reason))


def _comment(args) -> int:
    slug, backend, root = resolve_item(args.slug)
    text = read_piped_stdin()
    if not text.strip():
        raise UsageError("pipe the comment text on stdin")
    _own(slug, backend, root).comment(slug.folder, text)
    return codes.OK


def _rename(args) -> int:
    slug, backend, root = resolve_item(args.slug)
    item = _own(slug, backend, root).rename(slug.folder, args.new_name)
    print(item.slug)
    return codes.OK


# -- the parser ------------------------------------------------------------------------------


def _properties(p: argparse.ArgumentParser, *, editing: bool) -> None:
    p.add_argument("--priority")
    p.add_argument("--effort")
    p.add_argument("--complexity")
    p.add_argument("--tag", "--tags", dest="tag", type=_tags, action="extend",
                   help="a tag, or comma-separated tags; repeats")
    p.add_argument("--assignee")
    p.add_argument("--parent")
    p.add_argument("--blocked-by", dest="blocked_by", action="append")
    if editing:
        p.add_argument("--title", type=_nonempty)
        p.add_argument("--untag", "--untags", dest="untag", type=_tags,
                       action="extend")
        p.add_argument("--unblocked-by", dest="unblocked_by", action="append")
        p.add_argument("--blocks", action="append",
                       help="add this item to another item's blocked-by")


def add_subparser(sub: argparse._SubParsersAction) -> None:
    work = sub.add_parser(NAME, help="work items")
    cmds = work.add_subparsers(dest="work_command", required=True)

    p = cmds.add_parser("new", help="create an item; request text from stdin")
    p.add_argument("title")
    p.add_argument("--project")
    p.add_argument("--stage")
    _properties(p, editing=False)
    p.set_defaults(func=_new)

    p = cmds.add_parser("list", help="list items, one slug per line")
    p.add_argument("--stage", action="append")
    p.add_argument("--tag", "--tags", dest="tag", type=_tags, action="extend")
    p.add_argument("--parent")
    p.add_argument("--assignee")
    p.add_argument("--all", action="store_true")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=_list)

    p = cmds.add_parser("show", help="an item's record")
    p.add_argument("slug")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=_show)

    p = cmds.add_parser("path", help="a path in the work store")
    p.add_argument("slug", nargs="?")
    p.add_argument("stage", nargs="?")
    which = p.add_mutually_exclusive_group()
    which.add_argument("--next", action="store_true")
    which.add_argument("--handoff", action="store_true")
    p.set_defaults(func=_path)

    p = cmds.add_parser("edit", help="change an item's properties")
    p.add_argument("slug")
    _properties(p, editing=True)
    p.set_defaults(func=_edit)

    p = cmds.add_parser("advance", help="move an item to its next stage")
    p.add_argument("slug")
    p.add_argument("--to")
    p.add_argument("--force", action="store_true")
    p.add_argument("--reason")
    p.add_argument("--dry-run", dest="dry_run", action="store_true")
    p.set_defaults(func=_advance)

    p = cmds.add_parser("discard", help="move an item to discarded")
    p.add_argument("slug")
    p.add_argument("--reason", required=True)
    p.set_defaults(func=_discard)

    p = cmds.add_parser("comment", help="add a comment; text from stdin")
    p.add_argument("slug")
    p.set_defaults(func=_comment)

    p = cmds.add_parser("rename", help="rename an item's folder")
    p.add_argument("slug")
    p.add_argument("new_name")
    p.set_defaults(func=_rename)


def run(argv: list[str]) -> int:
    """This command group alone, as `tcw.cli.main` will run it."""
    parser = argparse.ArgumentParser(prog="tcw")
    add_subparser(parser.add_subparsers(dest="component", required=True))
    try:
        args = parser.parse_args(argv)
    except SystemExit as stop:
        return codes.USAGE if stop.code else codes.OK
    try:
        return args.func(args)
    except TcwError as error:
        print(f"tcw: {error}", file=sys.stderr)
        return error.code
