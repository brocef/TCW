"""The `tcw work` commands on the 3.0 model (TCW-70 Design 7).

Every stdout line is a full slug, a stage, a path, a record or composed text,
so a script can read it; everything said to a person goes to stderr. A failure
is a `TcwError` carrying its exit code, which `tcw.cli.main` turns into
`tcw work <command>: <message>` on stderr.
"""

from __future__ import annotations

import argparse
import sys
from datetime import timezone
from pathlib import Path

from tcw import exit as codes
from tcw.errors import NO_PROJECT, BackendError, NotFound, Refused, UsageError
from tcw.output import print_json, wrote
from tcw.store.base import normalize_tag
from tcw.store.fs import FsProjectRegistry, find_node_root
from tcw.stdin import read_piped_stdin
from tcw.work.advance import advance as advance_item, discard as discard_item
from tcw.work.backend import Query, WorkBackend
from tcw.work.fs_backend import FsWorkBackend, read_all
from tcw.work.jira.backend import KEY, JiraBackend
from tcw.work.jira.tickets import adopt, inbox, user_name
from tcw.work.gates import project_reader
from tcw.work.model import (
    STAGES, UNSET, Changes, Slug, completion_stage, inbox_stage, stage as table_stage,
    start_stage,
)
from tcw.work.open import (delegate, open_backend, open_for_update, open_project,
                           read_work_config)
from tcw.work.record import item_record

NAME = "work"


# -- finding the project and the item ---------------------------------------------


def project_root(here: Path | None = None) -> Path:
    root = find_node_root(here or Path.cwd())
    if root is None:
        raise BackendError(NO_PROJECT)
    return root


def resolve_item(arg: str, here: Path | None = None
                 ) -> tuple[Slug, WorkBackend, Path]:
    """The slug `arg` names, the backend that holds it, and this project's
    root. A full slug or a bare folder name, matched exactly; another
    project's slug opens that project for reading."""
    root = project_root(here)
    backend = open_backend(root)
    if isinstance(backend, JiraBackend) and isinstance(arg, str) and KEY.fullmatch(arg):
        # A ticket key typed where an item is named (TCW-71 Design 2.6).
        folder = backend.lookup(arg)
        if folder is None:
            raise NotFound(f"no work item here carries the Jira key {arg}")
        return Slug(backend.project, folder), backend, root
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


def _tag(value: str) -> str:
    """One tag per use (TCW-73 Design 2, decision 6). A comma is refused rather
    than split or normalized away: `--tag cli,docs` must not quietly become
    the one tag `cli-docs`."""
    if "," in value:
        raise argparse.ArgumentTypeError(
            f"{value!r} holds a comma; give one tag per use and repeat the "
            f"option for more")
    try:
        return normalize_tag(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError(str(error))


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
        if args.project == FsProjectRegistry.open(root).current.id:
            raise UsageError(f"--project {args.project} names this project; "
                             f"leave --project out to create the item here")
        given = [f for f in PROPERTY_FLAGS if getattr(args, f) is not None]
        if given:
            flag = "--" + given[0].replace("_", "-")
            raise UsageError(f"{flag} cannot be used with --project; only "
                             f"--priority can. Set it in that project afterwards")
        print(delegate(args.project, args.title, request, args.priority,
                       here=root, report=_say))
        return codes.OK
    backend = open_backend(root)
    if stage == inbox_stage() and not backend.inbox_items:
        raise UsageError(f"--stage {inbox_stage()} is for a filesystem-mode "
                         f"project; in Jira mode a new ticket waits in Jira "
                         f"until `tcw work tickets adopt` takes it")
    changes = Changes(
        priority=_optional(args.priority), effort=_optional(args.effort),
        complexity=_optional(args.complexity), assignee=_optional(args.assignee),
        parent=_optional(args.parent), add_tags=tuple(args.tag or ()),
        add_blocked_by=tuple(args.blocked_by or ()))
    # A failure after creation carries the name; `tcw.cli.main` prints it.
    item = backend.create(args.title, changes, stage=stage, request=request)
    print(item.slug)
    return codes.OK


def _list(args) -> int:
    for name in args.stage or ():
        table_stage(name)              # an unknown stage is a usage error
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
        print_json("items", [item_record(i, every, _layout(backend)) for i in items])
        return codes.OK
    for item in items:
        print(item.slug)
    return codes.OK


def _stamp(at) -> str:
    return at.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _person(backend: WorkBackend, account: str | None) -> str | None:
    """A person as the text form shows them: a Jira account's display name,
    falling back to the account ID (Design 1.9, R15)."""
    if account is None or not isinstance(backend, JiraBackend):
        return account
    return user_name(backend, account) or account


def _indented(text: str) -> list[str]:
    return [f"  {line}" if line else "" for line in text.rstrip("\n").split("\n")]


def _show(args) -> int:
    """The item's properties, its request and its comments, newest first: the
    whole item an agent needs to read (Design 1.9)."""
    slug, backend, _ = resolve_item(args.slug)
    item = backend.read(slug.folder)
    record = item_record(item, _readable(backend), _layout(backend))
    request = backend.read_request(slug.folder)
    comments = backend.read_comments(slug.folder)
    if args.json:
        print_json(None, {"item": record, "request": request, "comments": [
            {"at": _stamp(c.at), "author": c.author, "text": c.text}
            for c in comments]})
        return codes.OK
    lines = []
    for key, value in record.items():
        if key == "untracked" and not value:
            continue
        if key == "assignee":
            value = _person(backend, value)
        if isinstance(value, list):
            value = ", ".join(map(str, value))
        lines.append(f"{key}: {'' if value is None else value}")
    lines.append("")
    if request is None:
        lines.append("request: none")
    else:
        lines += ["request:", *_indented(request)]
    if comments:
        lines += ["", "comments:"]
        for c in comments:
            author = _person(backend, c.author)
            lines.append(f"- {_stamp(c.at)}" + (f" {author}" if author else ""))
            lines += _indented(c.text)
    print("\n".join(lines))
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
    if changes == Changes() and not targets:
        raise UsageError("nothing to change; give at least one property flag")
    own = _own(slug, backend, root)
    own.read(slug.folder)
    # Every target is opened and read before anything is written, so a
    # refused or missing one (exit 3 or 4) leaves every item as it was.
    blocked = []
    for target in targets:
        if target == slug:
            raise UsageError(f"{slug} cannot block itself")
        other = backend if target.project == slug.project else \
            open_for_update(target.project, root)
        other.read(target.folder)
        blocked.append((other, target))
    if changes != Changes():
        own.update(slug.folder, changes)
    for other, target in blocked:
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


def _tickets_list(args) -> int:
    tickets, query = inbox(open_backend(project_root()))
    if args.json:
        print_json("tickets", tickets)
    else:
        for ticket in tickets:
            print(ticket["key"])
    _say(f"{len(tickets)} ticket{'' if len(tickets) == 1 else 's'} waiting in Jira to "
         f"become items")
    _say(f"JQL: {query}")
    return codes.OK


def _tickets_adopt(args) -> int:
    root = project_root()
    backend = open_backend(root)
    slug, code = adopt(backend, args.key, config=backend.config,
                       layout=_layout(backend), project_root=root)
    print(slug)
    return code


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


def _procedure(args) -> int:
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
    return _print_resolution(res, f"tcw work procedure {args.procedure}",
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


def _lifecycle(args) -> int:
    """The stage table: every stage with its kind, whether this project enables
    it, and its bindings (Design 2, decision 4)."""
    config = open_backend(project_root()).config
    names = ([table_stage(args.stage).name] if args.stage is not None
             else [s.name for s in STAGES])
    if args.json:
        print_json(None, {
            "hooks": {"timeout": config.hooks.timeout,
                      "output-cap": config.hooks.output_cap},
            "stages": [{"name": name, "kind": table_stage(name).kind,
                        "enabled": name in config.enabled,
                        "bindings": {p: [_binding_json(b) for b in
                                         _phases(config, name)[p]]
                                     for p in PHASES}}
                       for name in names]})
        return codes.OK
    for i, name in enumerate(names):
        if i:
            print()
        state = "" if name in config.enabled else ", disabled"
        print(f"{name}  [{table_stage(name).kind}{state}]")
        rows = _phases(config, name)
        for phase in PHASES:
            if rows[phase]:
                refs = ", ".join(f"{b.kind}:{b.value}" if b.kind != "builtin"
                                 else "builtin" for b in rows[phase])
                print(f"  {phase + ':':8}{refs}")
    return codes.OK


def _docs(args) -> int:
    entries = open_backend(project_root()).config.documentation
    if args.json:
        print_json(None, {"source": "config" if entries else "agent-guide",
                          "entries": [{"path": e.path, "trigger": e.trigger,
                                       "description": e.description}
                                      for e in entries]})
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
    for tag in read_work_config(project_root()).tags:
        print(tag)
    return codes.OK


def _write_tags(change) -> int:
    """Rewrite `work.tags` in `tcw-config.yaml`, changing only its lines, and
    name the file on stderr when it changed. Prints nothing on stdout."""
    from tcw.store import config_edit
    from tcw.store.fs import SENTINEL, _atomic_write_all
    root = project_root()
    registered = set(read_work_config(root).tags)
    result = sorted(change(registered))
    if set(result) != registered:
        path = root / SENTINEL
        try:
            text = config_edit.edit_text(path, config_edit.read_text(path),
                                         [config_edit.SetList("work", "tags",
                                                              tuple(result))])
        except ValueError as error:
            raise BackendError(str(error)) from None
        if text is not None:
            _atomic_write_all([(path, text)])
            wrote(path)
    return codes.OK


def _tags_add(args) -> int:
    given = set(args.tag)
    return _write_tags(lambda tags: tags | given)


def _tags_rm(args) -> int:
    given = set(args.tag)
    return _write_tags(lambda tags: tags - given)


# -- the parser ------------------------------------------------------------------------------


def _properties(p: argparse.ArgumentParser, *, editing: bool) -> None:
    from tcw.work.model import PRIORITIES, SIZES
    clear = "; an empty value clears it" if editing else ""
    p.add_argument("--priority",
                   help=f"one of: {', '.join(PRIORITIES)}{clear}")
    p.add_argument("--effort", help=f"one of: {', '.join(SIZES)}{clear}")
    p.add_argument("--complexity", help=f"one of: {', '.join(SIZES)}{clear}")
    p.add_argument("--tag", type=_tag, action="append",
                   help="a registered tag; repeat the option for more")
    p.add_argument("--assignee", help=f"who the item is assigned to{clear}")
    p.add_argument("--parent", help=f"the item this one belongs under (a slug){clear}")
    p.add_argument("--blocked-by", dest="blocked_by", action="append",
                   help="an item that must finish first (a slug); repeat for more")
    if editing:
        p.add_argument("--title", type=_nonempty, help="a new title")
        p.add_argument("--untag", type=_tag, action="append",
                       help="a tag to take off; repeat the option for more")
        p.add_argument("--unblocked-by", dest="unblocked_by", action="append",
                       help="an item to take off blocked-by; repeat for more")
        p.add_argument("--blocks", action="append",
                       help="add this item to another item's blocked-by; repeat "
                            "for more")


def add_subparser(sub: argparse._SubParsersAction) -> None:
    from tcw.cli_help import command as leaf, group

    def command(verbs, name, *, examples, **kwargs):
        return leaf(verbs, name, examples=[f"work {e}" for e in examples], **kwargs)

    stages = ", ".join(s.name for s in STAGES)
    work = group(sub, NAME, help="work items")
    cmds = work.add_subparsers(dest="work_command", required=True)

    p = command(cmds, "new", help="create an item; text piped on stdin says what it "
                                  "asks for",
                prints="the new item's full slug (a ticket key when it stopped "
                       "after creating a ticket)",
                writes="the item, and in Jira mode its ticket",
                examples=["new 'Refund a payment' --priority high < ask.md",
                          "new 'Support SSO' --project platform --tag auth"])
    p.add_argument("title", help="the item's title; the folder name is made from it")
    p.add_argument("--project", help="create it in this connected project instead")
    p.add_argument("--stage", help=f"{inbox_stage()}, to start it there (filesystem "
                                   f"mode only)")
    _properties(p, editing=False)
    p.set_defaults(func=_new)

    p = command(cmds, "list", help="list items",
                prints="one full slug per line, or --json", writes="nothing",
                examples=["list", f"list --stage {start_stage()} --tag auth",
                          "list --all --json"])
    p.add_argument("--stage", action="append",
                   help=f"only items at this stage; repeat for more ({stages})")
    p.add_argument("--tag", type=_tag, action="append",
                   help="list items carrying this tag; repeat for any of several")
    p.add_argument("--parent", help="only items under this item (a slug)")
    p.add_argument("--assignee", help="only items assigned to this person")
    p.add_argument("--all", action="store_true",
                   help="include items that have ended")
    p.add_argument("--json", action="store_true",
                   help='print {"schema": 1, "items": [...]}')
    p.set_defaults(func=_list)

    p = command(cmds, "show", help="an item's record, what it asks for, and its "
                                   "comments",
                prints="the item's properties, what it asks for and its comments, "
                       "newest first, or --json", writes="nothing",
                examples=["show 2026-10-01-refund-a-payment",
                          "show 2026-10-01-refund-a-payment --json"])
    p.add_argument("slug", help=SLUG_HELP)
    p.add_argument("--json", action="store_true",
                   help="print one JSON object: the item, what it asks for, and "
                        "its comments")
    p.set_defaults(func=_show)

    p = command(cmds, "path", help="a path in the work store",
                prints="the path", writes="nothing",
                examples=["path", "path 2026-10-01-refund-a-payment",
                          f"path 2026-10-01-refund-a-payment {start_stage()} --next"])
    p.add_argument("slug", nargs="?",
                   help=f"{SLUG_HELP}; without one, the work store folder")
    p.add_argument("stage", nargs="?",
                   help="a stage whose folder or file to name")
    which = p.add_mutually_exclusive_group()
    which.add_argument("--next", action="store_true",
                       help="the stage's next round file")
    which.add_argument("--handoff", action="store_true",
                       help="the stage's handoff file")
    p.set_defaults(func=_path)

    p = command(cmds, "edit", help="change an item's properties", prints="nothing",
                writes="the item", examples=[
                    "edit 2026-10-01-refund-a-payment --priority low --tag billing",
                    "edit 2026-10-01-refund-a-payment --assignee ''"])
    p.add_argument("slug", help=SLUG_HELP)
    _properties(p, editing=True)
    p.set_defaults(func=_edit)

    p = command(cmds, "advance", help="move an item to its next stage",
                prints="the stage the item is at after the move; with --dry-run, "
                       "the target stage when the move would be allowed",
                writes="the item's stage, and the trace comment",
                examples=["advance 2026-10-01-refund-a-payment",
                          f"advance 2026-10-01-refund-a-payment --to {completion_stage()} "
                          f"--dry-run",
                          f"advance 2026-10-01-refund-a-payment --to {completion_stage()} "
                          f"--force --reason 'agreed in person'"])
    p.add_argument("slug", help=SLUG_HELP)
    p.add_argument("--to", help=f"the stage to move to (default: the next one; {stages})")
    p.add_argument("--force", action="store_true",
                   help="move past a refusing gate; needs --reason")
    p.add_argument("--reason", help="why, recorded in the trace comment")
    p.add_argument("--dry-run", dest="dry_run", action="store_true",
                   help="say where it would go; move nothing")
    p.set_defaults(func=_advance)

    p = command(cmds, "discard", help="abandon an item, with a reason",
                prints="the stage the item is at after the move",
                writes="the item's stage, and the trace comment",
                examples=["discard 2026-10-01-refund-a-payment --reason 'duplicate'"])
    p.add_argument("slug", help=SLUG_HELP)
    p.add_argument("--reason", required=True, help="why, recorded in the trace comment")
    p.set_defaults(func=_discard)

    p = command(cmds, "comment", help="add a comment; text from stdin",
                prints="nothing", writes="the comment",
                examples=["comment 2026-10-01-refund-a-payment < note.md"])
    p.add_argument("slug", help=SLUG_HELP)
    p.set_defaults(func=_comment)

    p = command(cmds, "rename", help="rename an item's folder",
                prints="the item's new full slug", writes="the item's folder name",
                examples=["rename 2026-10-01-refund-a-payment refund-an-order"])
    p.add_argument("slug", help=SLUG_HELP)
    p.add_argument("new_name", help="the new words after the date, lower case "
                                    "and hyphenated")
    p.set_defaults(func=_rename)

    p = group(cmds, "stage", help="read a stage's instructions")
    verbs = p.add_subparsers(dest="stage_verb", required=True)
    p = command(verbs, "prompt", help="print a stage's instructions, running no checks",
                prints="the instructions", writes="nothing",
                examples=[f"stage prompt {start_stage()}",
                          f"stage prompt {start_stage()} 2026-10-01-refund-a-payment"])
    p.add_argument("stage", help="a stage (`tcw work lifecycle` lists them)")
    p.add_argument("slug", nargs="?",
                   help=f"optional; {SLUG_HELP}, so the text is composed for it")
    p.add_argument("--no-exec", dest="no_exec", action="store_true",
                   help="report what would resolve; prints nothing on stdout")
    p.set_defaults(func=_stage_prompt)

    p = command(cmds, "procedure", help="print one of TCW's procedures, composed "
                                        "with this project's text",
                prints="the procedure's text", writes="nothing",
                examples=["procedure audit-backlog"])
    p.add_argument("procedure", help="one of TCW's procedure names")
    p.add_argument("slug", nargs="?",
                   help=f"optional; {SLUG_HELP}, so the text is composed for it")
    p.add_argument("--no-exec", dest="no_exec", action="store_true",
                   help="report what would resolve; prints nothing on stdout")
    p.set_defaults(func=_procedure)

    p = command(cmds, "lifecycle", help="the stage table and its bindings",
                prints="every stage with its kind, whether it is enabled, and its "
                       "bindings, or --json", writes="nothing",
                examples=["lifecycle", f"lifecycle --stage {start_stage()} --json"])
    p.add_argument("--stage", help=f"one stage only ({stages})")
    p.add_argument("--json", action="store_true",
                   help='print {"schema": 1, "hooks": {...}, "stages": [...]}')
    p.set_defaults(func=_lifecycle)

    p = command(cmds, "docs", help="this project's documentation entries",
                prints="the entries, or --json", writes="nothing",
                examples=["docs", "docs --json"])
    p.add_argument("--json", action="store_true",
                   help='print {"schema": 1, "source": ..., "entries": [...]}')
    p.set_defaults(func=_docs)

    p = group(cmds, "tags", help="this project's tag registry")
    verbs = p.add_subparsers(dest="tags_verb", required=True)
    command(verbs, "list", help="print the registered tags",
            prints="one tag per line", writes="nothing",
            examples=["tags list"]).set_defaults(func=_tags_list)
    for verb, func, what in (("add", _tags_add, "register"),
                             ("rm", _tags_rm, "unregister")):
        p = command(verbs, verb, help=f"{what} one or more tags", prints="nothing",
                    writes="tcw-config.yaml, named on stderr",
                    examples=[f"tags {verb} billing", f"tags {verb} billing auth"])
        p.add_argument("tag", nargs="+", type=_tag, help="a tag; one per argument")
        p.set_defaults(func=func)

    p = group(cmds, "tickets", help="Jira tickets that are not items yet (Jira mode "
                                    "only)")
    verbs = p.add_subparsers(dest="tickets_verb", required=True)
    p = command(verbs, "list", help="tickets waiting to become items",
                prints="one ticket key per line, or --json", writes="nothing",
                examples=["tickets list", "tickets list --json"])
    p.add_argument("--json", action="store_true",
                   help='print {"schema": 1, "tickets": [...]}')
    p.set_defaults(func=_tickets_list)
    p = command(verbs, "adopt", help="make a ticket an item",
                prints="the new item's full slug", writes="the item's folder, and "
                       "the ticket's TCW fields", examples=["tickets adopt TCW-42"])
    p.add_argument("key", help="the ticket's Jira key")
    p.set_defaults(func=_tickets_adopt)
