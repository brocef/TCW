"""The `tcw work` commands on the 3.0 model (TCW-70 Design 7).

Every stdout line is a full identifier, a stage, a path, a record or composed text,
so a script can read it; everything said to a person goes to stderr. A failure
is a `TcwError` carrying its exit code, which `tcw.cli.main` turns into
`tcw work <command>: <message>` on stderr.
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import replace
from datetime import timezone
from pathlib import Path

from tcw import exit as codes
from tcw.errors import (NO_PROJECT, BackendError, ConfigError, NotFound, Refused,
                        UsageError)
from tcw.ids import sort_input
from tcw.output import print_json, wrote
from tcw.scope import scope_options
from tcw.ownership import check_owned
from tcw.store.base import normalize_tag
from tcw.store.fs import FsProjectRegistry, find_project_root
from tcw.stdin import read_piped_stdin
from tcw.work.advance import advance as advance_item, discard as discard_item
from tcw.work.backend import Query, WorkBackend, folder_disagreement
from tcw.work.jira.backend import KEY, JiraBackend
from tcw.work.jira.tickets import adopt, inbox, user_name
from tcw.work.gates import project_reader
from tcw.work.model import (
    STAGES, UNSET, Changes, Slug, completion_stage, inbox_stage, stage as table_stage,
    start_stage,
)
from tcw.work.open import (existing_item, external_stages_of, name_item, open_backend,
                           project_facts, read_layered, read_work_config,
                           resolve_work_input)
from tcw.work.record import item_record, readable
from tcw.work.scoped import COUNTED_ACROSS

NAME = "work"


# -- finding the project and the item ---------------------------------------------


def project_root(here: Path | None = None) -> Path:
    root = find_project_root(here or Path.cwd())
    if root is None:
        raise BackendError(NO_PROJECT)
    return root


def resolve_item(arg: str, here: Path | None = None, *, writing: bool = False
                 ) -> tuple[Slug, WorkBackend, Path]:
    """The item `arg` names, the backend that holds it, and this project's
    root: a full identifier or its address, a folder name, or a tracker key,
    alone or in a full identifier (TCW-110 Design 3.1). Another project's
    item opens that project for reading.

    `writing` is for a command that changes the item: the ownership check
    (TCW-114 Design 1.1) is made on the project the text names before
    anything of that project is opened, so a write naming another project's
    item exits 3 whether or not that project can be read; text naming no
    project is looked up here, and what it names is checked too."""
    root = project_root(here)
    if writing:
        found = sort_input(arg, "work", KEY)
        if found.form in ("a", "c"):
            check_owned(found.full_id, root)
    slug, backend = resolve_work_input(arg, lambda: open_backend(root), root)
    if writing:
        check_owned(slug, root)
    return slug, backend, root


def _references(changes: Changes, backend: WorkBackend, root: Path) -> Changes:
    """`changes` with each item it names (`--parent`, `--blocked-by`,
    `--unblocked-by`) turned into that item's full identifier, read from its
    owner, so what is stored is the folder the backend holds however the
    item was typed (TCW-110 Design 3.3). A blocker being removed need not
    exist any more: removing a reference to a deleted item is how it is
    cleaned up."""
    def named(text) -> Slug:
        return existing_item(text, lambda: backend, root)[0]

    def sorted_(text) -> Slug:
        return resolve_work_input(text, lambda: backend, root)[0]
    parent = changes.parent
    if parent is not UNSET and parent is not None:
        parent = named(parent)
    return replace(changes, parent=parent,
                   add_blocked_by=tuple(named(t) for t in changes.add_blocked_by),
                   remove_blocked_by=tuple(sorted_(t) for t in changes.remove_blocked_by))


def _me(backend: WorkBackend) -> str:
    """Who is running the command, as the backend compares it with an item's
    assignee (TCW-72 Design 9). The CLI never interprets the value; with
    none configured, one message names every remedy, whatever the backend."""
    from tcw.config import LOCAL_FILE, user_config_label
    me = backend.current_user()
    if me is None:
        raise ConfigError(
            f"no identity is configured: set `user.name` in {user_config_label()} "
            f"or in {LOCAL_FILE}, or, in a Jira project, set the environment "
            f"variables named by `work.jira.credentials`")
    return me


def _alone(args, flag: str) -> None:
    """`--mine` and `--assign-me` each say who; `--assignee` beside one of
    them would say it twice."""
    if args.assignee is not None:
        raise UsageError(f"{flag} cannot be used with --assignee; give one of them")


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
    items, bad = readable(backend)
    if bad:
        _say("warning: these items could not be read, so blocks and children "
             "may be incomplete: " + ", ".join(bad))
    return items


def creation_stage(backend: WorkBackend, stage: str | None) -> str:
    """Where a new item starts: the start stage, or the inbox stage when
    `stage` names it and the backend keeps items there."""
    if stage is None:
        return start_stage()
    if stage != inbox_stage():
        raise UsageError(f"--stage accepts only {inbox_stage()}")
    if not backend.inbox_items:
        raise UsageError(f"--stage {inbox_stage()} is for a filesystem-mode "
                         f"project; in Jira mode a new ticket waits in Jira "
                         f"until `tcw work tickets adopt` takes it")
    return stage


def new_item(backend: WorkBackend, title: str, changes: Changes, *,
             stage: str | None, request: str | None, nest: bool = True):
    """Create an item in this project, where `creation_stage` says, and inside
    its parent's folder unless `nest` is false (`--flat`) or the parent is not
    an item of this project. What `new` and the web viewer both call."""
    return backend.create(title, changes, stage=creation_stage(backend, stage),
                          request=request, nest=nest)


def _quoted(text: str) -> str:
    """`text` as one shell word, for a command a message names."""
    import shlex
    return shlex.quote(text)


def _blocks_removed(args) -> UsageError:
    """TCW-114 Design 2.2's refusal of `--blocks`, naming the command that
    records the link on the blocked item. The first target is read only to
    word it: for another project's item the command runs in that project's
    folder, found without changing the exit, and names this item by its full
    identifier, since its folder name there would be one of that project's."""
    from tcw.ids import IdError
    from tcw.ownership import active_project_id
    target = args.blocks[0]
    blocker = args.slug
    where = ""
    try:
        found = sort_input(target, "work", KEY)
        owner = found.full_id.project if found.form in ("a", "c") else None
    except IdError:
        owner = None
    if owner is not None:
        folder = f"tcw://{owner}.path/"
        blocker = "<full id>"
        try:
            blocker = _quoted(_full_input(args.slug))
        except Exception:               # looking never changes the exit (2.2)
            pass
        try:
            root = project_root()
            if owner == active_project_id(root):
                folder, blocker = None, _quoted(args.slug)
            else:
                from tcw.locate import Locator
                locator = Locator.of(root)
                folder = str(locator.owner_root(owner, named_by=locator.root).resolve())
        except Exception:               # looking never changes the exit (2.2)
            pass
        where = f" -C {_quoted(folder)}" if folder else ""
    else:
        blocker = _quoted(blocker)
    return UsageError(f"work edit --blocks is removed in TCW 4: record it on the "
                      f"blocked item instead: tcw{where} work edit {_quoted(target)} "
                      f"--blocked-by {blocker}")


def _full_input(text: str) -> str:
    """Command input naming this project's item, as text another project
    reads the same way: a full identifier or an address as typed, and a
    folder's id-path or a tracker key with this project's ID before it, which
    the other project resolves in this one (TCW-110 Design 3.1). Its project's
    configuration is read; no backend is opened."""
    from tcw.ownership import active_project_id
    found = sort_input(text, "work", KEY)
    if found.form in ("a", "c"):
        return text
    return f"{active_project_id(project_root())}.work/{found.id_path or found.key}"


# -- commands ----------------------------------------------------------------------------


SLUG_HELP = ("the item: its full identifier (<project>.work/<id-path>), its "
             "id-path (its folder's path in the work store), or its tracker key")
PROPERTY_FLAGS = ("effort", "complexity", "tag", "assignee", "parent", "blocked_by")


def _new(args) -> int:
    root = project_root()
    if args.stage is not None and args.stage != inbox_stage():
        raise UsageError(f"--stage accepts only {inbox_stage()}")
    if args.assign_me:
        _alone(args, "--assign-me")
    if args.flat and args.parent is None:
        raise UsageError("--flat keeps a child's folder out of its parent's; "
                         "give the parent with --parent")
    if args.project:
        # Before the read of piped input and before anything is opened, so
        # the refusal never waits on either (TCW-114 Design 2.1).
        raise UsageError(f"work new --project is removed in TCW 4: an item is created "
                         f"in its own project; run tcw -C tcw://{args.project}.path/ "
                         f"work new {_quoted(args.title)} --parent <full id>")
    # Before the read of piped input too, so `--stage` refused in this
    # project never waits on it. Opening the backend makes no request.
    backend = open_backend(root)
    creation_stage(backend, args.stage)   # before `--assign-me` asks who
    request = read_piped_stdin()
    request = request if request.strip() else None
    assignee = _me(backend) if args.assign_me else _optional(args.assignee)
    changes = Changes(
        priority=_optional(args.priority), effort=_optional(args.effort),
        complexity=_optional(args.complexity), assignee=assignee,
        parent=_optional(args.parent), add_tags=tuple(args.tag or ()),
        add_blocked_by=tuple(args.blocked_by or ()))
    changes = _references(changes, backend, root)
    # A failure after creation carries the name; `tcw.cli.main` prints it.
    item = new_item(backend, args.title, changes, stage=args.stage, request=request,
                    nest=not args.flat)
    print(item.slug)
    return codes.OK


def _list(args) -> int:
    for name in args.stage or ():
        table_stage(name)              # an unknown stage is a usage error
    if args.mine:
        _alone(args, "--mine")
    root = project_root()
    covered = _covered(args, root)
    backend = open_backend(root)
    listed_here = covered is None or covered.active in {m.id for m in covered.wanted()}
    assignee = (_me(backend) if listed_here else None) if args.mine else args.assignee
    tags = frozenset(args.tag) if args.tag else None
    for tag in sorted(tags or ()):
        if tag not in backend.config.tags:
            _say(f"warning: tag '{tag}' is not in this project's registry")
    parent = existing_item(args.parent, lambda: backend, root)[0] if args.parent else None
    query = Query(stages=frozenset(args.stage) if args.stage else None,
                  parent=parent, assignee=assignee, tags=tags,
                  all=args.all)
    if covered is not None:
        return _list_scope(args, covered, backend, query, assignee)
    items = backend.list(query)
    if args.json:
        every = _readable(backend)
        print_json("items", [item_record(i, every, _layout(backend)) for i in items])
        return codes.OK
    for item in items:
        print(item.slug)
    return codes.OK


def _list_scope(args, covered, backend: WorkBackend, query: Query,
                assignee: str | None) -> int:
    """`list` over the projects a scope covers (TCW-113 Design 3.1, 3.2):
    each project's own items in scope order, `children` and `blocks`
    computed across the scope (Design 3.3)."""
    from tcw.config import effective
    from tcw.work.scoped import list_scope
    scoped = list_scope(covered, query, active=backend, active_assignee=assignee,
                        mine=args.mine,
                        me=lambda: effective(covered.root).user_name,
                        need_every=args.json)
    covered.warn("its work items are not listed", _say, besides=COUNTED_ACROSS)
    if scoped.bad:
        _say("warning: these items could not be read, so blocks and children "
             "may be incomplete: " + ", ".join(scoped.bad))
    if args.json:
        print_json(None, {"items": [item_record(i, scoped.every, _layout(b))
                                    for i, b in scoped.items()],
                          **_projects(covered)})
        return codes.OK
    for item, _ in scoped.items():
        print(item.slug)
    return codes.OK


def _covered(args, root: Path):
    """The projects a list or show command covers, or None for today's
    reading of the active project alone: `--scope own` with no
    `--project`. A `--project` the scope does not cover is refused here,
    before anything is read (Design 2.2)."""
    if args.scope == "own" and args.project is None:
        return None
    from tcw.scope import cover
    return cover(root, args.scope, args.project)


def _projects(covered) -> dict:
    """`projects` for a `--json` document, under a scope other than `own`."""
    projects = covered.projects_json()
    return {} if projects is None else {"projects": projects}


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
    root = project_root()
    found = sort_input(args.slug, "work", KEY)
    named = found.full_id.project if found.form in ("a", "c") else None
    if args.project is not None and named is not None and named != args.project:
        # Design 2.3: a full identifier names its own project's item.
        from tcw.scope import not_its_project
        raise not_its_project(args.slug, "an item", named, args.project)
    covered = _covered(args, root)
    active = None if covered is None else open_backend(root)
    if covered is None or named is not None:
        # A full identifier names that item wherever it is, outside any
        # catch (Design 1.7, 3.4); the scope decides only `children` and
        # `blocks`.
        slug, backend, _ = resolve_item(args.slug)
    else:
        slug, backend = _show_in_scope(args.slug, found, covered, active)
    item = backend.read(slug.folder)
    if covered is None:
        every = _readable(backend)
    else:
        from tcw.work.scoped import every_item
        every, bad = every_item(covered, active, backend if named is not None else None)
        covered.warn(COUNTED_ACROSS, _say)
        if bad:
            _say("warning: these items could not be read, so blocks and children "
                 "may be incomplete: " + ", ".join(bad))
    record = item_record(item, every, _layout(backend))
    request = backend.read_request(slug.folder)
    comments = backend.read_comments(slug.folder)
    if args.json:
        print_json(None, {"item": record, "request": request, "comments": [
            {"at": _stamp(c.at), "author": c.author, "text": c.text}
            for c in comments], **({} if covered is None else _projects(covered))})
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


def _show_in_scope(text: str, found, covered, active: WorkBackend
                   ) -> tuple[Slug, WorkBackend]:
    """The item a folder name or a ticket key names among the projects the
    scope keeps (Design 3.4): exactly one, or not found, or a usage error
    naming each."""
    from tcw.work.scoped import find_in_scope
    key = found.key if found.form == "b" else None
    matches = find_in_scope(covered, text, active=active, key=key,
                            id_path=None if key is not None else found.id_path)
    if len(matches) == 1:
        return matches[0]
    if not matches:
        raise NotFound(f"no work item {text} in --scope {covered.scope}, which covers "
                       f"{', '.join(m.id for m in covered.wanted())}")
    raise UsageError(f"'{text}' names {len(matches)} items in --scope {covered.scope}: "
                     f"{', '.join(str(slug) for slug, _ in matches)}; name one by its "
                     f"full identifier")


def _path(args) -> int:
    if args.slug is None:
        if args.stage or args.next or args.handoff:
            raise UsageError("name an item first")
        # The work path is the project's own: no store is opened for it, so
        # nothing the project inherits is read (TCW-109 Design 3.4).
        print(project_facts(project_root()).path)
        return codes.OK
    slug, backend, _ = resolve_item(args.slug)
    backend.read(slug.folder)
    print(_layout(backend).path(slug, args.stage, next=args.next,
                                handoff=args.handoff))
    return codes.OK


def _edit(args) -> int:
    if args.blocks:
        # Before anything is opened (TCW-114 Design 2.2).
        raise _blocks_removed(args)
    if args.assign_me:
        _alone(args, "--assign-me")
    slug, backend, root = resolve_item(args.slug, writing=True)
    changes = Changes(
        title=_optional(args.title), priority=_optional(args.priority),
        effort=_optional(args.effort), complexity=_optional(args.complexity),
        assignee=_optional(args.assignee), parent=_optional(args.parent),
        add_tags=tuple(args.tag or ()), remove_tags=tuple(args.untag or ()),
        add_blocked_by=tuple(args.blocked_by or ()),
        remove_blocked_by=tuple(args.unblocked_by or ()))
    if changes == Changes() and not args.assign_me:
        raise UsageError("nothing to change; give at least one property flag")
    own = backend
    own.read(slug.folder)
    changes = _references(changes, own, root)
    if args.assign_me:
        # Asked of this project's own backend, after the ownership check
        # has refused another project's item and the read has found it, and
        # before anything is written.
        changes = replace(changes, assignee=_me(own))
    if changes != Changes():
        updated = own.update(slug.folder, changes)
        if changes.parent is not UNSET:
            # Changing a parent never moves a folder (TCW-111 Design 3.4).
            if (warning := folder_disagreement(own, updated)):
                print(f"warning: {warning}", file=sys.stderr)
    return codes.OK


def _move(args, *, to=None, force=False, reason=None, dry_run=False) -> int:
    slug, backend, root = resolve_item(args.slug, writing=True)
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
    slug, backend, root = resolve_item(args.slug, writing=True)
    reader = project_reader(root, FsProjectRegistry.open(root))
    return _report(discard_item(backend, backend.config, _layout(backend), reader,
                                root, slug, args.reason))


def _comment(args) -> int:
    slug, backend, root = resolve_item(args.slug, writing=True)
    text = read_piped_stdin()
    if not text.strip():
        raise UsageError("pipe the comment text on stdin")
    backend.comment(slug.folder, text)
    return codes.OK


def _as_given(args, *words: str) -> str:
    """The command as typed, for a stopped move's "run the same command
    again" (TCW-114 Design 5.8)."""
    import shlex
    chdir = "".join(f" -C {shlex.quote(c)}" for c in getattr(args, "chdir", None) or [])
    return f"tcw{chdir} " + " ".join(shlex.quote(w) for w in words)


def _rename(args) -> int:
    from tcw.move import move_object
    command = _as_given(args, "work", "rename", args.slug, args.new_name)
    return move_object("work", args.slug, new_name=args.new_name, command=command,
                       as_json=args.json)


def _move_item(args) -> int:
    from tcw.move import move_object
    where = ["--top"] if args.top else ["--into", args.into]
    command = _as_given(args, "work", "move", args.slug, *where)
    return move_object("work", args.slug, into=args.into, top=args.top,
                       command=command, as_json=args.json)


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
    """`(config, external, project, item, record, request, layout, root)` for
    a composed prompt: the named item's, or, with no item, this project's,
    read without opening its store, so nothing it inherits is read (TCW-109
    Design 3.4). `external` is the backend kind's stages whose record it
    keeps, and `project` the ID of the project whose lists are composed."""
    if args.slug is None:
        root = project_root()
        facts = project_facts(root)
        config = facts.layered.work
        return (config, external_stages_of(config), facts.project, None, None, None,
                None, root)
    slug, backend, root = resolve_item(args.slug)
    item = backend.read(slug.folder)
    record = item_record(item, _readable(backend), _layout(backend))
    return (backend.config, backend.external_stages, backend.project, item, record,
            backend.read_request(slug.folder), _layout(backend), root)


def _personal_note(project: str, root: Path, key_path: tuple) -> None:
    """Say on stderr when a personal file set the list being composed (TCW-72
    Design 7.3). Only for the project the command acts on: another
    project's lists never come from this person's files."""
    from tcw.config import effective
    from tcw.output import shown
    if project != project_facts(root).project:
        return
    config = effective(root)
    named = [shown(f) for f in config.personal_files(key_path)]
    named += config.personal_variables(key_path)
    if named:
        _say("note: this prompt was changed by personal configuration: "
             + ", ".join(named))


def _print_resolution(res, label: str, no_exec: bool) -> int:
    """The composed text on stdout, or with `--no-exec` the plan on stderr and
    nothing on stdout. `label` names what was composed (`stage spec`); a note
    never starts with the command's words, which mark an error (Design 1.3)."""
    if no_exec:
        _say(f"note: {label}: --no-exec, nothing was resolved")
        for entry in res.plan:
            state = "matched" if entry.matched else "skipped (condition)"
            detail = f": {entry.ref}" if entry.kind != "builtin" else ""
            _say(f"  {entry.kind} — {state}{detail}")
        return codes.OK
    if res.text:
        print(res.text)
    elif res.plan and not any(entry.matched for entry in res.plan):
        _say(f"note: every binding of {label} carries a when: that did not "
             f"match, so nothing resolved")
    return codes.OK


def _resolved(compose_call):
    from tcw.work.resolve import ResolveError
    try:
        return compose_call()
    except ResolveError as error:
        raise BackendError(str(error)) from None


def _stage_prompt(args) -> int:
    from tcw.work.resolve import stage_footer, stage_header, stage_prompt
    step = table_stage(args.stage)
    if not step.prompt:
        raise UsageError(f"'{step.name}' has no instructions; it is where an item "
                         f"ends, not a stage worked in")
    if step.name == inbox_stage() and args.slug is not None:
        raise UsageError(f"'{step.name}' runs before an item exists and takes no "
                         f"work item; run it with no argument")
    config, external, project, item, record, request, layout, root = _prompt_target(args)
    if step.name not in config.enabled:
        _say(f"note: '{step.name}' is disabled in this project; printing its "
             f"instructions because you asked to read them")
    res = _resolved(lambda: stage_prompt(
        config, step.name, item=item, record=record, request=request,
        layout=layout, project_root=root, execute=not args.no_exec))
    _personal_note(project, root, ("work", "stages", step.name, "prompt"))
    label = f"stage {step.name}"
    if not args.no_exec and res.text:
        parts = [stage_header("<slug>"), res.text]
        footer = stage_footer(step, external, "<slug>")
        if footer is not None:
            parts.append(footer)
        res.text = "\n\n".join(parts)
        if item is not None:
            # Every `<slug>` in the output names this item (TCW-74 Design
            # 4.2): the same full identifier hooks receive as TCW_SLUG.
            res.text = res.text.replace("<slug>", str(item.slug))
    return _print_resolution(res, label, args.no_exec)


def _procedure(args) -> int:
    from tcw.store.base import PROCEDURE_IDS
    from tcw.work.resolve import packaged_text, procedure_prompt
    if args.procedure not in PROCEDURE_IDS:
        raise UsageError(f"unknown procedure '{args.procedure}'; expected one of "
                         f"{', '.join(PROCEDURE_IDS)}")
    if args.slug is None and find_project_root(Path.cwd()) is None:
        # No project, so nothing to compose: TCW's own text, with every
        # backend passage removed since there is no backend (TCW-74 Design
        # 3.2). Skills that also run outside TCW projects (documentation-sync)
        # rely on this.
        from tcw.work.passages import filter_backend
        print(filter_backend(packaged_text("procedures", args.procedure),
                             None).rstrip())
        return codes.OK
    config, _, project, item, record, request, layout, root = _prompt_target(args)
    res = _resolved(lambda: procedure_prompt(
        config, args.procedure, item=item, record=record,
        request=request, layout=layout, project_root=root,
        execute=not args.no_exec))
    _personal_note(project, root, ("work", "procedures", args.procedure))
    return _print_resolution(res, f"procedure {args.procedure}",
                             args.no_exec)


PHASES = ("pre", "prompt", "post")


def _binding_json(b) -> dict:
    out: dict = {b.kind: True if b.kind == "builtin" else b.value}
    if b.when is not None:
        out["when"] = {k: list(v) for k, v in
                       (("tags", b.when.tags), ("not-tags", b.when.not_tags)) if v}
    return out


def _phases(config, name: str) -> dict:
    """A stage's three resolved binding lists."""
    settings = config.stage(name)
    return {"pre": settings.pre or (), "prompt": settings.prompt or (),
            "post": settings.post or ()}


def _lifecycle(args) -> int:
    """The stage table: every stage with its kind, whether this project enables
    it, and its bindings (Design 2, decision 4). The stages are the project's
    own, so no store is opened (TCW-109 Design 3.4)."""
    config = project_facts(project_root()).layered.work
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
    entries = project_facts(project_root()).layered.work.documentation
    if args.json:
        print_json(None, {"source": "config" if entries else "agent-guide",
                          "entries": [{"path": e.path, "trigger": e.trigger,
                                       "description": e.description}
                                      for e in entries]})
        return codes.OK
    if not entries:
        _say("this project declares no `work.documentation`; documentation "
             "entries come from the project's agent guide (`AGENTS.md` or "
             "`CLAUDE.md`).")
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


class _Tags:
    """The tags of the project a tag command acts on (TCW-109 Design 6): the
    merged list, which raises exit 7 or 1 when it cannot be used; the
    project's own list in its shared file, and whether it holds an
    `inherit: true` entry; and which tags reach it from another project."""

    def __init__(self, root: Path):
        from tcw.config import read_project_file
        config = read_layered(root)
        self.root = root
        self.merged = set(config.work.tags)
        own_id = config.sources[-1] if config.sources else None
        raw, _ = read_project_file(root)
        work = raw.get("work") if isinstance(raw, dict) else None
        listed = work.get("tags") if isinstance(work, dict) else None
        self.absent = not isinstance(listed, list)
        entries = listed if isinstance(listed, list) else []
        self.inherit = any(isinstance(e, dict) and e.get("inherit") is True
                           for e in entries)
        self.own = {normalize_tag(e) for e in entries if isinstance(e, str)}
        self.has_source = len(config.sources) > 1
        values = config.values.get("work", {}).get("tags") or []
        self.inherited: dict[str, str] = {}
        for i, value in enumerate(values):
            origin = config.origins.get(("work", "tags", i))
            if (isinstance(value, str) and origin is not None
                    and origin.project not in (None, own_id)):
                self.inherited[normalize_tag(value)] = origin.project

    def write(self, own: set, inherit: bool) -> int:
        """Rewrite `work.tags` in `tcw-config.yaml` as `own`, sorted, after an
        `inherit: true` entry when `inherit`, changing only its lines, and
        name the file on stderr when it changed. Prints nothing on stdout."""
        from tcw.store import config_edit
        from tcw.store.fs import SENTINEL, _atomic_write_all
        path = self.root / SENTINEL
        try:
            text = config_edit.edit_text(path, config_edit.read_text(path),
                                         [config_edit.SetList("work", "tags",
                                                              tuple(sorted(own)),
                                                              inherit=inherit)])
        except ValueError as error:
            raise BackendError(str(error)) from None
        if text is not None:
            _atomic_write_all([(path, text)])
            wrote(path)
        return codes.OK


def _tags_add(args) -> int:
    """Add the tags not already registered to the project's own list. A
    project with another source and no list of its own gets an `inherit:
    true` entry first, so it keeps following its parents (TCW-109 Design
    6.2)."""
    tags = _Tags(project_root())
    new = {normalize_tag(t) for t in args.tag} - tags.merged
    if not new:
        return codes.OK
    return tags.write(tags.own | new, tags.inherit or (tags.absent and tags.has_source))


def _tags_rm(args) -> int:
    """Refuse the whole call, writing nothing, when any tag given is not
    registered: not found (4), naming each one (Design 2 decision 6); or
    when one would stay registered because a parent passes it: refused (3,
    TCW-109 Design 6.3)."""
    tags = _Tags(project_root())
    given = {normalize_tag(t) for t in args.tag}
    missing = sorted(given - tags.merged)
    if missing:
        raise NotFound("no such tag" + ("s" if len(missing) > 1 else "")
                       + ": " + ", ".join(f"'{t}'" for t in missing))
    if tags.absent or tags.inherit:
        for tag in sorted(given):
            if tag in tags.inherited:
                raise Refused(f"tag '{tag}' is inherited from '{tags.inherited[tag]}'; "
                              f"to drop it, list this project's tags under work.tags in "
                              f".tcw/tcw-config.yaml without an 'inherit: true' entry")
    if not given & tags.own:
        return codes.OK
    return tags.write(tags.own - given, tags.inherit)


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
    p.add_argument("--assign-me", dest="assign_me", action="store_true",
                   help="assign it to you: user.name, or your Jira account")
    p.add_argument("--parent", help=f"the item this one belongs under (an item: its full "
                        f"identifier or folder name){clear}")
    p.add_argument("--blocked-by", dest="blocked_by", action="append",
                   help="an item that must finish first (an item: its full "
                        "identifier or folder name); repeat for more")
    if editing:
        p.add_argument("--title", type=_nonempty, help="a new title")
        p.add_argument("--untag", type=_tag, action="append",
                       help="a tag to take off; repeat the option for more")
        p.add_argument("--unblocked-by", dest="unblocked_by", action="append",
                       help="an item to take off blocked-by; repeat for more")
        # Removed in TCW 4; kept only to say so (TCW-114 Design 2.2).
        p.add_argument("--blocks", action="append", help=argparse.SUPPRESS)


def add_subparser(sub: argparse._SubParsersAction) -> None:
    from tcw.cli_help import command as leaf, group

    def command(verbs, name, *, examples, **kwargs):
        return leaf(verbs, name, examples=[f"work {e}" for e in examples], **kwargs)

    stages = ", ".join(s.name for s in STAGES)
    work = group(sub, NAME, help="work items")
    cmds = work.add_subparsers(dest="work_command", required=True)

    p = command(cmds, "new", help="create an item; text piped on stdin says what it "
                                  "asks for",
                prints="the new item's full identifier (a ticket key when it "
                       "stopped after creating a ticket)",
                writes="the item, and in Jira mode its ticket",
                examples=["new 'Refund a payment' --priority high < ask.md",
                          "new 'Support SSO' --parent planning.work/2026-10-01-sso "
                          "--tag auth",
                          "new 'Part' --parent 2026-10-01-epic --flat"])
    p.add_argument("title", help="the item's title; the folder name is made from it")
    # Removed in TCW 4; kept only to say so (TCW-114 Design 2.1).
    p.add_argument("--project", help=argparse.SUPPRESS)
    p.add_argument("--stage", help=f"{inbox_stage()}, to start it there (filesystem "
                                   f"mode only)")
    _properties(p, editing=False)
    p.add_argument("--flat", action="store_true",
                   help="make the new item's folder at the top of the work folder "
                        "rather than inside its parent's; with --parent, whose "
                        "folder holds the new one by default when the parent is "
                        "an item of this project")
    p.set_defaults(func=_new)

    p = command(cmds, "list", help="list items",
                prints="one full identifier per line, or --json", writes="nothing",
                examples=["list", f"list --stage {start_stage()} --tag auth",
                          "list --all --json", "list --scope down --json"])
    p.add_argument("--stage", action="append",
                   help=f"only items at this stage; repeat for more ({stages})")
    p.add_argument("--tag", type=_tag, action="append",
                   help="list items carrying this tag; repeat for any of several")
    p.add_argument("--parent", help="only items under this item (an item: its "
                                   "full identifier or folder name)")
    p.add_argument("--assignee", help="only items assigned to this person")
    p.add_argument("--mine", action="store_true",
                   help="only items assigned to you: user.name, or your Jira account")
    p.add_argument("--all", action="store_true",
                   help="include items that have ended")
    scope_options(p)
    p.add_argument("--json", action="store_true",
                   help='print {"schema": 2, "items": [...]}, and "projects" when '
                        'the scope is not own')
    p.set_defaults(func=_list)

    p = command(cmds, "show", help="an item's record, what it asks for, and its "
                                   "comments",
                prints="the item's properties, what it asks for and its comments, "
                       "newest first, or --json", writes="nothing",
                examples=["show 2026-10-01-refund-a-payment",
                          "show 2026-10-01-refund-a-payment --json",
                          "show 2026-10-01-refund-a-payment --scope down"])
    p.add_argument("slug", help=SLUG_HELP)
    scope_options(p)
    p.add_argument("--json", action="store_true",
                   help="print one JSON object: the item, what it asks for, and "
                        "its comments, and \"projects\" when the scope is not own")
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

    p = command(cmds, "rename", help="rename an item's folder, and every item nested "
                                     "in it",
                prints="one `<old full id> -> <new full id>` line per identifier it "
                       "changed, the item first",
                writes="the item's folder name, the references that name it in this "
                       "project, and in Jira each moved ticket's TCW Item",
                examples=["rename 2026-10-01-refund-a-payment refund-an-order"])
    p.add_argument("slug", help=SLUG_HELP)
    p.add_argument("new_name", help="the new words after the date or key, lower case "
                                    "and hyphenated")
    p.add_argument("--json", action="store_true",
                   help="print the changed identifiers as JSON")
    p.set_defaults(func=_rename)

    p = command(cmds, "move", help="move an item's folder into another folder, or to "
                                   "the top; the items nested in it move with it",
                prints="one `<old full id> -> <new full id>` line per identifier it "
                       "changed, the item first",
                writes="the item's folder place, the references that name it in this "
                       "project, and in Jira each moved ticket's TCW Item",
                examples=["move 2026-10-01-refund-a-payment --into 2026-09-01-payments",
                          "move 2026-09-01-payments/2026-10-01-refund-a-payment --top"])
    p.add_argument("slug", help=SLUG_HELP)
    place = p.add_mutually_exclusive_group(required=True)
    place.add_argument("--into", metavar="<id-path>",
                       help="an item, or an organising folder (made when missing), "
                            "to put the item's folder in")
    place.add_argument("--top", action="store_true",
                       help="put the item's folder at the top of the work folder")
    p.add_argument("--json", action="store_true",
                   help="print the changed identifiers as JSON")
    p.set_defaults(func=_move_item)

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
                   help='print {"schema": 2, "hooks": {...}, "stages": [...]}')
    p.set_defaults(func=_lifecycle)

    p = command(cmds, "docs", help="this project's documentation entries",
                prints="the entries, or --json", writes="nothing",
                examples=["docs", "docs --json"])
    p.add_argument("--json", action="store_true",
                   help='print {"schema": 2, "source": ..., "entries": [...]}')
    p.set_defaults(func=_docs)

    p = group(cmds, "tags", help="this project's tag registry")
    verbs = p.add_subparsers(dest="tags_verb", required=True)
    command(verbs, "list", help="print the registered tags",
            prints="one tag per line", writes="nothing",
            examples=["tags list"]).set_defaults(func=_tags_list)
    for verb, func, what in (("add", _tags_add, "register"),
                             ("rm", _tags_rm, "unregister")):
        p = command(verbs, verb, help=f"{what} one or more tags", prints="nothing",
                    writes=".tcw/tcw-config.yaml, named on stderr",
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
                   help='print {"schema": 2, "tickets": [...]}')
    p.set_defaults(func=_tickets_list)
    p = command(verbs, "adopt", help="make a ticket an item",
                prints="the new item's full identifier", writes="the item's folder, and "
                       "the ticket's TCW fields", examples=["tickets adopt TCW-42"])
    p.add_argument("key", help="the ticket's Jira key")
    p.set_defaults(func=_tickets_adopt)
