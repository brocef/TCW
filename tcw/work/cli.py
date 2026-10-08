"""The `tcw work` commands on the 3.0 model (TCW-70 Design 7).

Every stdout line is a full slug, a stage, a path, a record or composed text,
so a script can read it; everything said to a person goes to stderr. A failure
is a `TcwError` carrying its exit code, which `tcw.cli.main` turns into
`tcw: <message>` on stderr.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from tcw import exit as codes
from tcw.errors import BackendError, Refused, UsageError
from tcw.store.base import normalize_tag
from tcw.store.fs import FsProjectRegistry, find_node_root
from tcw.stdin import read_piped_stdin
from tcw.work.advance import advance as advance_item, discard as discard_item
from tcw.work.backend import Query, WorkBackend
from tcw.work.fs_backend import FsWorkBackend, read_all
from tcw.work.gates import project_reader
from tcw.work.model import (
    STAGES, UNSET, Changes, Slug, inbox_stage, stage as table_stage, start_stage,
)
from tcw.work.open import delegate, open_backend, open_for_update, open_project
from tcw.work.record import item_record

NAME = "work"
SUBCOMMANDS = {"new", "list", "show", "path", "edit", "advance", "discard",
               "comment", "rename", "stage", "procedure", "lifecycle", "docs",
               "tags", "nodes", "init"}
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


SLUG_HELP = "the item: its full slug, or its folder name"
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


# -- instructions: stage prompt, procedure prompt, lifecycle, docs ----------------------


def _prompt_target(args):
    """`(backend, item, record, request, layout, root)` for a composed prompt:
    the named item's, or this project's with no item."""
    if args.slug is None:
        root = project_root()
        return open_backend(root), None, None, None, None, root
    slug, backend, root = resolve_item(args.slug)
    item = backend.read(slug.folder)
    record = item_record(item, _readable(backend), _layout(backend))
    return (backend, item, record, backend.read_request(slug.folder),
            _layout(backend), root)


def _print_resolution(res, label: str, no_exec: bool) -> int:
    """The composed text on stdout, or with `--no-exec` the plan on stderr and
    nothing on stdout."""
    if no_exec:
        _say(f"{label}: --no-exec, nothing was resolved")
        for entry in res.plan:
            state = "matched" if entry.matched else "skipped (condition)"
            detail = f": {entry.ref}" if entry.kind != "builtin" else ""
            _say(f"  {entry.kind} — {state}{detail}")
        return codes.OK
    if res.text:
        print(res.text)
    elif res.plan and not any(entry.matched for entry in res.plan):
        _say(f"{label}: note — every binding carries a when: that did not "
             f"match, so nothing resolved")
    return codes.OK


def _resolved(compose_call):
    from tcw.work.resolve import ResolveError
    try:
        return compose_call()
    except ResolveError as error:
        raise BackendError(str(error)) from None


def _stage_prompt(args) -> int:
    from tcw.work.resolve import stage_header, stage_prompt
    step = table_stage(args.stage)
    if not step.prompt:
        raise UsageError(f"'{step.name}' has no instructions; it is where an item "
                         f"ends, not a stage worked in")
    if step.name == inbox_stage() and args.slug is not None:
        raise UsageError(f"'{step.name}' runs before an item exists and takes no "
                         f"work item; run it with no argument")
    backend, item, record, request, layout, root = _prompt_target(args)
    if step.name not in backend.config.enabled:
        _say(f"note: '{step.name}' is disabled in this project; printing its "
             f"instructions because you asked to read them")
    res = _resolved(lambda: stage_prompt(
        backend.config, step.name, item=item, record=record, request=request,
        layout=layout, project_root=root, execute=not args.no_exec))
    label = f"tcw work stage prompt {step.name}"
    if not args.no_exec and res.text:
        target = str(item.slug) if item is not None else "<slug>"
        res.text = f"{stage_header(step.name, target)}\n\n{res.text}"
    return _print_resolution(res, label, args.no_exec)


def _procedure_prompt(args) -> int:
    from tcw.store.base import PROCEDURE_IDS
    from tcw.work.resolve import packaged_text, procedure_prompt
    if args.procedure not in PROCEDURE_IDS:
        raise UsageError(f"unknown procedure '{args.procedure}'; expected one of "
                         f"{', '.join(PROCEDURE_IDS)}")
    if args.slug is None and find_node_root(Path.cwd()) is None:
        # No project, so nothing to compose: TCW's own text. Skills that also
        # run outside TCW projects (documentation-sync) rely on this.
        print(packaged_text("procedures", args.procedure).rstrip())
        return codes.OK
    backend, item, record, request, layout, root = _prompt_target(args)
    res = _resolved(lambda: procedure_prompt(
        backend.config, args.procedure, item=item, record=record,
        request=request, layout=layout, project_root=root,
        execute=not args.no_exec))
    return _print_resolution(res, f"tcw work procedure prompt {args.procedure}",
                             args.no_exec)


PHASES = ("pre", "prompt", "post")


def _binding_json(b) -> dict:
    out: dict = {b.kind: True if b.kind == "builtin" else b.value}
    if b.when is not None:
        out["when"] = {k: list(v) for k, v in
                       (("tags", b.when.tags), ("not_tags", b.when.not_tags)) if v}
    return out


def _phases(config, name: str) -> dict:
    """A stage's three binding lists, `prompt` defaulting to TCW's own text."""
    from tcw.work.config import Binding as Binding3
    settings = config.stage(name)
    prompt = settings.prompt
    if prompt is None:
        prompt = (Binding3("builtin", ""),) if table_stage(name).prompt else ()
    return {"pre": settings.pre or (), "prompt": prompt,
            "post": settings.post or ()}


def _directive(name: str, bindings) -> str:
    """One instruction line for an agent, or "" when nothing is bound."""
    parts: list[str] = []
    text_named = False
    for b in bindings:
        if b.kind == "skill":
            parts.append(f"invoke the {b.value} skill")
        elif b.kind == "command":
            parts.append(f"run `{b.value}`")
        elif not text_named:
            parts.append("read this project's configured instructions")
            text_named = True
    return f"For the {name} stage, {' and '.join(parts)}." if parts else ""


def _lifecycle(args) -> int:
    if args.slug is not None:
        _, backend, _ = resolve_item(args.slug)
    else:
        backend = open_backend(project_root())
    config = backend.config
    if args.stage is not None:
        table_stage(args.stage)
        if args.stage not in config.enabled:
            raise UsageError(f"'{args.stage}' is disabled in this project")
        names = [args.stage]
    else:
        names = [s.name for s in STAGES if s.name in config.enabled]
    if args.directive:
        if args.stage is None:
            raise UsageError("--directive needs --stage")
        rows = _phases(config, args.stage)
        bindings = [b for phase in ([args.phase] if args.phase else PHASES)
                    for b in rows[phase]]
        text = _directive(args.stage, bindings)
        if text:
            print(text)
        return codes.OK
    wanted = [args.phase] if args.phase else list(PHASES)
    if args.json:
        print(json.dumps({
            "hooks": {"timeout": config.hooks.timeout,
                      "output-cap": config.hooks.output_cap},
            "stages": [{"name": name, "kind": table_stage(name).kind,
                        "bindings": {p: [_binding_json(b) for b in
                                         _phases(config, name)[p]]
                                     for p in wanted}}
                       for name in names]}, indent=2))
        return codes.OK
    for i, name in enumerate(names):
        if i:
            print()
        print(f"{name}  [{table_stage(name).kind}]")
        rows = _phases(config, name)
        for phase in wanted:
            if rows[phase]:
                refs = ", ".join(f"{b.kind}:{b.value}" if b.kind != "builtin"
                                 else "builtin" for b in rows[phase])
                print(f"  {phase + ':':8}{refs}")
    return codes.OK


def _docs(args) -> int:
    entries = open_backend(project_root()).config.documentation
    if args.json:
        print(json.dumps({"schema": 1,
                          "source": "config" if entries else "agent-guide",
                          "entries": [{"path": e.path, "trigger": e.trigger,
                                       "description": e.description}
                                      for e in entries]}, indent=2))
        return codes.OK
    if not entries:
        _say("tcw work docs: this project declares no `work.documentation`; "
             "documentation entries come from the project's agent guide "
             "(`AGENTS.md` or `CLAUDE.md`).")
        return codes.OK
    width = max(len(e.path) for e in entries)
    trigger_width = max(len(e.trigger) for e in entries) + 2
    for e in entries:
        description = " ".join(e.description.split())
        print(f"{e.path:<{width}}  {'[' + e.trigger + ']':<{trigger_width}}  "
              f"{description}")
    return codes.OK


# -- the tag registry -----------------------------------------------------------------


def _tags_list(args) -> int:
    for tag in open_backend(project_root()).config.tags:
        print(tag)
    return codes.OK


def _write_tags(change) -> int:
    """Rewrite `work.tags` in `tcw-config.yaml`, changing only its lines. The
    file is written and left unstaged, inside or outside a git repository."""
    from tcw.store import config_edit
    from tcw.store.fs import SENTINEL, _atomic_write_all
    root = project_root()
    backend = open_backend(root)
    result = sorted(change(set(backend.config.tags)))
    if set(result) != set(backend.config.tags):
        path = root / SENTINEL
        try:
            text = config_edit.edit_text(path, config_edit.read_text(path),
                                         [config_edit.SetList("work", "tags",
                                                              tuple(result))])
        except ValueError as error:
            raise BackendError(str(error)) from None
        if text is not None:
            _atomic_write_all([(path, text)])
    for tag in result:
        print(tag)
    return codes.OK


def _tags_add(args) -> int:
    given = {t for value in args.tag for t in value}
    return _write_tags(lambda tags: tags | given)


def _tags_rm(args) -> int:
    given = {t for value in args.tag for t in value}
    return _write_tags(lambda tags: tags - given)


# -- the project graph and init --------------------------------------------------------


def _nodes(args) -> int:
    from tcw.store.fs import (
        _has_work_store, child_nodes, parent_node, registered_children,
        registered_parent, registered_project_id, unreachable_children,
        unreachable_parent,
    )
    node = project_root()
    if not _has_work_store(node):
        raise BackendError("this project has no work store here — run `tcw init` "
                           "in the project folder")
    parent = parent_node(node)
    print(f"node:   {registered_project_id(node, node)}")
    if parent is not None:
        print(f"parent: {registered_project_id(node, parent)}")
    else:
        registered = registered_parent(node)
        if registered is not None:
            print(f"parent: {registered_project_id(node, registered)}"
                  f"{_no_store_note(registered)}")
        elif (absent := unreachable_parent(node)) is not None:
            print(f"parent: {absent.id}  (not in this checkout)")
        else:
            print("parent: (none — root)")
    children = registered_children(node)
    absent_children = unreachable_children(node)
    if children or absent_children:
        print("children:")
        with_store = {c.resolve() for c in child_nodes(node)}
        for c in children:
            print(f"  {registered_project_id(node, c)}"
                  f"{'' if c.resolve() in with_store else _no_store_note(c)}")
        for entry in absent_children:
            print(f"  {entry.id}  (not in this checkout)")
    else:
        print("children: (none — leaf)")
    _print_upstreams(node)
    return codes.OK


def _print_upstreams(node: Path) -> None:
    """The projects this one reads but may not write, each with who declared it
    and where it is. Printed only when there is one."""
    import os
    try:
        registry = FsProjectRegistry.open(node)
    except ValueError:
        return
    here = registry.current.id
    lines = []
    for declarer in [here, *(a.id for a in registry.ancestors(here))]:
        for upstream_id in registry.declared_upstream_ids(declarer):
            project = registry.get(upstream_id)
            where = (os.path.relpath(project.locator, node) if project is not None
                     else "(not in this checkout)")
            lines.append(f"  {upstream_id}  (declared by {declarer})  {where}")
    if lines:
        print("upstream (read-only):")
        print("\n".join(lines))


def _no_store_note(child: Path) -> str:
    """Why a registered child keeps no usable work store here."""
    from tcw.store.fs import declared_repository
    try:
        declaration, _ = declared_repository(child, "work")
    except Exception:
        declaration = None
    if declaration is not None:
        return "  (work store not provisioned here)"
    return "  (no work store)"


def _init(args) -> int:
    from tcw.cli import run_init  # function-local: tcw.cli imports this module
    return run_init([NAME], args.id, args.path)


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

    p = cmds.add_parser("new", help="create an item; text piped on stdin says what it asks for")
    p.add_argument("title", help="the item's title; the folder name is made from it")
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
    p.add_argument("slug", help=SLUG_HELP)
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=_show)

    p = cmds.add_parser("path", help="a path in the work store")
    p.add_argument("slug", nargs="?",
                   help=f"{SLUG_HELP}; without one, the work store folder")
    p.add_argument("stage", nargs="?",
                   help="a stage whose folder or file to name")
    which = p.add_mutually_exclusive_group()
    which.add_argument("--next", action="store_true")
    which.add_argument("--handoff", action="store_true")
    p.set_defaults(func=_path)

    p = cmds.add_parser("edit", help="change an item's properties")
    p.add_argument("slug", help=SLUG_HELP)
    _properties(p, editing=True)
    p.set_defaults(func=_edit)

    p = cmds.add_parser("advance", help="move an item to its next stage")
    p.add_argument("slug", help=SLUG_HELP)
    p.add_argument("--to")
    p.add_argument("--force", action="store_true")
    p.add_argument("--reason")
    p.add_argument("--dry-run", dest="dry_run", action="store_true")
    p.set_defaults(func=_advance)

    p = cmds.add_parser("discard", help="abandon an item, with a reason")
    p.add_argument("slug", help=SLUG_HELP)
    p.add_argument("--reason", required=True)
    p.set_defaults(func=_discard)

    p = cmds.add_parser("comment", help="add a comment; text from stdin")
    p.add_argument("slug", help=SLUG_HELP)
    p.set_defaults(func=_comment)

    p = cmds.add_parser("rename", help="rename an item's folder")
    p.add_argument("slug", help=SLUG_HELP)
    p.add_argument("new_name", help="the new words after the date, lower case "
                                    "and hyphenated")
    p.set_defaults(func=_rename)

    p = cmds.add_parser("stage", help="read a stage's instructions")
    verbs = p.add_subparsers(dest="stage_verb", required=True)
    p = verbs.add_parser("prompt", help="print a stage's instructions, running "
                                        "no checks")
    p.add_argument("stage", help="a stage (`tcw work lifecycle` lists them)")
    p.add_argument("slug", nargs="?",
                   help=f"optional; {SLUG_HELP}, so the text is composed for it")
    p.add_argument("--no-exec", dest="no_exec", action="store_true",
                   help="report what would resolve; prints nothing on stdout")
    p.set_defaults(func=_stage_prompt)

    p = cmds.add_parser("procedure", help="read one of TCW's procedures, "
                                          "composed with this project's text")
    verbs = p.add_subparsers(dest="procedure_verb", required=True)
    p = verbs.add_parser("prompt", help="print a procedure's instructions")
    p.add_argument("procedure", help="one of TCW's procedure names")
    p.add_argument("slug", nargs="?",
                   help=f"optional; {SLUG_HELP}, so the text is composed for it")
    p.add_argument("--no-exec", dest="no_exec", action="store_true",
                   help="report what would resolve; prints nothing on stdout")
    p.set_defaults(func=_procedure_prompt)

    p = cmds.add_parser("lifecycle", help="the enabled stages and their bindings")
    p.add_argument("slug", nargs="?",
                   help=f"optional; {SLUG_HELP}, to read its project's stages")
    p.add_argument("--json", action="store_true")
    p.add_argument("--stage")
    p.add_argument("--phase", choices=PHASES)
    p.add_argument("--directive", action="store_true",
                   help="one instruction line for an agent, or nothing when "
                        "unbound; needs --stage")
    p.set_defaults(func=_lifecycle)

    p = cmds.add_parser("docs", help="this project's documentation entries")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=_docs)

    p = cmds.add_parser("tags", help="this project's tag registry")
    verbs = p.add_subparsers(dest="tags_verb", required=True)
    verbs.add_parser("list", help="print the registered tags").set_defaults(
        func=_tags_list)
    for verb, func, what in (("add", _tags_add, "register"),
                             ("rm", _tags_rm, "unregister")):
        p = verbs.add_parser(verb, help=f"{what} one or more tags")
        p.add_argument("tag", nargs="+", type=_tags,
                       help="a tag, or comma-separated tags")
        p.set_defaults(func=func)

    p = cmds.add_parser("nodes", help="this project's parent and child projects")
    p.set_defaults(func=_nodes)

    p = cmds.add_parser("init", help="create this project's work folder")
    p.add_argument("--id", help="canonical project ID (required for a new project)")
    p.add_argument("--path", help="where the work store lives")
    p.set_defaults(func=_init)

