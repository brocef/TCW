"""`tcw capabilities` — the user stories. Path-addressed folder capabilities.

stdout carries each command's product and nothing else (TCW-73 Design 1):
`add` prints the new capability's full identifier, `list` and `search` one
full identifier per line (`<project>.capabilities/<path>`, TCW-110 Design 4),
`show` the record, `path` the store folder; `set`, `reset` and `rm` print
nothing. Every file a write changed is named on stderr, and so is each warning
about the project's view (TCW-112 Design 3.2). A failure is raised for the
top-level handler to print and turn into its exit code.
"""

import argparse
import sys

from tcw import exit as codes
from tcw.cli_help import command, group
from tcw.errors import BackendError, InheritedUnavailable, UsageError
from tcw.locate import find_tree_writable
from tcw.output import changed, own_only, print_json, say
from tcw.scope import scope_options
from tcw.tree_scope import (LEFT_OUT, active_store, capability_detail, covered_for,
                            print_rows, refuse_local, scope_keys, show_lines, show_row)
from tcw.stdin import read_piped_stdin
from tcw.store.base import CAP_STATUSES, Capability
from tcw.store.fs import FsCapabilitiesStore, find_component_project, no_store_here

NAME = "capabilities"


def _missing() -> BackendError:
    return no_store_here(NAME)


def _project():
    project = find_component_project(NAME)
    if project is None:
        raise _missing()
    return project


def _store() -> FsCapabilitiesStore:
    return FsCapabilitiesStore.open(_project())


def _fmt(v) -> str:
    return ", ".join(v) if isinstance(v, list) else str(v)


def _covered(args: argparse.Namespace):
    return covered_for(args, NAME, _missing)


def _list(args: argparse.Namespace) -> int:
    refuse_local(args)
    return print_rows(_covered(args), NAME, args.json, status=args.status,
                      namespace=args.namespace)


def _search(args: argparse.Namespace) -> int:
    return print_rows(_covered(args), NAME, args.json, query=args.query)


def _show(args: argparse.Namespace) -> int:
    covered = _covered(args)
    st = active_store(covered, NAME)
    row = show_row(covered, NAME, args.id, say=say)
    cap = row.obj
    covered.warn(LEFT_OUT[NAME][1], say)
    if cap.partial and st.view_error is not None:
        own_only(st.view_error, st.project_id)
    if args.json:
        projects = covered.projects_json()
        print_json(None, {"capability": {**capability_detail(cap), **scope_keys(row)},
                          **({} if projects is None else {"projects": projects})})
        return codes.OK
    overridden, block = show_lines(covered, row)
    lines = [f"full-id: {cap.full_id}", f"owner: {cap.owner}",
             *([f"parent: {cap.parent}"] if cap.parent is not None else []),
             *([f"overrides: {cap.overrides}"] if cap.overrides is not None else []),
             *overridden,
             *(["partial: inherited content could not be read"] if cap.partial else []),
             f"name: {cap.name}"]
    lines += [f"{k}: {_fmt(v)}" for k, v in cap.fields.items()]
    lines += block
    body = cap.body.strip()
    if body:
        lines += ["", "body:", *(f"  {line}" if line else "" for line in body.splitlines())]
    print("\n".join(lines))
    return codes.OK


def _path(args: argparse.Namespace) -> int:
    print(_store().root)
    return codes.OK


def _add(args: argparse.Namespace) -> int:
    if args.flat and not args.parent:
        raise UsageError("--flat keeps a child's folder out of its parent's; "
                         "give the parent with --parent")
    st = _store()
    cap = st.add(args.path, name=args.name, status=args.status, body=read_piped_stdin(),
                 parent=args.parent, flat=args.flat, report=say)
    changed(st.changed)
    _warn_folder(st, cap)
    print(cap.full_id)
    return codes.OK


def _warn_folder(st: FsCapabilitiesStore, cap: Capability) -> None:
    """Design 3.2's warning on standard error, when the capability's folder
    sits in another's that its `parent` does not name (TCW-111 Design 3.3)."""
    if cap.origin == "local" and (warning := st.folder_disagreement(cap)):
        print(f"warning: {warning}", file=sys.stderr)


def _fields(args: argparse.Namespace, *, alone: bool = False) -> dict:
    """`--status` and each `--field K=V`, one field per use. A key given twice,
    `--status` together with `--field Status=`, or a `--field` with no `=` is
    a usage error; the value is kept whole, as the record file writes it, and
    an empty one is None, which clears the field."""
    fields: dict = {}
    pairs = [("Status", args.status)] if args.status else []
    for kv in args.field or []:
        if "=" not in kv:
            raise UsageError(f"--field takes K=V, got '{kv}'")
        k, v = kv.split("=", 1)
        # An empty value is the clear value (TCW-112 plan Step 8): written
        # as `null`, which removes an inherited value too.
        pairs.append((k.strip(), v.strip() or None))
    for k, v in pairs:
        if k in fields:
            raise UsageError(f"field '{k}' given more than once")
        fields[k] = v
    if not fields and not alone:
        raise UsageError("give --status, --parent or at least one --field")
    return fields


def _set(args: argparse.Namespace) -> int:
    fields = _fields(args, alone=args.parent is not None)
    st = _store()
    # What is refused is decided once, by `override_target` (TCW-112 choice
    # 9); the store's `set` resolves the same input the same way, since the
    # project's own full identifier of an object not yet written is not
    # input it accepts (Design 3.1).
    find_tree_writable(st, args.id, removing=False)
    cap = st.set(args.id, fields, parent=args.parent)
    changed(st.changed)
    if args.parent is not None:
        _warn_folder(st, cap)
    return codes.OK


def _reset(args: argparse.Namespace) -> int:
    st = _store()
    find_tree_writable(st, args.id, removing=False)
    try:
        st.reset(args.id)
    finally:
        # A removal that stops partway has still deleted files; name them.
        changed(st.changed)
    return codes.OK


def _rm(args: argparse.Namespace) -> int:
    st = _store()
    target = find_tree_writable(st, args.id, removing=True)
    try:
        st.remove(target)
    finally:
        # A removal that stops partway has still deleted files; name them.
        changed(st.changed)
    _now_shows(st, target)
    return codes.OK


def _now_shows(st, target) -> None:
    """After an override is removed, what its id-path shows (TCW-112 Design
    4.4), on standard error; nothing when the view cannot be built."""
    try:
        now = st.get_view(target.id_path)
    except (InheritedUnavailable, BackendError):
        return
    if now is not None:
        say(f"{target.id_path} now shows {now.full_id}")


def _drift(args: argparse.Namespace) -> int:
    """Capabilities that drifted from what the work says (TCW-73 Design 7):
    inherited ones never ruled on here, then what completed work items
    declared in their `capabilities.yaml` that today's records do not show.
    One finding per stdout line, `<kind>: <path>: <message>`; nothing when
    clean; exit 1 on any finding. Read-only."""
    project = _project()
    st = FsCapabilitiesStore.open(project)
    found = 0
    # Printed before the completed-work half reads anything, so an
    # unreachable Jira (exit 5) still leaves these on stdout.
    for c in st.unreviewed_inherited():
        print(f"unreviewed: {c.full_id}: inherited, and its status is still the "
              f"one it inherits; never ruled on here")
        found += 1
    sys.stdout.flush()
    for problem in _completed_work_drift(project):
        print(problem)
        found += 1
    return codes.ERROR if found else codes.OK


def _completed_work_drift(project) -> list:
    """What the completed items declared in `capabilities.yaml` that today's
    records no longer show, through TCW-69's `drift_problems`. The completed
    items come from the backend, so in Jira mode this asks Jira and an
    unreachable Jira propagates (exit 5). A project with no work component
    says so on stderr and contributes nothing. It never reads a `Planning
    doc` field."""
    from tcw.store.fs import FsProjectRegistry, _has_work_store
    from tcw.work.backend import Query
    from tcw.work.fs_backend import FsWorkBackend, read_all
    from tcw.work.gates import DriftProblem, drift_problems, project_reader
    from tcw.work.model import completion_stage
    from tcw.work.open import open_backend

    if not _has_work_store(project):
        print("completed-work drift was not checked: this project has no work "
              "component", file=sys.stderr)
        return []
    backend = open_backend(project)
    finished_stage = completion_stage()
    problems = []
    if isinstance(backend, FsWorkBackend):
        # Read directly rather than through `list`, which refuses the whole
        # board for one unreadable item: here that item is one finding.
        items, unreadable = read_all(backend.work_path, backend.project, backend.enabled)
        finished = [i for i in items if i.stage == finished_stage]
        problems += [DriftProblem("unchecked", str(u.path),
                                  f"cannot be read, so its declarations were not "
                                  f"checked: {u.message}") for u in unreadable]
    else:
        finished = backend.list(Query(stages=frozenset({finished_stage})))
    if finished:
        registry = FsProjectRegistry.open(project)
        problems += drift_problems(backend.layout, finished,
                                   project_reader(project, registry))
    return problems


def add_subparser(sub: argparse._SubParsersAction) -> None:
    p = group(sub, NAME, help="the user stories — what a user can do")
    g = p.add_subparsers(dest="cmd", required=True)

    pl = command(g, "list", help="every capability's full identifier",
                 prints="one full identifier per line, or --json", writes="nothing",
                 examples=["capabilities list", "capabilities list --status Missing",
                           "capabilities list --namespace billing --json",
                           "capabilities list --scope down --json"])
    pl.add_argument("--status", choices=sorted(CAP_STATUSES),
                    help="only capabilities with this status")
    pl.add_argument("--namespace", help="only capabilities under this namespace folder")
    pl.add_argument("--local", action="store_true", help=argparse.SUPPRESS)
    scope_options(pl)
    pl.add_argument("--json", action="store_true",
                    help='print {"schema": 2, "capabilities": [...]}, and "projects" '
                         'when the scope is not own')
    pl.set_defaults(func=_list)

    ps = command(g, "show", help="read a capability", prints="the record, or --json",
                 writes="nothing", examples=["capabilities show billing/refund",
                                             "capabilities show shared.capabilities/web/login "
                                             "--json",
                                             "capabilities show web/login --scope down"])
    ps.add_argument("id", metavar="path",
                    help="the capability: its full identifier "
                         "(<project>.capabilities/<path>), or its path in this "
                         "project, e.g. web/login")
    scope_options(ps)
    ps.add_argument("--json", action="store_true",
                    help='print {"schema": 2, "capability": {...}}, and "projects" when '
                         'the scope is not own')
    ps.set_defaults(func=_show)

    command(g, "path", help="print the capabilities store folder", prints="the folder",
            writes="nothing", examples=["capabilities path"]).set_defaults(func=_path)

    pa = command(g, "add", help="create a capability; its body is read from stdin",
                 prints="the new capability's full identifier",
                 writes="the capability's files, each named on stderr",
                 examples=["capabilities add billing/refund",
                           "capabilities add billing/refund 'Refund a payment' "
                           "--status Supported",
                           "capabilities add bulk --parent billing/invoices"])
    pa.add_argument("path",
                    help="path for the new capability: namespace folder first, or "
                         "with --parent one name inside the parent's folder (the "
                         "parent's path, / and one name is used as given)")
    pa.add_argument("name", nargs="?",
                    help="display name (default: titled from the last path segment)")
    pa.add_argument("--status", default="Missing", choices=sorted(CAP_STATUSES),
                    help="initial status (default: Missing)")
    pa.add_argument("--parent", help="the capability this one belongs under; its full "
                                     "identifier or its path here; the folder is made "
                                     "inside it when it is this project's own or "
                                     "this project overrides it, else the path is "
                                     "read as given")
    pa.add_argument("--flat", action="store_true",
                    help="with --parent: read the path as the whole path, namespace "
                         "folder first, not inside the parent's folder; the parent "
                         "is recorded all the same")
    pa.set_defaults(func=_add)

    pset = command(g, "set", help="change a capability's status or fields",
                   prints="nothing", writes="the record, named on stderr",
                   examples=["capabilities set billing/refund --status Supported",
                             "capabilities set billing/refund --field Subject=invoice,payment"])
    pset.add_argument("id", metavar="path",
                      help="the capability to update: its full identifier or its path; "
                           "for an inherited one, this project's own capability at the "
                           "same path is written, holding only what is given")
    pset.add_argument("--status", choices=sorted(CAP_STATUSES),
                      help="the same as --field Status=<status>")
    pset.add_argument("--field", action="append", metavar="K=V",
                      help="set one metadata field; repeat for more fields "
                           "(a list field such as Subject takes a,b,c; an empty "
                           "value clears the field)")
    pset.add_argument("--parent", help="the capability this one belongs under; its full "
                                       "identifier or its path here; an empty value "
                                       "clears it")
    pset.set_defaults(func=_set)

    prst = command(g, "reset", help="drop a local override, inheriting again",
                   prints="nothing", writes="removes the override, named on stderr",
                   examples=["capabilities reset web/login",
                             "capabilities reset shared.capabilities/web/login"])
    prst.add_argument("id", metavar="path", help="the overridden capability: its path, "
                                                 "this project's full identifier, or the "
                                                 "full identifier of the capability it "
                                                 "overrides")
    prst.set_defaults(func=_reset)

    prm = command(g, "rm", help="remove a local capability, an override included",
                  prints="nothing",
                  writes="removes its files, each named on stderr",
                  examples=["capabilities rm billing/refund"])
    prm.add_argument("id", metavar="path", help="the local capability to remove: its "
                                                "full identifier or its path")
    prm.set_defaults(func=_rm)

    from tcw.move import add_tree_commands
    add_tree_commands(g, command, "capabilities", "capability", "capabilities rename billing/refund return",
                      "capabilities move billing/refund --into payments")

    pse = command(g, "search", help="capabilities whose name or body holds the text",
                  prints="one full identifier per line, or --json", writes="nothing",
                  examples=["capabilities search refund",
                            "capabilities search refund --scope up"])
    pse.add_argument("query", help="text matched case-insensitively in names + bodies")
    scope_options(pse)
    pse.add_argument("--json", action="store_true",
                     help='print {"schema": 2, "capabilities": [...]}, and "projects" '
                          'when the scope is not own')
    pse.set_defaults(func=_search)

    pd = command(g, "drift", help="inherited capabilities never ruled on, and what "
                                  "completed work declared that the records do not show",
                 prints="one finding per line, `<kind>: <path>: <message>`; nothing "
                        "when clean", writes="nothing",
                 examples=["capabilities drift"])
    pd.set_defaults(func=_drift)
