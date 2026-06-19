"""`tcw work` — the changes. Single-node state machine per phase-5-work B.2."""

import argparse
import sys

from tcw.store.base import (
    WORK_RESOLUTIONS, IllegalTransition, MultipleMatch, WorkItem,
)
from tcw.store.fs import COMPONENTS, FsWorkStore, find_node, git_root, init

NAME = "work"
SUBCOMMANDS = {"init", "new", "list", "show", "path", "start", "complete", "drop"}
DEFAULT_SUBCOMMAND = None  # work uses explicit show/path (slugs aren't tree paths)

_ERRORS = (ValueError, IllegalTransition, MultipleMatch)


def _store() -> FsWorkStore | None:
    node = find_node(NAME)
    if node is None:
        print("tcw work: no docs/work/ in this repo. Run `tcw work init`.", file=sys.stderr)
        return None
    return FsWorkStore.open(node)


def _stdin_body() -> str:
    if sys.stdin.isatty():
        return ""
    try:
        return sys.stdin.read()
    except (OSError, ValueError):
        return ""


def _print_item(item: WorkItem) -> None:
    print(f"{item.slug}  [{item.status}]")
    print(f"title: {item.title}")
    if item.phase:
        print(f"phase: {item.phase}")
    if item.resolution:
        print(f"resolution: {item.resolution}")
    if item.blocked_by:
        labels = [b["slug"] if "slug" in b else f"external: {b['external']}"
                  for b in item.blocked_by]
        print(f"blocked_by: {', '.join(labels)}")
    body = item.body.strip()
    if body:
        print()
        print("\n".join(body.splitlines()[:12]))


def _init(args: argparse.Namespace) -> int:
    root = git_root()
    if root is None:
        print("tcw work init: not inside a git repository. Run `git init` first.", file=sys.stderr)
        return 1
    init(["work"], root)
    print(f"Initialized docs/work/ under {root}")
    return 0


def _new(args: argparse.Namespace) -> int:
    st = _store()
    if st is None:
        return 1
    item = st.create(args.title, body=_stdin_body())
    print(item.slug)
    return 0


def _list(args: argparse.Namespace) -> int:
    st = _store()
    if st is None:
        return 1
    for item in st.query(status=args.status):
        print(f"{item.slug}\t{item.status}\t{item.phase or '-'}\t{item.title}")
    return 0


def _show(args: argparse.Namespace) -> int:
    st = _store()
    if st is None:
        return 1
    try:
        item = st.get(args.slug)
    except MultipleMatch as e:
        print(f"tcw work show: {e}", file=sys.stderr)
        return 1
    if item is None:
        print(f"tcw work show: no such work item: {args.slug}", file=sys.stderr)
        return 1
    _print_item(item)
    return 0


def _path(args: argparse.Namespace) -> int:
    st = _store()
    if st is None:
        return 1
    p = st.path(args.slug)
    if p is None:
        print(f"tcw work path: no such work item: {args.slug}", file=sys.stderr)
        return 1
    print(p)
    return 0


def _start(args: argparse.Namespace) -> int:
    return _run(lambda st: st.start(args.slug), f"started {args.slug}")


def _complete(args: argparse.Namespace) -> int:
    st = _store()
    if st is None:
        return 1
    checklist = st.dod_checklist()
    print("Definition of Done — acknowledge each item:")
    for item in checklist:
        print(f"  [ ] {item}")
    if not args.confirm:
        print("Refused: re-run with --confirm once the checklist is satisfied.", file=sys.stderr)
        return 1
    try:
        st.complete(args.slug, args.resolution, dod_ack=checklist)
    except _ERRORS as e:
        print(f"tcw work complete: {e}", file=sys.stderr)
        return 1
    print(f"completed {args.slug} ({args.resolution})")
    return 0


def _drop(args: argparse.Namespace) -> int:
    return _run(lambda st: st.drop(args.slug), f"dropped {args.slug}")


def _run(op, success: str) -> int:
    st = _store()
    if st is None:
        return 1
    try:
        op(st)
    except _ERRORS as e:
        print(f"tcw work: {e}", file=sys.stderr)
        return 1
    print(success)
    return 0


def add_subparser(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser(NAME, help="the changes — work items through a state machine")
    g = p.add_subparsers(dest="cmd", required=True)

    g.add_parser("init", help="create docs/work/{inbox,backlog,active,completed}/") \
        .set_defaults(func=_init)

    pn = g.add_parser("new", help="create a backlog item; prints its slug")
    pn.add_argument("title")
    pn.set_defaults(func=_new)

    pl = g.add_parser("list", help="the board")
    pl.add_argument("--status")
    pl.set_defaults(func=_list)

    psh = g.add_parser("show", help="resolve slug → item; print state + body")
    psh.add_argument("slug")
    psh.set_defaults(func=_show)

    pp = g.add_parser("path", help="print the current path of a slug")
    pp.add_argument("slug")
    pp.set_defaults(func=_path)

    pst = g.add_parser("start", help="inbox|backlog → active")
    pst.add_argument("slug")
    pst.set_defaults(func=_start)

    pc = g.add_parser("complete", help="active → completed (DoD gate)")
    pc.add_argument("slug")
    pc.add_argument("--resolution", required=True, choices=sorted(WORK_RESOLUTIONS))
    pc.add_argument("--confirm", action="store_true")
    pc.set_defaults(func=_complete)

    pd = g.add_parser("drop", help="inbox|backlog → deleted")
    pd.add_argument("slug")
    pd.set_defaults(func=_drop)
