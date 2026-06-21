"""`tcw work` — the changes. Single-node state machine per phase-5-work B.2."""

import argparse
import subprocess
import sys

from tcw.store.base import (
    WORK_RESOLUTIONS, IllegalTransition, MultipleMatch, WorkItem,
)
from tcw.store.fs import (
    COMPONENTS, WORKTREES_DIR, FsWorkStore, add_worktree, child_nodes,
    ensure_worktree_ignored, find_node, git_commit, parent_node,
    remove_worktree,
)
from tcw.work.recursion import delegate, escalate, reconcile

NAME = "work"
SUBCOMMANDS = {"init", "new", "list", "show", "path", "start", "edit", "complete",
               "drop", "nodes", "reconcile", "delegate", "escalate"}
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


def _split(val: str | None) -> list[str]:
    """Comma-split a flag value: strip tokens, drop empties (repo idiom)."""
    return [s.strip() for s in (val or "").split(",") if s.strip()]


def _print_item(item: WorkItem) -> None:
    print(f"{item.slug}  [{item.status}]")
    print(f"title: {item.title}")
    if item.parent:
        print(f"parent: {item.parent}")
    if item.phase:
        print(f"phase: {item.phase}")
    if item.priority is not None:
        print(f"priority: {item.priority}")
    if item.resolution:
        print(f"resolution: {item.resolution}")
    if item.blocked_by:
        labels = []
        for b in item.blocked_by:
            if "slug" in b:
                labels.append(b["slug"])
            elif "external" in b:
                labels.append(f"external: {b['external']}")
        if labels:
            print(f"blocked_by: {', '.join(labels)}")
    body = item.body.strip()
    if body:
        print()
        print("\n".join(body.splitlines()[:12]))


def _nodes(args: argparse.Namespace) -> int:
    node = find_node(NAME)
    if node is None:
        print("tcw work: no docs/work/ in this repo. Run `tcw work init`.", file=sys.stderr)
        return 1
    parent = parent_node(node)
    print(f"node:   {node}")
    print(f"parent: {parent if parent else '(none — root)'}")
    children = child_nodes(node)
    if children:
        print("children:")
        for c in children:
            print(f"  {c.relative_to(node)}")
    else:
        print("children: (none — leaf)")
    return 0


def _reconcile(args: argparse.Namespace) -> int:
    node = find_node(NAME)
    if node is None:
        print("tcw work: no docs/work/ in this repo. Run `tcw work init`.", file=sys.stderr)
        return 1
    try:
        block = reconcile(node, args.slug, commit=args.commit)
    except _ERRORS as e:
        print(f"tcw work reconcile: {e}", file=sys.stderr)
        return 1
    print(block)
    return 0


def _delegate(args: argparse.Namespace) -> int:
    node = find_node(NAME)
    if node is None:
        print("tcw work: no docs/work/ in this repo. Run `tcw work init`.", file=sys.stderr)
        return 1
    try:
        doc = delegate(node, args.child, args.title, body=_stdin_body(),
                       initiative=args.initiative)
    except _ERRORS as e:
        print(f"tcw work delegate: {e}", file=sys.stderr)
        return 1
    print(doc)
    return 0


def _escalate(args: argparse.Namespace) -> int:
    node = find_node(NAME)
    if node is None:
        print("tcw work: no docs/work/ in this repo. Run `tcw work init`.", file=sys.stderr)
        return 1
    try:
        doc = escalate(node, args.title, body=_stdin_body(), initiative=args.initiative)
    except _ERRORS as e:
        print(f"tcw work escalate: {e}", file=sys.stderr)
        return 1
    print(doc)
    print("Reminder: start an orchestrator session to triage the parent's inbox.",
          file=sys.stderr)
    return 0


def _init(args: argparse.Namespace) -> int:
    from tcw.cli import run_init      # function-local: top-level cli imports this module
    return run_init([NAME])


def _new(args: argparse.Namespace) -> int:
    st = _store()
    if st is None:
        return 1
    try:
        item = st.create(args.title, body=_stdin_body(), priority=args.priority,
                         parent=args.parent)
    except _ERRORS as e:
        print(f"tcw work new: {e}", file=sys.stderr)
        return 1
    rc = 0
    try:
        for ref in _split(args.blocked_by):
            st.add_blocker(item.slug, ref)
    except _ERRORS as e:
        print(f"tcw work new: {e}", file=sys.stderr)
        rc = 1
    if args.epic:
        st.set_field(item.slug, "type", "epic")
    if args.initiative:
        st.set_field(item.slug, "initiative", args.initiative)
    print(item.slug)
    if not args.epic:                         # epic's next step is delegate, not start
        print(f"→ next: when you begin implementing, run `tcw work start {item.slug}`",
              file=sys.stderr)
    return rc


def _list(args: argparse.Namespace) -> int:
    st = _store()
    if st is None:
        return 1
    items = st.board(status=args.status)
    if args.status is None and not args.all:
        items = [i for i in items if i.status != "completed"]
    present = {i.slug for i in items}
    by_parent: dict[str, list[WorkItem]] = {}
    for it in items:                              # board order preserved per sibling group
        by_parent.setdefault(it.parent, []).append(it)

    def emit(it: WorkItem, depth: int) -> None:
        blockers = st.unresolved_blockers(it)
        suffix = f" | blocked-by: {', '.join(blockers)}" if blockers else ""
        pri = it.priority if it.priority is not None else "-"
        print(f"{'  ' * depth}{it.slug} | {it.status} | {it.phase or '-'} | "
              f"{pri} | {it.title}{suffix}")
        for ch in by_parent.get(it.slug, []):
            emit(ch, depth + 1)

    for it in items:                              # roots first; children ride their parent
        if it.parent in present:                  # a visible parent will emit it
            continue
        emit(it, 0)
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


def _complete_hint(slug: str) -> None:
    print(f"→ next: when done & verified, run "
          f"`tcw work complete {slug} --resolution done --confirm`", file=sys.stderr)


def _start(args: argparse.Namespace) -> int:
    st = _store()
    if st is None:
        return 1
    try:
        st.start(args.slug, force=args.force)
    except _ERRORS as e:
        print(f"tcw work: {e}", file=sys.stderr)
        return 1
    if not args.worktree:
        print(f"started {args.slug}")
        _complete_hint(args.slug)
        return 0
    node = st.node_root
    ensure_worktree_ignored(node)
    st.set_field(args.slug, "worktree", f"{WORKTREES_DIR}/{args.slug}")
    st.set_field(args.slug, "branch", f"work/{args.slug}")
    try:
        git_commit(node, f"tcw work: start {args.slug} (worktree)", "docs/work", ".gitignore")
        wt, _branch = add_worktree(node, args.slug)
    except subprocess.CalledProcessError as e:
        print(f"tcw work start: worktree setup failed: {e.stderr or e}", file=sys.stderr)
        return 1
    print(f"started {args.slug} → worktree {wt}")
    _complete_hint(args.slug)
    return 0


def _edit(args: argparse.Namespace) -> int:
    st = _store()
    if st is None:
        return 1
    try:
        if st.get(args.slug) is None:
            print(f"tcw work edit: no such work item: {args.slug}", file=sys.stderr)
            return 1
        blocks = _split(args.blocks)
        for ref in blocks:
            if st.get(ref) is None:
                print(f"tcw work edit: no such work item: {ref}", file=sys.stderr)
                return 1
        for ref in _split(args.blocked_by):
            st.add_blocker(args.slug, ref)
        for ref in blocks:
            st.add_blocker(ref, args.slug)
        for ref in _split(args.unblocked_by):
            st.remove_blocker(args.slug, ref)
        if args.initiative is not None:
            st.set_field(args.slug, "initiative", args.initiative)
        if args.priority is not None:
            st.set_field(args.slug, "priority", args.priority)
    except _ERRORS as e:
        print(f"tcw work edit: {e}", file=sys.stderr)
        return 1
    print(f"edited {args.slug}")
    return 0


def _complete(args: argparse.Namespace) -> int:
    st = _store()
    if st is None:
        return 1
    try:
        item = st.get(args.slug)
    except MultipleMatch as e:
        print(f"tcw work complete: {e}", file=sys.stderr)
        return 1
    if item is None:
        print(f"tcw work complete: no such work item: {args.slug}", file=sys.stderr)
        return 1
    branch = item.branch or None              # capture before complete moves the folder
    has_worktree = bool(item.worktree)
    if not args.force:
        blockers = st.unresolved_blockers(item)
        if blockers:
            print(f"tcw work complete: blocked by: {', '.join(blockers)} "
                  f"(use --force to override)", file=sys.stderr)
            return 1
    checklist = st.dod_checklist()
    print("Definition of Done — acknowledge each item:")
    for c in checklist:
        print(f"  [ ] {c}")
    if not args.confirm:
        print("Refused: re-run with --confirm once the checklist is satisfied.", file=sys.stderr)
        return 1
    try:
        st.complete(args.slug, args.resolution, dod_ack=checklist, force=args.force)
    except _ERRORS as e:
        print(f"tcw work complete: {e}", file=sys.stderr)
        return 1
    print(f"completed {args.slug} ({args.resolution})")
    if has_worktree:
        for w in remove_worktree(st.node_root, args.slug, branch):
            print(f"tcw work complete: {w}", file=sys.stderr)
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

    g.add_parser("nodes", help="list this node's parent + child nodes").set_defaults(func=_nodes)

    pr = g.add_parser("reconcile", help="scan child nodes → write the epic rollup")
    pr.add_argument("slug")
    pr.add_argument("--commit", action="store_true", help="also commit the rollup")
    pr.set_defaults(func=_reconcile)

    pdg = g.add_parser("delegate", help="write a request into a child node's inbox/")
    pdg.add_argument("child", help="child node path (relative to this node)")
    pdg.add_argument("title")
    pdg.add_argument("--initiative", help="stamp the request with an initiative slug")
    pdg.set_defaults(func=_delegate)

    pes = g.add_parser("escalate", help="write a request into the parent node's inbox/")
    pes.add_argument("title")
    pes.add_argument("--initiative", help="stamp the request with an initiative slug")
    pes.set_defaults(func=_escalate)

    pn = g.add_parser("new", help="create a backlog item; prints its slug")
    pn.add_argument("title")
    pn.add_argument("--priority", type=int, help="integer priority (higher = higher)")
    pn.add_argument("--blocked-by", help="comma-separated slugs/externals that block it")
    pn.add_argument("--epic", action="store_true", help="mark as an epic (type: epic)")
    pn.add_argument("--parent", help="create as a child nested under this item's slug")
    pn.add_argument("--initiative", help="back-pointer slug to an owning epic")
    pn.set_defaults(func=_new)

    pl = g.add_parser("list", help="the board (hides completed unless --status/--all)")
    pl.add_argument("--status")
    pl.add_argument("--all", action="store_true", help="include completed items")
    pl.set_defaults(func=_list)

    psh = g.add_parser("show", help="resolve slug → item; print state + body")
    psh.add_argument("slug")
    psh.set_defaults(func=_show)

    pp = g.add_parser("path", help="print the current path of a slug")
    pp.add_argument("slug")
    pp.set_defaults(func=_path)

    pst = g.add_parser("start", help="inbox|backlog → active")
    pst.add_argument("slug")
    pst.add_argument("--force", action="store_true", help="start despite unresolved blockers")
    pst.add_argument("--worktree", action="store_true",
                     help="isolate the item in its own git worktree + branch")
    pst.set_defaults(func=_start)

    pe = g.add_parser("edit", help="change blocking links between items")
    pe.add_argument("slug")
    pe.add_argument("--blocked-by", help="comma-separated slugs/externals that block this item")
    pe.add_argument("--blocks", help="comma-separated items this item blocks")
    pe.add_argument("--unblocked-by", help="comma-separated blockers to remove")
    pe.add_argument("--priority", type=int, help="set integer priority (higher = higher)")
    pe.add_argument("--initiative", help='set the owning-epic back-pointer (use "" to clear)')
    pe.set_defaults(func=_edit)

    pc = g.add_parser("complete", help="active → completed (DoD gate)")
    pc.add_argument("slug")
    pc.add_argument("--resolution", required=True, choices=sorted(WORK_RESOLUTIONS))
    pc.add_argument("--confirm", action="store_true")
    pc.add_argument("--force", action="store_true", help="complete despite unresolved blockers")
    pc.set_defaults(func=_complete)

    pd = g.add_parser("drop", help="inbox|backlog → deleted")
    pd.add_argument("slug")
    pd.set_defaults(func=_drop)
