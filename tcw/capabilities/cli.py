"""`tcw capabilities` — the user stories. Path-addressed folder capabilities.

stdout carries each command's product and nothing else (TCW-73 Design 1):
`add` prints the new capability's qualified path, `list` and `search` one path
per line, `show` the record, `path` the store folder; `set`, `reset`, `rm` and
`extends add|rm` print nothing. Every file a write changed is named on stderr.
A failure is raised for the top-level handler to print and turn into its exit
code.
"""

import argparse
import sys

from tcw import exit as codes
from tcw.errors import BackendError, NotFound, UsageError
from tcw.output import changed, print_json
from tcw.stdin import read_piped_stdin
from tcw.store.base import Capability
from tcw.store.fs import FsCapabilitiesStore, find_node

NAME = "capabilities"


def _node():
    node = find_node(NAME)
    if node is None:
        raise BackendError("no capabilities store here — run `tcw init capabilities "
                           "--id <id>` in the project folder")
    return node


def _store() -> FsCapabilitiesStore:
    return FsCapabilitiesStore.open(_node())


def _record(cap: Capability) -> dict:
    return {"path": cap.qualified, "name": cap.name, "status": cap.status,
            "origin": cap.origin}


def _detail(cap: Capability) -> dict:
    return {**_record(cap), "id": cap.id, "fields": dict(cap.fields), "body": cap.body}


def _fmt(v) -> str:
    return ", ".join(v) if isinstance(v, list) else str(v)


def _print_caps(caps: list[Capability], as_json: bool) -> int:
    if as_json:
        print_json("capabilities", [_record(c) for c in caps])
    else:
        for c in caps:
            print(c.qualified)
    return codes.OK


def _list(args: argparse.Namespace) -> int:
    return _print_caps(_store().list_all(status=args.status, namespace=args.namespace,
                                         local_only=args.local), args.json)


def _search(args: argparse.Namespace) -> int:
    return _print_caps(_store().search(args.query), args.json)


def _show(args: argparse.Namespace) -> int:
    cap = _store().get(args.id)
    if cap is None:
        raise NotFound(f"no such capability: '{args.id}'")
    if args.json:
        print_json("capability", _detail(cap))
        return codes.OK
    lines = [f"path: {cap.qualified}", f"name: {cap.name}", f"origin: {cap.origin}"]
    if cap.id:
        lines.append(f"id: {cap.id}")
    lines += [f"{k}: {_fmt(v)}" for k, v in cap.fields.items()]
    body = cap.body.strip()
    if body:
        lines += ["", "body:", *(f"  {line}" if line else "" for line in body.splitlines())]
    print("\n".join(lines))
    return codes.OK


def _path(args: argparse.Namespace) -> int:
    print(_store().root)
    return codes.OK


def _add(args: argparse.Namespace) -> int:
    st = _store()
    cap = st.add(args.path, name=args.name, status=args.status, body=read_piped_stdin())
    changed(st.changed)
    print(cap.qualified)
    return codes.OK


def _fields(args: argparse.Namespace) -> dict:
    """`--status` and each `--field K=V`, one field per use. A key given twice,
    `--status` together with `--field Status=`, or a `--field` with no `=` is
    a usage error; the value is kept whole, as the record file writes it."""
    fields: dict = {}
    pairs = [("Status", args.status)] if args.status else []
    for kv in args.field or []:
        if "=" not in kv:
            raise UsageError(f"--field takes K=V, got '{kv}'")
        k, v = kv.split("=", 1)
        pairs.append((k.strip(), v.strip()))
    for k, v in pairs:
        if k in fields:
            raise UsageError(f"field '{k}' given more than once")
        fields[k] = v
    if not fields:
        raise UsageError("give --status or at least one --field")
    return fields


def _set(args: argparse.Namespace) -> int:
    fields = _fields(args)
    st = _store()
    st.set(args.id, fields)
    changed(st.changed)
    return codes.OK


def _reset(args: argparse.Namespace) -> int:
    st = _store()
    st.reset(args.id)
    changed(st.changed)
    return codes.OK


def _rm(args: argparse.Namespace) -> int:
    st = _store()
    st.remove(args.id)
    changed(st.changed)
    return codes.OK


def _extends_add(args: argparse.Namespace) -> int:
    st = _store()
    st.extends_add(args.project_id)
    changed(st.changed)
    return codes.OK


def _extends_rm(args: argparse.Namespace) -> int:
    st = _store()
    st.extends_remove(args.project_id)
    changed(st.changed)
    return codes.OK


def _drift(args: argparse.Namespace) -> int:
    """Report capabilities that drifted from ground truth: inherited-but-unreviewed
    (status is the master default, never locally ruled on), and what completed
    work items declared in their `capabilities.yaml` that today's records no
    longer show. Read-only; exits non-zero when any drift is found."""
    node = _node()
    st = FsCapabilitiesStore.open(node)

    unreviewed = st.unreviewed_inherited()
    completed_missing = _completed_but_missing(node)

    for c in unreviewed:
        print(f"unreviewed\t{c.qualified}\t(inherited; status is the master default)")
    for problem in completed_missing:
        print(f"completed-work\t{problem}")

    n = len(unreviewed) + len(completed_missing)
    if n:
        print(f"{n} capability(ies) drifted.", file=sys.stderr)
        return 1
    print("no capability drift")
    return 0


def _completed_but_missing(node) -> list[str]:
    """What the finished items declared in `capabilities.yaml` that today's
    records no longer show, through TCW-69's `drift_problems`, plus one finding
    per unreadable `item.yaml`. It never reads a `Planning doc` field, and is
    empty for a project with no work store."""
    from tcw.errors import BackendError
    from tcw.store.fs import FsProjectRegistry, _has_work_store
    from tcw.work.fs_backend import FsWorkBackend, read_all
    from tcw.work.gates import drift_problems, project_reader
    from tcw.work.model import completion_stage
    from tcw.work.open import open_backend

    if not _has_work_store(node):
        return []
    try:
        backend = open_backend(node)
    except BackendError as error:
        return [str(error)]
    if not isinstance(backend, FsWorkBackend):
        return []
    items, unreadable = read_all(backend.work_path, backend.project, backend.enabled)
    finished = [i for i in items if i.stage == completion_stage()]
    problems = [f"{u.path}: cannot be read, so its declarations were not "
                f"checked: {u.message}" for u in unreadable]
    if finished:
        registry = FsProjectRegistry.open(node)
        problems += drift_problems(backend.layout, finished,
                                   project_reader(node, registry))
    return problems


def _completed_but_missing(node) -> list[str]:
    """What the finished items declared in `capabilities.yaml` that today's
    records no longer show, through TCW-69's `drift_problems`, plus one finding
    per unreadable `item.yaml`. It never reads a `Planning doc` field, and is
    empty for a project with no work store."""
    from tcw.errors import BackendError
    from tcw.store.fs import FsProjectRegistry, _has_work_store
    from tcw.work.fs_backend import FsWorkBackend, read_all
    from tcw.work.gates import drift_problems, project_reader
    from tcw.work.model import completion_stage
    from tcw.work.open import open_backend

    if not _has_work_store(node):
        return []
    try:
        backend = open_backend(node)
    except BackendError as error:
        return [str(error)]
    if not isinstance(backend, FsWorkBackend):
        return []
    items, unreadable = read_all(backend.work_path, backend.project, backend.enabled)
    finished = [i for i in items if i.stage == completion_stage()]
    problems = [f"{u.path}: cannot be read, so its declarations were not "
                f"checked: {u.message}" for u in unreadable]
    if finished:
        registry = FsProjectRegistry.open(node)
        problems += drift_problems(backend.layout, finished,
                                   project_reader(node, registry))
    return problems


def add_subparser(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser(NAME, help="the user stories — what a user can do")
    g = p.add_subparsers(dest="cmd", required=True)

    pl = g.add_parser("list", help="every capability's path, one per line")
    pl.add_argument("--status", help="only capabilities with this status")
    pl.add_argument("--namespace", help="only capabilities under this namespace folder")
    pl.add_argument("--local", action="store_true",
                    help="local capabilities only, none inherited")
    pl.add_argument("--json", action="store_true",
                    help='print {"schema": 1, "capabilities": [...]}')
    pl.set_defaults(func=_list)

    ps = g.add_parser("show", help="read a capability by path")
    ps.add_argument("id", metavar="path",
                    help="capability path, e.g. web/login (alias-prefixed if inherited)")
    ps.add_argument("--json", action="store_true",
                    help='print {"schema": 1, "capability": {...}}')
    ps.set_defaults(func=_show)

    g.add_parser("path", help="print the capabilities store folder").set_defaults(func=_path)

    pa = g.add_parser("add", help="create a capability; its body is read from stdin")
    pa.add_argument("path", metavar="namespace/path",
                    help="path for the new capability, namespace folder first")
    pa.add_argument("name", nargs="?",
                    help="display name (default: titled from the last path segment)")
    pa.add_argument("--status", default="Missing",
                    help="initial status (default: Missing)")
    pa.set_defaults(func=_add)

    pset = g.add_parser("set", help="update a capability's status or fields in place")
    pset.add_argument("id", metavar="path",
                      help="capability path to update; an inherited one gains a local override")
    pset.add_argument("--status", help="the same as --field Status=<status>")
    pset.add_argument("--field", action="append", metavar="K=V",
                      help="set one metadata field; repeat for more fields "
                           "(a list field such as Subject takes a,b,c)")
    pset.set_defaults(func=_set)

    prst = g.add_parser("reset", help="drop a local override, inheriting again")
    prst.add_argument("id", metavar="path", help="path of the local override to drop")
    prst.set_defaults(func=_reset)

    prm = g.add_parser("rm", help="remove a local capability")
    prm.add_argument("id", metavar="path", help="path of the local capability to remove")
    prm.set_defaults(func=_rm)

    pse = g.add_parser("search", help="capabilities whose name or body holds the text")
    pse.add_argument("query", help="text matched case-insensitively in names + bodies")
    pse.add_argument("--json", action="store_true",
                     help='print {"schema": 1, "capabilities": [...]}')
    pse.set_defaults(func=_search)

    pe = g.add_parser("extends", help="inherit another project's capabilities")
    eg = pe.add_subparsers(dest="ecmd", required=True)
    pea = eg.add_parser("add", help="inherit a registered project's capabilities")
    pea.add_argument("project_id", help="registered project ID whose capabilities to inherit")
    pea.set_defaults(func=_extends_add)
    per = eg.add_parser("rm", help="stop inheriting a project's capabilities")
    per.add_argument("project_id", help="registered project ID to stop inheriting")
    per.set_defaults(func=_extends_rm)

    pd = g.add_parser("drift", help="report unreviewed inherited and shipped-but-missing "
                                    "capabilities")
    pd.set_defaults(func=_drift)
