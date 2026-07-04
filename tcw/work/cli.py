"""`tcw work` — the changes. Single-node state machine per phase-5-work B.2."""

import argparse
import subprocess
import sys

from tcw.store.base import (
    WORK_RESOLUTIONS, _UNSET, IllegalTransition, MultipleMatch, WorkItem,
    normalize_work_level,
)
from tcw.store.fs import (
    COMPONENTS, WORKTREES_DIR, FsWorkStore, add_worktree, child_nodes,
    descendant_nodes, ensure_worktree_ignored, find_node, git_commit,
    merge_worktree, parent_node, remove_worktree, resolve_qualified_work_ref,
)
from tcw.work.recursion import delegate, escalate, reconcile

NAME = "work"
SUBCOMMANDS = {"init", "new", "list", "show", "path", "start", "edit", "complete",
               "drop", "nodes", "reconcile", "delegate", "escalate"}
DEFAULT_SUBCOMMAND = None  # work uses explicit show/path (slugs aren't tree paths)

_ERRORS = (ValueError, IllegalTransition, MultipleMatch)


def _work_level(value: str) -> str:
    """argparse ``type=`` for --effort/--complexity: normalize input to canonical,
    re-raising as ArgumentTypeError so the message reaches the user cleanly."""
    try:
        return normalize_work_level(value)
    except ValueError as e:
        raise argparse.ArgumentTypeError(str(e))


def _store() -> FsWorkStore | None:
    node = find_node(NAME)
    if node is None:
        print("tcw work: no tcw work node here — run `tcw init` in the project folder.", file=sys.stderr)
        return None
    return FsWorkStore.open(node)


def _resolve(slug: str, label: str) -> tuple[FsWorkStore, str] | None:
    """Resolve a (possibly subproject-qualified) slug to (store, bare_slug).

    A bare slug stays on the anchor node (unchanged); `sub/proj/<slug>` resolves
    to the descendant node's store — equivalent to `cd`-ing there first. Prints
    the right message and returns None on failure (no work node here, or the
    qualifier names no real node) so callers just `return 1`. Item existence is
    still the caller's `get`/`path` check — the returned slug is always bare."""
    node = find_node(NAME)
    if node is None:
        print("tcw work: no tcw work node here — run `tcw init` in the project folder.", file=sys.stderr)
        return None
    resolved = resolve_qualified_work_ref(node, slug)
    if resolved is None:                          # qualifier names no node within anchor
        print(f"tcw work {label}: no such work item: {slug}", file=sys.stderr)
        return None
    return resolved


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
    if item.type:
        print(f"type: {item.type}")
    if item.initiative:
        print(f"initiative: {item.initiative}")
    if item.phase:
        print(f"phase: {item.phase}")
    if item.priority is not None:
        print(f"priority: {item.priority}")
    if item.effort:
        print(f"effort: {item.effort}")
    if item.complexity:
        print(f"complexity: {item.complexity}")
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
        print("tcw work: no tcw work node here — run `tcw init` in the project folder.", file=sys.stderr)
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
        print("tcw work: no tcw work node here — run `tcw init` in the project folder.", file=sys.stderr)
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
        print("tcw work: no tcw work node here — run `tcw init` in the project folder.", file=sys.stderr)
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
        print("tcw work: no tcw work node here — run `tcw init` in the project folder.", file=sys.stderr)
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


def _provided(value):
    """Map CLI ``None`` (not provided) → ``_UNSET`` sentinel so the store
    can distinguish 'omitted' from 'set to null'."""
    return value if value is not None else _UNSET


def _new(args: argparse.Namespace) -> int:
    st = _store()
    if st is None:
        return 1
    try:
        detail = st.create_work(
            args.title,
            body=_stdin_body(),
            priority=args.priority,
            effort=args.effort or "",
            complexity=args.complexity or "",
            blockers=_split(args.blocked_by) or None,
            parent=args.parent,
            initiative=args.initiative or "",
            type="epic" if args.epic else "",
        )
        item = detail.item
    except _ERRORS as e:
        print(f"tcw work new: {e}", file=sys.stderr)
        return 1
    print(item.slug)
    body = st.body_path(item.slug)
    if body is not None:
        print(f"→ edit: {body}", file=sys.stderr)
    if not args.epic:                         # epic's next step is delegate, not start
        print(f"→ next: when you begin implementing, run `tcw work start {item.slug}`",
              file=sys.stderr)
    return 0


def _render_board(st: FsWorkStore, status: str | None, show_all: bool,
                  prefix: str = "") -> None:
    items = st.board(status=status)
    if status is None and not show_all:
        items = [i for i in items if i.status != "completed"]
    present = {i.slug for i in items}
    by_parent: dict[str, list[WorkItem]] = {}
    for it in items:                              # board order preserved per sibling group
        by_parent.setdefault(it.parent, []).append(it)

    def stages(it: WorkItem) -> str:
        labels = {
            "initial-request": "R",
            "spec": "S",
            "plan": "P",
            "outcome": "O",
            "refined-outcome": "F",
        }
        out = ""
        for artifact in st.artifacts(it.slug):
            if artifact.present:
                out += labels[artifact.name]
        return out or "-"

    def emit(it: WorkItem, depth: int) -> None:
        blockers = st.unresolved_blockers(it)
        suffix = f" | blocked-by: {', '.join(blockers)}" if blockers else ""
        pri = it.priority if it.priority is not None else "-"
        print(f"{'  ' * depth}{prefix}{it.slug} | {it.status} | {stages(it)} | "
              f"{pri} | {it.title}{suffix}")
        for ch in by_parent.get(it.slug, []):
            emit(ch, depth + 1)

    for it in items:                              # roots first; children ride their parent
        if it.parent in present:                  # a visible parent will emit it
            continue
        emit(it, 0)


def _list(args: argparse.Namespace) -> int:
    st = _store()
    if st is None:
        return 1
    if not args.include_descendants:
        _render_board(st, args.status, args.all)
        return 0
    node = st.node_root.resolve()                 # descendant_nodes returns resolved
    for i, root in enumerate([node, *descendant_nodes(node)]):   # paths → relative_to
        if i:
            print()                               # blank line between node groups
        rel = "." if root == node else f"./{root.relative_to(node)}"
        print(f"# {rel}")
        prefix = "" if root == node else f"{root.relative_to(node)}/"  # qualified slugs
        _render_board(FsWorkStore.open(root), args.status, args.all, prefix)
    return 0


def _show(args: argparse.Namespace) -> int:
    resolved = _resolve(args.slug, "show")
    if resolved is None:
        return 1
    st, bare = resolved
    try:
        item = st.get(bare)
    except MultipleMatch as e:
        print(f"tcw work show: {e}", file=sys.stderr)
        return 1
    if item is None:
        print(f"tcw work show: no such work item: {args.slug}", file=sys.stderr)
        return 1
    _print_item(item)
    return 0


def _path(args: argparse.Namespace) -> int:
    resolved = _resolve(args.slug, "path")
    if resolved is None:
        return 1
    st, bare = resolved
    try:
        p = st.path(bare)
    except MultipleMatch as e:                    # wrap consistently with _show/_complete
        print(f"tcw work path: {e}", file=sys.stderr)
        return 1
    if p is None:
        print(f"tcw work path: no such work item: {args.slug}", file=sys.stderr)
        return 1
    print(p)
    return 0


def _complete_hint(slug: str) -> None:
    print(f"→ next: when done & verified, run "
          f"`tcw work complete {slug} --resolution done --confirm`", file=sys.stderr)


def _start(args: argparse.Namespace) -> int:
    resolved = _resolve(args.slug, "start")
    if resolved is None:
        return 1
    st, bare = resolved
    try:
        st.start(bare, force=args.force)
    except _ERRORS as e:
        print(f"tcw work: {e}", file=sys.stderr)
        return 1
    if not args.worktree:
        print(f"started {args.slug}")
        _complete_hint(args.slug)
        return 0
    node = st.node_root
    ensure_worktree_ignored(node)
    st.set_field(bare, "worktree", f"{WORKTREES_DIR}/{bare}")
    st.set_field(bare, "branch", f"work/{bare}")
    try:
        git_commit(node, f"tcw work: start {bare} (worktree)", "docs/work", ".gitignore")
        wt, _branch = add_worktree(node, bare)
    except subprocess.CalledProcessError as e:
        print(f"tcw work start: worktree setup failed: {e.stderr or e}", file=sys.stderr)
        return 1
    print(f"started {args.slug} → worktree {wt}")
    _complete_hint(args.slug)
    return 0


def _edit(args: argparse.Namespace) -> int:
    resolved = _resolve(args.slug, "edit")
    if resolved is None:
        return 1
    st, bare = resolved                           # blocker refs are node-local to `st`
    try:
        if st.get(bare) is None:
            print(f"tcw work edit: no such work item: {args.slug}", file=sys.stderr)
            return 1
        blocks = _split(args.blocks)
        for ref in blocks:
            if st.get(ref) is None:
                print(f"tcw work edit: no such work item: {ref}", file=sys.stderr)
                return 1
        for ref in _split(args.blocked_by):
            st.add_blocker(bare, ref)
        for ref in blocks:
            st.add_blocker(ref, bare)             # reverse link: bare into ref's blocked_by
        for ref in _split(args.unblocked_by):
            st.remove_blocker(bare, ref)
        # Use composite update for field changes
        st.update_work(
            bare,
            initiative=_provided(args.initiative),
            priority=_provided(args.priority),
            effort=_provided(args.effort),
            complexity=_provided(args.complexity),
        )
    except _ERRORS as e:
        print(f"tcw work edit: {e}", file=sys.stderr)
        return 1
    print(f"edited {args.slug}")
    return 0


def _complete(args: argparse.Namespace) -> int:
    resolved = _resolve(args.slug, "complete")
    if resolved is None:
        return 1
    st, bare = resolved
    try:
        item = st.get(bare)
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
    if has_worktree and branch:                       # merge-back before the rename/teardown
        err = merge_worktree(st.node_root, branch)
        if err:
            print(f"tcw work complete: {err}", file=sys.stderr)
            return 1
    try:
        st.complete(bare, args.resolution, dod_ack=checklist, force=args.force)
    except _ERRORS as e:
        print(f"tcw work complete: {e}", file=sys.stderr)
        return 1
    print(f"completed {args.slug} ({args.resolution})")
    if has_worktree:
        for w in remove_worktree(st.node_root, bare, branch):
            print(f"tcw work complete: {w}", file=sys.stderr)
    return 0


def _drop(args: argparse.Namespace) -> int:
    resolved = _resolve(args.slug, "drop")
    if resolved is None:
        return 1
    st, bare = resolved
    try:
        st.drop(bare)
    except _ERRORS as e:
        print(f"tcw work: {e}", file=sys.stderr)
        return 1
    print(f"dropped {args.slug}")
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
    pn.add_argument("--effort", type=_work_level,
                    help="estimated effort: low|medium|high|very-high (or L/M/H/VH)")
    pn.add_argument("--complexity", type=_work_level,
                    help="estimated complexity: low|medium|high|very-high (or L/M/H/VH)")
    pn.add_argument("--blocked-by", help="comma-separated slugs/externals that block it")
    pn.add_argument("--epic", action="store_true", help="mark as an epic (type: epic)")
    pn.add_argument("--parent", help="create as a child nested under this item's slug")
    pn.add_argument("--initiative", help="back-pointer slug to an owning epic")
    pn.set_defaults(func=_new)

    pl = g.add_parser("list", help="the board (hides completed unless --status/--all)")
    pl.add_argument("--status")
    pl.add_argument("--all", action="store_true", help="include completed items")
    pl.add_argument("--include-descendants", action="store_true",
                    help="also list every descendant work node's board, grouped by node")
    pl.set_defaults(func=_list)

    psh = g.add_parser("show", help="resolve slug → item; print state + body")
    psh.add_argument("slug")
    psh.set_defaults(func=_show)

    pp = g.add_parser("path", help="print the current work item folder path")
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
    pe.add_argument("--effort", type=_work_level,
                    help="set estimated effort: low|medium|high|very-high (or L/M/H/VH)")
    pe.add_argument("--complexity", type=_work_level,
                    help="set estimated complexity: low|medium|high|very-high (or L/M/H/VH)")
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
