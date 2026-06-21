"""`tcw capabilities` — the user stories. Subcommands per phase-3-capabilities B.2."""

import argparse
import sys

from tcw.store.base import Capability, RefError
from tcw.store.fs import FsCapabilitiesStore, FsTaxonomyStore, find_node, git_root

NAME = "capabilities"
SUBCOMMANDS = {"init", "list", "show", "add", "search", "check", "set"}
DEFAULT_SUBCOMMAND = "show"  # `tcw capabilities <id>` == `tcw capabilities show <id>`


def _init(args: argparse.Namespace) -> int:
    from tcw.cli import run_init      # function-local: top-level cli imports this module
    return run_init([NAME])


def _store() -> FsCapabilitiesStore | None:
    node = find_node(NAME)
    if node is None:
        print("tcw capabilities: no docs/capabilities/ in this repo. Run `tcw init capabilities`.",
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


def _print_cap(cap: Capability) -> None:
    print(f"## {cap.name}  ({cap.ref})")
    for k, v in cap.fields.items():
        print(f"**{k}:** {v}")
    body = cap.body.strip()
    if body:
        print()
        print("\n".join(body.splitlines()[:10]))


def _list(args: argparse.Namespace) -> int:
    st = _store()
    if st is None:
        return 1
    for c in st.list(status=args.status, namespace=args.namespace):
        print(f"[{c.status}]\t{c.ref}\t{c.name}")
    return 0


def _show(args: argparse.Namespace) -> int:
    st = _store()
    if st is None:
        return 1
    try:
        cf = st.get(args.id)
    except RefError as e:
        print(f"tcw capabilities show: {e}", file=sys.stderr)
        return 1
    if cf is None:
        print(f"tcw capabilities show: no such capability: {args.id}", file=sys.stderr)
        return 1
    heading = args.id.split("#", 1)[1] if "#" in args.id else None
    caps = [c for c in cf.capabilities if c.heading_slug == heading] if heading else cf.capabilities
    if heading and not caps:
        print(f"tcw capabilities show: no heading '#{heading}' in {cf.identifier}", file=sys.stderr)
        return 1
    print(f"# {cf.title}")
    for c in caps:
        print()
        _print_cap(c)
    return 0


def _add(args: argparse.Namespace) -> int:
    st = _store()
    if st is None:
        return 1
    try:
        cf = st.add(args.path, name=args.name, status=args.status,
                    body=_stdin_body(), folder=args.folder)
    except (ValueError, RefError) as e:
        print(f"tcw capabilities add: {e}", file=sys.stderr)
        return 1
    print(f"Added capability {cf.identifier}")
    return 0


def _set(args: argparse.Namespace) -> int:
    st = _store()
    if st is None:
        return 1
    fields: dict[str, str] = {}
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
    print(f"Set {cap.ref}")
    return 0


def _search(args: argparse.Namespace) -> int:
    st = _store()
    if st is None:
        return 1
    for c in st.search(args.query):
        print(f"{c.ref}\t{c.name}")
    return 0


def _check(args: argparse.Namespace) -> int:
    node = find_node(NAME)
    if node is None:
        print("tcw capabilities: no docs/capabilities/ in this repo. Run `tcw init capabilities`.",
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

    g.add_parser("init", help="scaffold docs/capabilities/ (mirror of `tcw init capabilities`)") \
        .set_defaults(func=_init)

    pl = g.add_parser("list", help="list capabilities, flagged by status")
    pl.add_argument("--status")
    pl.add_argument("--namespace")
    pl.set_defaults(func=_list)

    ps = g.add_parser("show", help="read a capability (file, or a #heading)")
    ps.add_argument("id")
    ps.set_defaults(func=_show)

    pa = g.add_parser("add", help="scaffold a capability file/heading")
    pa.add_argument("path", metavar="namespace/path")
    pa.add_argument("name", nargs="?")
    pa.add_argument("-s", "--status", default="Missing")
    pa.add_argument("--folder", action="store_true", help="scaffold a folder + capabilities.md")
    pa.set_defaults(func=_add)

    pset = g.add_parser("set", help="update a capability's status/fields in place")
    pset.add_argument("id")
    pset.add_argument("--status", help="shorthand for --field Status=<S>")
    pset.add_argument("--field", action="append", metavar="K=V",
                      help="set a metadata field (repeatable)")
    pset.set_defaults(func=_set)

    pse = g.add_parser("search", help="search names + bodies")
    pse.add_argument("query")
    pse.set_defaults(func=_search)

    pc = g.add_parser("check", help="validate identifiers, subject refs, metadata")
    pc.set_defaults(func=_check)
