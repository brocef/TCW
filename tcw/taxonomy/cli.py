"""`tcw taxonomy` — the nouns. Subcommands per phase-2-taxonomy B.2."""

import argparse
import sys

from tcw.store.base import AmbiguousRef, Term
from tcw.store.fs import FsTaxonomyStore, find_node

NAME = "taxonomy"
SUBCOMMANDS = {"init", "list", "add", "show", "rm", "search", "check", "extends"}
DEFAULT_SUBCOMMAND = "show"  # `tcw taxonomy <path>` == `tcw taxonomy show <path>`


def _init(args: argparse.Namespace) -> int:
    from tcw.cli import run_init      # function-local: top-level cli imports this module
    return run_init([NAME])


def _store() -> FsTaxonomyStore | None:
    node = find_node(NAME)
    if node is None:
        print("tcw taxonomy: no tcw taxonomy node here — run `tcw init` in the project folder.",
              file=sys.stderr)
        return None
    return FsTaxonomyStore.open(node)


def _stdin_body() -> str:
    if sys.stdin.isatty():
        return ""
    try:
        return sys.stdin.read()
    except (OSError, ValueError):  # e.g. stdin not readable (captured under pytest)
        return ""


def _print_term(term: Term) -> None:
    print(f"{term.name}  ({term.qualified}, {term.origin})")
    print(f"kind: {term.kind}")
    if term.vocabulary:
        print(f"vocabulary: {', '.join(term.vocabulary)}")
    if term.relates_to:
        print(f"relatesTo: {', '.join(term.relates_to)}")
    if term.attachments:
        print(f"attachments: {', '.join(term.attachments)}")
    body = term.description.strip()
    if body:
        print()
        print("\n".join(body.splitlines()[:10]))


def _list(args: argparse.Namespace) -> int:
    st = _store()
    if st is None:
        return 1
    for t in sorted(st.list(local_only=args.local), key=lambda t: (t.origin != "local", t.qualified)):
        indent = "  " * t.slug.count("/")
        marker = "F" if t.kind == "Feature" else "V"
        print(f"{indent}{t.slug.rsplit('/', 1)[-1]}  [{marker}] ({t.origin})")
    return 0


def _add(args: argparse.Namespace) -> int:
    st = _store()
    if st is None:
        return 1
    try:
        term = st.add(args.name, slug=args.slug, parent=args.parent,
                      description=args.description or _stdin_body(),
                      kind=args.kind, vocabulary=args.vocab)
    except ValueError as e:
        print(f"tcw taxonomy add: {e}", file=sys.stderr)
        return 1
    print(f"Added term {term.slug}")
    return 0


def _show(args: argparse.Namespace) -> int:
    st = _store()
    if st is None:
        return 1
    try:
        term = st.get(args.path)
    except AmbiguousRef:
        print(f"tcw taxonomy show: ambiguous ref '{args.path}' — qualify with an alias.",
              file=sys.stderr)
        return 1
    if term is None:
        print(f"tcw taxonomy show: no such term: {args.path}", file=sys.stderr)
        return 1
    _print_term(term)
    return 0


def _rm(args: argparse.Namespace) -> int:
    st = _store()
    if st is None:
        return 1
    try:
        term = st.get(args.path)
    except AmbiguousRef:
        print(f"tcw taxonomy rm: ambiguous ref '{args.path}'.", file=sys.stderr)
        return 1
    if term is None:
        print(f"tcw taxonomy rm: no such term: {args.path}", file=sys.stderr)
        return 1
    relators = st.relators(term.slug) if term.origin == "local" else []
    try:
        st.remove(args.path)
    except ValueError as e:
        print(f"tcw taxonomy rm: {e}", file=sys.stderr)
        return 1
    if relators:
        print(f"warning: still referenced by relatesTo of: {', '.join(relators)}",
              file=sys.stderr)
    print(f"Removed term {term.slug}")
    return 0


def _search(args: argparse.Namespace) -> int:
    st = _store()
    if st is None:
        return 1
    for t in st.search(args.query):
        print(f"{t.qualified}\t{t.name}")
    return 0


def _check(args: argparse.Namespace) -> int:
    st = _store()
    if st is None:
        return 1
    problems = st.check()
    for p in problems:
        print(p, file=sys.stderr)
    if problems:
        print(f"{len(problems)} problem(s).", file=sys.stderr)
        return 1
    print("taxonomy OK")
    return 0


def _extends_add(args: argparse.Namespace) -> int:
    st = _store()
    if st is None:
        return 1
    try:
        st.extends_add(args.alias, args.path)
    except ValueError as e:
        print(f"tcw taxonomy extends add: {e}", file=sys.stderr)
        return 1
    print(f"Extends '{args.alias}' -> {args.path}  (docs/taxonomy/config.yaml). "
          f"Run `tcw taxonomy check`.")
    return 0


def _extends_rm(args: argparse.Namespace) -> int:
    st = _store()
    if st is None:
        return 1
    try:
        st.extends_remove(args.alias)
    except ValueError as e:
        print(f"tcw taxonomy extends rm: {e}", file=sys.stderr)
        return 1
    print(f"Removed extends '{args.alias}'")
    return 0


def add_subparser(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser(NAME, help="vocabulary and feature entries")
    g = p.add_subparsers(dest="cmd", required=True)

    g.add_parser("init", help="scaffold docs/taxonomy/ (mirror of `tcw init taxonomy`)") \
        .set_defaults(func=_init)

    pl = g.add_parser("list", help="list entries as a tree, flagged by kind and origin")
    pl.add_argument("--local", action="store_true", help="local entries only")
    pl.set_defaults(func=_list)

    pa = g.add_parser("add", help="create a vocabulary term or feature")
    pa.add_argument("name")
    pa.add_argument("description", nargs="?")
    pa.add_argument("-s", "--slug", help="leaf slug (default: slugified name)")
    pa.add_argument("-p", "--parent", help="parent term path (default: root)")
    pa.add_argument("--kind", choices=("vocabulary", "feature"), default="vocabulary",
                    help="taxonomy object kind (default: vocabulary)")
    pa.add_argument("--vocab", action="append", metavar="REF",
                    help="vocabulary ref involved by a feature (repeatable)")
    pa.set_defaults(func=_add)

    ps = g.add_parser("show", help="read an entry")
    ps.add_argument("path")
    ps.set_defaults(func=_show)

    pr = g.add_parser("rm", help="remove a local entry")
    pr.add_argument("path")
    pr.set_defaults(func=_rm)

    pse = g.add_parser("search", help="search entry names + descriptions")
    pse.add_argument("query")
    pse.set_defaults(func=_search)

    pc = g.add_parser("check", help="validate aliases + references")
    pc.set_defaults(func=_check)

    pe = g.add_parser("extends", help="declare taxonomy inheritance (federation)")
    eg = pe.add_subparsers(dest="ecmd", required=True)
    pea = eg.add_parser("add", help="add an extends alias -> sibling repo path")
    pea.add_argument("alias")
    pea.add_argument("path", help="path to a sibling repo containing docs/taxonomy/")
    pea.set_defaults(func=_extends_add)
    per = eg.add_parser("rm", help="remove an extends alias")
    per.add_argument("alias")
    per.set_defaults(func=_extends_rm)
