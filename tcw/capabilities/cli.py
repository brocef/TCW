"""`tcw capabilities` — the user stories. Path-addressed folder capabilities."""

import argparse
import sys

from tcw.store.base import Capability, RefError
from tcw.store.base import AmbiguousRef
from tcw.store.fs import FsCapabilitiesStore, FsTaxonomyStore, find_node, git_root

NAME = "capabilities"
SUBCOMMANDS = {"init", "list", "show", "add", "search", "check", "set", "reset", "extends", "drift"}
DEFAULT_SUBCOMMAND = "show"  # `tcw capabilities <path>` == `tcw capabilities show <path>`


def _init(args: argparse.Namespace) -> int:
    from tcw.cli import run_init      # function-local: top-level cli imports this module
    return run_init([NAME], args.id)


def _store() -> FsCapabilitiesStore | None:
    node = find_node(NAME)
    if node is None:
        print("tcw capabilities: no tcw capabilities node here — run `tcw init` in the project folder.",
              file=sys.stderr)
        return None
    return FsCapabilitiesStore.open(node)


def _taxonomy_for(node):
    """The node's taxonomy store, if it has one (for cross-component Subject check)."""
    return FsTaxonomyStore.open(node) if (node / "docs" / "taxonomy").is_dir() else None


def _stdin_body() -> str:
    if sys.stdin.isatty():
        return ""
    try:
        return sys.stdin.read()
    except (OSError, ValueError):
        return ""


def _fmt(v) -> str:
    return ", ".join(v) if isinstance(v, list) else str(v)


def _print_cap(cap: Capability) -> None:
    tag = f"  [{cap.origin}]" if cap.origin != "local" else ""
    print(f"## {cap.name}  ({cap.qualified}){tag}")
    if cap.id:
        print(f"**id:** {cap.id}")
    for k, v in cap.fields.items():
        print(f"**{k}:** {_fmt(v)}")
    body = cap.body.strip()
    if body:
        print()
        print(body)


def _list(args: argparse.Namespace) -> int:
    st = _store()
    if st is None:
        return 1
    for c in st.list_all(status=args.status, namespace=args.namespace,
                         local_only=args.local_only):
        print(f"[{c.status}]\t{c.qualified}\t{c.name}")
    return 0


def _show(args: argparse.Namespace) -> int:
    st = _store()
    if st is None:
        return 1
    try:
        cap = st.get(args.id)
    except (RefError, AmbiguousRef) as e:
        print(f"tcw capabilities show: {e}", file=sys.stderr)
        return 1
    if cap is None:
        print(f"tcw capabilities show: no such capability: {args.id}", file=sys.stderr)
        return 1
    _print_cap(cap)
    return 0


def _add(args: argparse.Namespace) -> int:
    st = _store()
    if st is None:
        return 1
    try:
        cap = st.add(args.path, name=args.name, status=args.status, body=_stdin_body())
    except (ValueError, RefError) as e:
        print(f"tcw capabilities add: {e}", file=sys.stderr)
        return 1
    print(f"Added capability {cap.path} ({cap.id})")
    return 0


def _set(args: argparse.Namespace) -> int:
    st = _store()
    if st is None:
        return 1
    fields: dict = {}
    if args.status:
        fields["Status"] = args.status
    for kv in (args.field or []):
        if "=" not in kv:
            print(f"tcw capabilities set: --field must be K=V: {kv}", file=sys.stderr)
            return 1
        k, v = kv.split("=", 1)
        fields[k.strip()] = v.strip()
    if not fields:
        print("tcw capabilities set: need --status or at least one --field", file=sys.stderr)
        return 1
    try:
        cap = st.set(args.id, fields)
    except (ValueError, RefError) as e:
        print(f"tcw capabilities set: {e}", file=sys.stderr)
        return 1
    print(f"Set {cap.path}")
    return 0


def _reset(args: argparse.Namespace) -> int:
    st = _store()
    if st is None:
        return 1
    try:
        st.reset(args.id)
    except (ValueError, RefError) as e:
        print(f"tcw capabilities reset: {e}", file=sys.stderr)
        return 1
    print(f"reset {args.id}")
    return 0


def _search(args: argparse.Namespace) -> int:
    st = _store()
    if st is None:
        return 1
    for c in st.search(args.query):
        print(f"{c.qualified}\t{c.name}")
    return 0


def _extends(args: argparse.Namespace) -> int:
    st = _store()
    if st is None:
        return 1
    try:
        if args.rm:
            st.extends_remove(args.project_id)
            print(f"Removed extends project {args.project_id}")
        else:
            st.extends_add(args.project_id)
            print(f"Added extends project {args.project_id}")
    except (ValueError, RefError) as e:
        print(f"tcw capabilities extends: {e}", file=sys.stderr)
        return 1
    return 0


def _drift(args: argparse.Namespace) -> int:
    """Report capabilities that drifted from ground truth: inherited-but-unreviewed
    (status is the master default, never locally ruled on) and local-Missing whose
    Planning doc points to a completed work item (declared, shipped, never flipped).
    Read-only; exits non-zero when any drift is found."""
    node = find_node(NAME)
    if node is None:
        print("tcw capabilities: no tcw capabilities node here — run `tcw init` in the project folder.",
              file=sys.stderr)
        return 1
    st = FsCapabilitiesStore.open(node)

    unreviewed = st.unreviewed_inherited()
    shipped_missing = _shipped_but_missing(node, st)

    for c in unreviewed:
        print(f"unreviewed\t{c.qualified}\t(inherited; status is the master default)")
    for path, slug in shipped_missing:
        print(f"shipped-missing\t{path}\t(Planning doc {slug} is completed, still Missing)")

    n = len(unreviewed) + len(shipped_missing)
    if n:
        print(f"{n} capability(ies) drifted.", file=sys.stderr)
        return 1
    print("no capability drift")
    return 0


def _shipped_but_missing(node, st) -> list[tuple[str, str]]:
    """Local Missing capabilities whose `Planning doc` names a completed work item.
    Read-only follow of an existing capability→work forward pointer; degrades to
    empty when no work node is present (no hard cross-axis dependency)."""
    if not (node / "docs" / "work").is_dir():
        return []
    from tcw.store.fs import FsWorkStore
    work = FsWorkStore.open(node)
    out: list[tuple[str, str]] = []
    for c in st.list_all(local_only=True):
        if c.status != "Missing":
            continue
        slug = c.fields.get("Planning doc")
        if not slug:
            continue
        try:
            item = work.get(str(slug))
        except Exception:
            item = None
        if item is not None and item.status == "completed":
            out.append((c.path, str(slug)))
    return out


def _check(args: argparse.Namespace) -> int:
    node = find_node(NAME)
    if node is None:
        print("tcw capabilities: no tcw capabilities node here — run `tcw init` in the project folder.",
              file=sys.stderr)
        return 1
    problems = FsCapabilitiesStore.open(node).check(taxonomy=_taxonomy_for(node))
    for p in problems:
        print(p, file=sys.stderr)
    if problems:
        print(f"{len(problems)} problem(s).", file=sys.stderr)
        return 1
    print("capabilities OK")
    return 0


def add_subparser(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser(NAME, help="the user stories — what a user can do")
    g = p.add_subparsers(dest="cmd", required=True)

    pi = g.add_parser("init", help="scaffold docs/capabilities/ (mirror of `tcw init capabilities`)")
    pi.add_argument("--id", help="canonical project ID (required for new/legacy nodes)")
    pi.set_defaults(func=_init)

    pl = g.add_parser("list", help="list capabilities, flagged by status + origin")
    pl.add_argument("--status")
    pl.add_argument("--namespace")
    pl.add_argument("--local-only", action="store_true",
                    help="exclude inherited (federated) capabilities")
    pl.set_defaults(func=_list)

    ps = g.add_parser("show", help="read a capability by path")
    ps.add_argument("id", metavar="path")
    ps.set_defaults(func=_show)

    pa = g.add_parser("add", help="scaffold a capability folder")
    pa.add_argument("path", metavar="namespace/path")
    pa.add_argument("name", nargs="?")
    pa.add_argument("-s", "--status", default="Missing")
    pa.set_defaults(func=_add)

    pset = g.add_parser("set", help="update a capability's status/fields in place")
    pset.add_argument("id", metavar="path")
    pset.add_argument("--status", help="shorthand for --field Status=<S>")
    pset.add_argument("--field", action="append", metavar="K=V",
                      help="set a metadata field (repeatable; Subject accepts a,b,c)")
    pset.set_defaults(func=_set)

    prst = g.add_parser("reset", help="drop a local override, re-inheriting upstream")
    prst.add_argument("id", metavar="path")
    prst.set_defaults(func=_reset)

    pse = g.add_parser("search", help="search names + bodies")
    pse.add_argument("query")
    pse.set_defaults(func=_search)

    pe = g.add_parser("extends", help="federate another project's capabilities")
    pe.add_argument("project_id")
    pe.add_argument("--rm", action="store_true", help="remove the project instead")
    pe.set_defaults(func=_extends)

    pc = g.add_parser("check", help="validate paths, subject/feature refs, federation, metadata")
    pc.set_defaults(func=_check)

    pd = g.add_parser("drift", help="report unreviewed inherited + shipped-but-Missing capabilities")
    pd.set_defaults(func=_drift)
