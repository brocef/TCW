"""`tcw work` — the changes. Single-node state machine per phase-5-work B.2."""

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

from tcw.store.base import (
    DEFAULT_OUTPUT_CAP, RESOLVED_STATUSES, STAGE_STATUSES, WORK_ARTIFACTS,
    WORK_RESOLUTIONS, WORK_STATUSES, _UNSET,
    IllegalTransition, LIFECYCLE_STEPS, LIFECYCLE_STEPS_BY_ID, MultipleMatch,
    StoreNotProvisioned, TransitionCommitError, WorkItem, normalize_tag, AlreadyClaimed,
    normalize_work_level, resolution_status,
)
from tcw.store.fs import (
    COMPONENTS, NOT_A_REPOSITORY, WORKTREES_DIR, FsWorkStore, add_worktree,
    child_nodes, descendant_nodes, ensure_worktree_ignored, find_node,
    git_commit_result, git_root, merge_worktree, parent_node,
    qualified_work_ref_problem, registered_project_id, remove_worktree,
    resolve_qualified_work_ref,
)
from tcw.stdin import read_piped_stdin
from tcw.store.project import worktree_anchors
from tcw.work.hooks import hook_env, run_bindings, run_post, run_pre
from tcw.work.projection import work_item_json
from tcw.work.resolve import (
    ResolveError, load_builtins, resolve_artifact, resolve_prompts, select,
)
from tcw.work.recursion import capability_gate, delegate, escalate, reconcile

NAME = "work"
SUBCOMMANDS = {"init", "inbox", "new", "list", "show", "path", "start", "submit",
               "rework", "edit", "complete", "drop", "nodes", "reconcile", "delegate",
               "escalate", "tags", "lifecycle", "stage", "scaffold", "docs"}
DEFAULT_SUBCOMMAND = None  # work uses explicit show/path (slugs aren't tree paths)

# TransitionCommitError is included deliberately: the item *did* move, and its
# message says so. The non-zero exit is the point — a refused commit must not
# read as success — but nothing here should imply the transition failed.
_ERRORS = (ValueError, IllegalTransition, MultipleMatch, TransitionCommitError, AlreadyClaimed)


def _work_level(value: str) -> str:
    """argparse ``type=`` for --effort/--complexity: normalize input to canonical,
    re-raising as ArgumentTypeError so the message reaches the user cleanly."""
    try:
        return normalize_work_level(value)
    except ValueError as e:
        raise argparse.ArgumentTypeError(str(e))


def _nonempty(value: str) -> str:
    """argparse ``type=`` for --title: `create_work` refuses an empty title, so
    `edit` must too — otherwise the CLI can reach a state creation forbids."""
    if not value.strip():
        raise argparse.ArgumentTypeError("title must be non-empty")
    return value


def _tag(value: str) -> str:
    """argparse ``type=`` for --tag/--untag: normalize to a canonical slug."""
    try:
        return normalize_tag(value)
    except ValueError as e:
        raise argparse.ArgumentTypeError(str(e))


def _require_node() -> Path | None:
    """This node, or None after saying why there isn't one.

    One place, because there are two different "no store" answers and they need
    different words. An *absent* node is what `tcw init` fixes. A node whose
    store is declared elsewhere and simply not here yet is not missing at all —
    it needs provisioning, and `tcw init` would scaffold a second, empty store
    beside the real one. That advice used to be printed at six call sites, which
    is why it could not be improved in one.
    """
    try:
        node = find_node(NAME)
    except StoreNotProvisioned as e:
        print(f"tcw work: {e}", file=sys.stderr)
        return None
    if node is None:
        print("tcw work: no tcw work node here — run `tcw init` in the project folder.",
              file=sys.stderr)
    return node


def _store() -> FsWorkStore | None:
    node = _require_node()
    if node is None:
        return None
    return FsWorkStore.open(node)


def _resolve(slug: str, label: str) -> tuple[FsWorkStore, str] | None:
    """Resolve a (possibly subproject-qualified) slug to (store, bare_slug).

    A bare slug stays on the anchor node (unchanged); `<project-id>/<slug>`
    resolves to that node's store — equivalent to `cd`-ing there first — for any
    node in the registered graph, in any direction. Prints the right message and
    returns None on failure (no work node here, or the qualifier names no
    registered project) so callers just `return 1`. Item existence is still the
    caller's `get`/`path` check — the returned slug is always bare."""
    node = _require_node()
    if node is None:
        return None
    resolved = resolve_qualified_work_ref(node, slug)
    if resolved is None:
        print(f"tcw work {label}: {qualified_work_ref_problem(node, slug)}", file=sys.stderr)
        return None
    return resolved


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
    if item.priority is not None:
        print(f"priority: {item.priority}")
    if item.effort:
        print(f"effort: {item.effort}")
    if item.complexity:
        print(f"complexity: {item.complexity}")
    if item.tags:
        print(f"tags: {', '.join(item.tags)}")
    if item.resolution:
        print(f"resolution: {item.resolution}")
    if item.owner:
        print(f"owner: {item.owner}")
    if item.started:
        print(f"started: {item.started}")
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
    node = _require_node()
    if node is None:
        return 1
    parent = parent_node(node)
    print(f"node:   {registered_project_id(node, node)}")
    print(f"parent: {registered_project_id(node, parent) if parent else '(none — root)'}")
    children = child_nodes(node)
    if children:
        print("children:")
        for c in children:
            print(f"  {registered_project_id(node, c)}")
    else:
        print("children: (none — leaf)")
    return 0


def _reconcile(args: argparse.Namespace) -> int:
    node = _require_node()
    if node is None:
        return 1
    try:
        block = reconcile(node, args.slug, commit=args.commit,
                          complete_when_ready=args.complete_when_ready)
    except _ERRORS as e:
        print(f"tcw work reconcile: {e}", file=sys.stderr)
        return 1
    print(block)
    return 0


def _delegate(args: argparse.Namespace) -> int:
    node = _require_node()
    if node is None:
        return 1
    try:
        doc = delegate(node, args.child, args.title, body=read_piped_stdin(),
                       initiative=args.initiative)
    except _ERRORS as e:
        print(f"tcw work delegate: {e}", file=sys.stderr)
        return 1
    print(doc)
    return 0


def _escalate(args: argparse.Namespace) -> int:
    node = _require_node()
    if node is None:
        return 1
    try:
        doc = escalate(node, args.title, body=read_piped_stdin(),
                       initiative=args.initiative)
    except _ERRORS as e:
        print(f"tcw work escalate: {e}", file=sys.stderr)
        return 1
    print(doc)
    print("Reminder: start an orchestrator session to triage the parent's inbox.",
          file=sys.stderr)
    return 0


def _init(args: argparse.Namespace) -> int:
    from tcw.cli import run_init      # function-local: top-level cli imports this module
    return run_init([NAME], args.id, args.path)


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
            intake=read_piped_stdin(),   # piped text is raw input, not a request
            priority=args.priority,
            effort=args.effort or "",
            complexity=args.complexity or "",
            blockers=args.blocked_by or None,
            parent=args.parent,
            initiative=args.initiative or "",
            type="epic" if args.epic else "",
            tags=args.tag or None,
        )
        item = detail.item
    except _ERRORS as e:
        print(f"tcw work new: {e}", file=sys.stderr)
        return 1
    print(item.slug)
    if loc := st.locate(item.slug):
        print(f"→ created at {loc}", file=sys.stderr)
    body = st.body_path(item.slug)
    if body is not None:
        print(f"→ edit: {body}", file=sys.stderr)
    if not args.epic:                         # epic's next step is delegate, not start
        print(f"→ next: when you begin implementing, run `tcw work start {item.slug}`",
              file=sys.stderr)
    return 0


def _inbox_list(args: argparse.Namespace) -> int:
    st = _store()
    if st is None:
        return 1
    for entry in st.inbox_list():
        print(f"{entry.ref} | {entry.kind} | {entry.title}")
    return 0


def _inbox_show(args: argparse.Namespace) -> int:
    st = _store()
    if st is None:
        return 1
    try:
        detail = st.inbox_show(args.entry)
    except _ERRORS as e:
        print(f"tcw work inbox show: {e}", file=sys.stderr)
        return 1
    print(f"{detail.entry.ref}  [{detail.entry.kind}]")
    print(f"title: {detail.entry.title}")
    print("resources:")
    for resource in detail.resources:
        readable = "text" if resource.readable else "binary"
        print(f"  {resource.name} | {resource.size} bytes | {resource.media_type} | {readable}")
    if detail.body is not None:
        print("\nbody:\n")
        print(detail.body, end="" if detail.body.endswith("\n") else "\n")
    return 0


def _inbox_path(args: argparse.Namespace) -> int:
    st = _store()
    if st is None:
        return 1
    print(st.inbox_root)
    return 0


def _inbox_accept(args: argparse.Namespace) -> int:
    st = _store()
    if st is None:
        return 1
    try:
        item = st.inbox_accept(args.entry, title=args.title)
    except _ERRORS as e:
        print(f"tcw work inbox accept: {e}", file=sys.stderr)
        return 1
    print(item.slug)
    if loc := st.locate(item.slug):
        print(f"→ now at {loc}", file=sys.stderr)
    return 0


def _visible_board_items(st: FsWorkStore, status: str | None, show_all: bool,
                         tags: list[str] | None = None) -> list[WorkItem]:
    items = st.board(status=status)
    if status is None and not show_all:
        items = [i for i in items if i.status not in RESOLVED_STATUSES]
    if tags:                                       # --tag filter: match-any (OR)
        wanted = set(tags)
        items = [i for i in items if wanted & set(i.tags)]
    return items


def _render_board_item(st: FsWorkStore, it: WorkItem, prefix: str, depth: int) -> None:
    # Display order, not registry order: WORK_ARTIFACTS is append-only so that
    # adding a name never shifts an existing item's letters, which leaves the
    # newest entry last no matter where it belongs in the lifecycle. `intake`
    # comes before the request, so the string still reads chronologically.
    labels = {
        "intake": "i",
        "initial-request": "R",
        "spec": "S",
        "plan": "P",
        "outcome": "O",
        "refined-outcome": "F",
        "rework": "W",
        "post-mortem": "M",
    }
    present = {a.name for a in st.artifacts(it.slug) if a.present}
    stages = "".join(letter for name, letter in labels.items() if name in present)
    # A name in the registry with no letter here must not vanish silently.
    stages += "?" * len(present - labels.keys())
    blockers = st.unresolved_blockers(it)
    suffix = f" | blocked-by: {', '.join(blockers)}" if blockers else ""
    ready = " | ready-to-close" if it.type == "epic" and st.epic_completable(it) else ""
    tag_seg = f" | [{', '.join(it.tags)}]" if it.tags else ""
    pri = it.priority if it.priority is not None else "-"
    claim = ""
    if it.status == "active":
        claim = (f" | owner: {it.owner} | started: {it.started}"
                 if it.owner else " | owner: unclaimed")
    print(f"{'  ' * depth}{prefix}{it.slug} | {it.status} | {stages or '-'} | "
          f"{pri} | {it.title}{tag_seg}{ready}{suffix}{claim}")


def _render_board(st: FsWorkStore, status: str | None, show_all: bool,
                  prefix: str = "", tags: list[str] | None = None) -> None:
    items = _visible_board_items(st, status, show_all, tags)
    present = {i.slug for i in items}
    by_parent: dict[str, list[WorkItem]] = {}
    for it in items:                              # board order preserved per sibling group
        by_parent.setdefault(it.parent, []).append(it)

    def emit(it: WorkItem, depth: int) -> None:
        _render_board_item(st, it, prefix, depth)
        for ch in by_parent.get(it.slug, []):
            emit(ch, depth + 1)

    for it in items:                              # roots first; children ride their parent
        if it.parent in present:                  # a visible parent will emit it
            continue
        emit(it, 0)


def _render_descendant_boards(anchor: FsWorkStore, status: str | None,
                              show_all: bool, tags: list[str] | None) -> None:
    """Render the anchor plus registered descendants as one ownership forest.

    Node headers remain in registered order, while visible local-parent and
    initiative relationships decide row indentation across those node bounds.
    The filesystem adapter's registered parent relation resolves an initiative
    child only toward its local node or ancestors; nearby/unregistered stores
    never participate.
    """
    anchor_root = anchor.node_root.resolve()
    roots = [anchor_root, *descendant_nodes(anchor_root)]
    stores = {root: FsWorkStore.open(root) for root in roots}
    prefixes = {
        root: "" if root == anchor_root else f"{registered_project_id(anchor_root, root)}/"
        for root in roots
    }
    entries: list[tuple[Path, FsWorkStore, WorkItem]] = []
    for root in roots:
        st = stores[root]
        entries.extend((root, st, item)
                       for item in _visible_board_items(st, status, show_all, tags))

    by_key = {(root, item.slug): (root, st, item) for root, st, item in entries}
    children: dict[tuple[Path, str], list[tuple[Path, FsWorkStore, WorkItem]]] = {}
    owned: set[tuple[Path, str]] = set()
    for entry in entries:
        root, _, item = entry
        key = (root, item.slug)
        owner: tuple[Path, str] | None = None
        if item.parent and (root, item.parent) in by_key:
            owner = (root, item.parent)
        elif item.initiative:
            candidate_root: Path | None = root
            while candidate_root is not None:
                candidate_key = (candidate_root, item.initiative)
                candidate = by_key.get(candidate_key)
                if candidate is not None and candidate[2].type == "epic":
                    owner = candidate_key
                    break
                candidate_root = parent_node(candidate_root)
        if owner is not None and owner != key:
            children.setdefault(owner, []).append(entry)
            owned.add(key)

    emitted: set[tuple[Path, str]] = set()

    def emit(entry: tuple[Path, FsWorkStore, WorkItem], depth: int) -> None:
        root, st, item = entry
        key = (root, item.slug)
        if key in emitted:                         # defensive against malformed cycles
            return
        emitted.add(key)
        _render_board_item(st, item, prefixes[root], depth)
        for child in children.get(key, []):
            emit(child, depth + 1)

    for index, root in enumerate(roots):
        if index:
            print()
        label = "." if root == anchor_root else registered_project_id(anchor_root, root)
        print(f"# {label}")
        node_entries = [entry for entry in entries if entry[0] == root]
        for entry in node_entries:
            key = (root, entry[2].slug)
            if key not in owned:
                emit(entry, 0)
        for entry in node_entries:                 # malformed ownership cycle fallback
            emit(entry, 0)


def _list(args: argparse.Namespace) -> int:
    st = _store()
    if st is None:
        return 1
    if not args.include_descendants:
        _render_board(st, args.status, args.all, tags=args.tag)
        return 0
    _render_descendant_boards(st, args.status, args.all, args.tag)
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
    if getattr(args, "json", False):
        # Built and encoded before anything is printed, so a projection failure
        # leaves stdout empty rather than half a document for `jq` to choke on.
        # No `default=`: the DTO is JSON-native by construction, and allow_nan
        # is the guard for the case where it turns out not to be.
        try:
            doc = work_item_json(item, st.artifacts(bare))
            text = json.dumps(doc, indent=2, sort_keys=True, allow_nan=False)
        except (ValueError, TypeError) as e:
            print(f"tcw work show: cannot project {bare} as JSON: {e}",
                  file=sys.stderr)
            return 1
        print(text)
        return 0
    _print_item(item)
    return 0


def _path(args: argparse.Namespace) -> int:
    if args.slug is None:
        st = _store()
        if st is None:
            return 1
        print(st.root)
        return 0
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


def _post_result(err: str | None, transition: str, slug: str) -> int:
    """Report a `post` hook failure without pretending the transition failed.

    The move and its commit have already happened; unwinding a committed
    transition is worse than the failure. Exit non-zero so nothing downstream
    reads this as clean, but say plainly that the item moved.
    """
    if err is None:
        return 0
    print(f"tcw work {transition}: {err}. {slug} moved and was committed; the "
          f"hook failure does not roll that back.", file=sys.stderr)
    return 1


def _complete_hint(slug: str) -> None:
    print(f"→ next: when done & verified, run "
          f"`tcw work complete {slug} --resolution done --confirm`", file=sys.stderr)


def _start(args: argparse.Namespace) -> int:
    resolved = _resolve(args.slug, "start")
    if resolved is None:
        return 1
    st, bare = resolved
    # `--worktree` writes the *node's* `.gitignore` and creates the worktree
    # there. That is not always the repository the store guard checks: an
    # external `work.path` splits ownership, and then `st.start` passes against
    # the store's repository while the node has none — which used to move the
    # item, write `.gitignore`, and only then die in `git add`. Checked here, so
    # a refusal means nothing happened at all, and worded as the shared sentence
    # so the single-repository case still refuses with one wording.
    if args.worktree and git_root(st.node_root) is None:
        print(f"tcw work start: {NOT_A_REPOSITORY}", file=sys.stderr)
        return 1
    # `pre` hooks run before the store is touched at all — not merely before the
    # move. A hook is allowed to refuse the transition, and a refusal has to mean
    # nothing happened; evaluating one after any store call would make that false.
    if (err := run_pre(st.lifecycle_policy(), "start", st.node_root, bare, "backlog",
                       st.get(bare))):
        print(f"tcw work start: {err}; {bare} not started", file=sys.stderr)
        return 1
    owner = (args.owner or os.environ.get("TCW_WORK_OWNER", "")).strip()
    if not owner:
        for key in ("user.email", "user.name"):
            probe = subprocess.run(["git", "-C", str(st.node_root), "config", "--get", key],
                                   stdin=subprocess.DEVNULL,
                                   capture_output=True, text=True)
            if probe.returncode == 0 and probe.stdout.strip():
                owner = probe.stdout.strip()
                break
    if not owner:
        print("tcw work start: claimant identity required; pass --owner or set TCW_WORK_OWNER",
              file=sys.stderr)
        return 1
    try:
        st.start(bare, force=args.force, owner=owner, take_over=args.take_over)
    except _ERRORS as e:
        print(f"tcw work: {e}", file=sys.stderr)
        return 1
    post_err = run_post(st.lifecycle_policy(), "start", st.node_root, bare, "active",
                        st.get(bare))
    if not args.worktree:
        loc = st.locate(bare)
        print(f"started {args.slug}" + (f" → {loc}" if loc else ""))
        _complete_hint(args.slug)
        return _post_result(post_err, "start", args.slug)
    node = st.node_root
    ignore_changed = ensure_worktree_ignored(node)
    st.set_field(bare, "worktree", f"{WORKTREES_DIR}/{bare}")
    st.set_field(bare, "branch", f"work/{bare}")
    # The store already committed the status move (unless auto-commit is off).
    # What is still uncommitted is `.gitignore` and the worktree/branch fields
    # written just above — and both must land before `add_worktree`, because the
    # work branch is created from HEAD and would otherwise not carry them.
    #
    # Two owners, and they are not always the same repository: the work store
    # owns the item folder, the code node owns `.gitignore` and the worktree.
    # The pathspec deliberately names both status folders. With auto-commit off
    # the move is still staged and this commit is the one that records it, and a
    # staged rename needs both halves or the deletion is left behind.
    # `git_commit_result` drops pathspecs git has nothing for, so listing the
    # already-committed source folder is harmless. It stays scoped to *this*
    # item — naming the store root would sweep in every other staged work-store
    # change.
    #
    # `--worktree` commits regardless of `auto-commit-transitions`: with the
    # setting off and no commit here, the branch would be created without the
    # item's own status move on it, producing a worktree whose item is not in it.
    same_repo = st.store_git_root == node
    rel = st.root.relative_to(st.store_git_root)
    store_paths = [str(rel / "backlog" / bare), str(rel / "active" / bare)]
    if same_repo and ignore_changed:      # one repository, one commit, as before
        store_paths.append(".gitignore")
        ignore_changed = False
    what = "worktree" if same_repo else "worktree metadata"
    err = git_commit_result(st.store_git_root, f"tcw work: start {bare} ({what})",
                            *store_paths)
    if err:
        print(f"tcw work start: {bare} is active, but committing the worktree "
              f"setup in {st.store_git_root} failed; no worktree was created:\n{err}",
              file=sys.stderr)
        return 1
    if ignore_changed:                    # split repositories: the code node's half
        err = git_commit_result(node, f"tcw work: start {bare} (worktree ignore)",
                                ".gitignore")
        if err:
            print(f"tcw work start: {bare} metadata was committed in "
                  f"{st.store_git_root}, but committing .gitignore in {node} failed; "
                  f"no worktree was created:\n{err}", file=sys.stderr)
            return 1
    try:
        wt, _branch = add_worktree(node, bare)
    except subprocess.CalledProcessError as e:
        print(f"tcw work start: worktree setup failed: {e.stderr or e}", file=sys.stderr)
        return 1
    loc = st.locate(bare)
    print(f"started {args.slug} → {loc} (worktree {wt})" if loc
          else f"started {args.slug} → worktree {wt}")
    _complete_hint(args.slug)
    return _post_result(post_err, "start", args.slug)


def _submit(args: argparse.Namespace) -> int:
    resolved = _resolve(args.slug, "submit")
    if resolved is None:
        return 1
    st, bare = resolved
    if (err := run_pre(st.lifecycle_policy(), "submit", st.node_root, bare, "active",
                       st.get(bare))):
        print(f"tcw work submit: {err}; {bare} not moved", file=sys.stderr)
        return 1
    try:
        st.submit(bare)
    except _ERRORS as e:
        print(f"tcw work: {e}", file=sys.stderr)
        return 1
    post_err = run_post(st.lifecycle_policy(), "submit", st.node_root, bare, "review",
                        st.get(bare))
    print(f"submitted {args.slug} → review")
    print(f"→ next: verify the work, then either "
          f"`tcw work complete {args.slug} --resolution done --confirm` or, to "
          f"send it back, delete refined-outcome.md and run "
          f"`tcw work rework {args.slug}`", file=sys.stderr)
    return _post_result(post_err, "submit", args.slug)


def _rework(args: argparse.Namespace) -> int:
    resolved = _resolve(args.slug, "rework")
    if resolved is None:
        return 1
    st, bare = resolved
    if (err := run_pre(st.lifecycle_policy(), "rework", st.node_root, bare, "review",
                       st.get(bare))):
        print(f"tcw work rework: {err}; {bare} not moved", file=sys.stderr)
        return 1
    try:
        st.rework(bare)
    except _ERRORS as e:
        print(f"tcw work: {e}", file=sys.stderr)
        return 1
    post_err = run_post(st.lifecycle_policy(), "rework", st.node_root, bare, "active",
                        st.get(bare))
    print(f"reworking {args.slug} → active")
    print(f"→ next: address rework.md, then `tcw work submit {args.slug}`",
          file=sys.stderr)
    return _post_result(post_err, "rework", args.slug)


def _lifecycle_lines(step, bindings_for) -> list[str]:
    """Human-readable block for one step. `bindings_for(step)` yields
    (label, [Binding]) pairs so stages and transitions render alike."""
    out = [f"{step.id}  [{step.kind}]", f"  {step.objective}"]
    if step.moves:
        out.append(f"  moves:    {step.moves}")
    if step.inputs:
        out.append(f"  inputs:   {', '.join(step.inputs)}")
    if step.produces_note:
        out.append(f"  produces: {step.produces_note}")
    if step.gates:
        out.append(f"  gates:    {'; '.join(step.gates)}")
    for label, bindings in bindings_for(step):
        if bindings:
            refs = ", ".join(f"{b.kind}:{b.ref}" for b in bindings)
            out.append(f"  {label:9}{refs}")
    return out


def _directive_text(step, bindings, grouped: bool = True) -> str:
    """One complete instruction, or "" when nothing is bound.

    Never a bare value: this is injected verbatim into an agent's context, so an
    unbound id has to render as *nothing* rather than as a broken sentence.

    `grouped` is the **legacy** rendering: all skills ahead of all commands,
    regardless of declaration order. That is what a bare stage list has always
    produced, so a naive move to declaration order would silently change output
    this repo's own criterion requires to be byte-identical. An explicit
    `prompt:` list is new syntax and renders in the order it was written.
    """
    if not bindings:
        return ""
    where = "this stage" if step.kind == "stage" else f"the {step.id} transition"
    if grouped:
        skills = [b.ref for b in bindings if b.kind == "skill"]
        commands = [b.ref for b in bindings if b.kind == "command"]
        parts = []
        if skills:
            parts.append(f"invoke the {' then '.join(skills)} skill"
                         f"{'s' if len(skills) > 1 else ''}")
        if commands:
            parts.append("run " + " then ".join(f"`{c}`" for c in commands))
        return f"For {where}, {' and '.join(parts)}."

    # Declaration order. The text-producing kinds (blob/file/generate/builtin)
    # cannot be inlined here: `tcw work lifecycle` executes nothing, so naming a
    # `generate` script's output would mean running it. They collapse into one
    # clause, at the position of the first one.
    parts: list[str] = []
    named_text = False
    for b in bindings:
        if b.kind == "skill":
            parts.append(f"invoke the {b.ref} skill")
        elif b.kind == "command":
            parts.append(f"run `{b.ref}`")
        elif not named_text:
            parts.append("read this node's configured instructions")
            named_text = True
    return f"For {where}, {' and '.join(parts)}." if parts else ""


def _binding_json(b) -> dict:
    """A binding as `--json` reports it.

    `{kind: value}` is the shape this payload has always had, so a legacy
    `skill`/`command` binding serializes exactly as before. `builtin` reports
    `true` — its configured form — rather than the empty string it parses to,
    and `when` appears only when there is one. A legacy config has neither, so
    its payload is byte-identical.
    """
    out: dict = {b.kind: True if b.kind == "builtin" else b.ref}
    if b.when is not None:
        w: dict = {}
        if b.when.tags:
            w["tags"] = list(b.when.tags)
        if b.when.not_tags:
            w["not_tags"] = list(b.when.not_tags)
        if b.when.type is not None:
            w["type"] = b.when.type
        out["when"] = w
    return out


def _stage_without_item(args: argparse.Namespace, step) -> int:
    """The `inbox` half of `tcw work stage`: same contract, no item.

    Every step the item path takes that *reads* the item is skipped rather than
    fed a placeholder — no `get`, no status-legality check — and the two that do
    not are run with `item=None`, which both already accept. A `when:`-condition
    correctly never matches (`Condition.matches` answers False for no item), so
    a project's conditioned `inbox` binding does not fire on nothing.

    Stream discipline is the same promise the item path makes: stdout carries
    the resolved prompt and nothing else, emitted once at the end.
    """
    st = _store()
    if st is None:
        return 1
    policy = st.lifecycle_policy()
    if not args.no_exec:
        checks = select(policy.stage_checks(step.id), None)
        err = run_bindings(checks, st.node_root,
                           hook_env(st.node_root, "", "", step.id),
                           policy.timeout, f"{step.id} pre")
        if err:
            print(f"tcw work stage: {err}; nothing resolved", file=sys.stderr)
            return 1
    try:
        res = resolve_prompts(policy, step.id, None, st.node_root,
                              load_builtins(), env=dict(os.environ),
                              execute=not args.no_exec,
                              documentation=st.documentation())
    except ResolveError as e:
        print(f"tcw work stage: {e}", file=sys.stderr)
        return 1

    if args.no_exec:
        print(f"tcw work stage {step.id}: --no-exec, nothing was executed",
              file=sys.stderr)
        for b in select(policy.stage_checks(step.id), None):
            print(f"  pre check would run: {b.ref}", file=sys.stderr)
        for entry in res.plan:
            state = "matched" if entry.matched else "skipped (condition)"
            detail = f": {entry.ref}" if entry.kind != "builtin" else ""
            print(f"  prompt {entry.kind} — {state}{detail}", file=sys.stderr)

    if res.text:
        print(res.text)
    return 0


def _stage(args: argparse.Namespace) -> int:
    """`tcw work stage <id> [ref]` — what to do at a lifecycle stage.

    Order matters and is the contract: id → item → legality → checks → resolve →
    print. Legality is decided **before any hook runs** — not before any read,
    which is impossible, since the item's status is the thing being judged.

    stdout carries the resolved prompt and nothing else, emitted once at the end
    after everything that could fail has succeeded. An agent piping this gets
    either the whole instruction or nothing, never a fragment.
    """
    step = LIFECYCLE_STEPS_BY_ID.get(args.stage_id)
    if step is None or step.kind != "stage":
        legal = [s.id for s in LIFECYCLE_STEPS if s.kind == "stage"]
        print(f"tcw work stage: unknown stage '{args.stage_id}'; expected one of "
              f"{', '.join(legal)}", file=sys.stderr)
        return 1

    # `inbox` runs before an item exists, so it resolves against the node alone.
    # Branching on the **stage id**, never on `STAGE_STATUSES[step.id]` being
    # empty: that emptiness says "no work-item status applies", which is a true
    # statement about this stage and not a licence to read it as "any status".
    if step.id == "inbox":
        if args.slug is not None:
            print(f"tcw work stage: '{step.id}' runs before an item exists and "
                  f"takes no work item; run it with no argument",
                  file=sys.stderr)
            return 1
        return _stage_without_item(args, step)
    if args.slug is None:
        print(f"tcw work stage: '{step.id}' needs a work item; "
              f"run `tcw work stage {step.id} <slug>`", file=sys.stderr)
        return 1

    resolved = _resolve(args.slug, "stage")
    if resolved is None:
        return 1
    st, bare = resolved
    try:
        item = st.get(bare)
    except MultipleMatch as e:
        print(f"tcw work stage: {e}", file=sys.stderr)
        return 1
    if item is None:
        print(f"tcw work stage: no such work item: {args.slug}", file=sys.stderr)
        return 1

    legal = STAGE_STATUSES[step.id]
    if item.status not in legal:
        print(f"tcw work stage: '{step.id}' is not legal for an item in "
              f"'{item.status}'; it runs in {', '.join(legal)}", file=sys.stderr)
        return 1

    policy = st.lifecycle_policy()
    if not args.no_exec:
        checks = select(policy.stage_checks(step.id), item)
        err = run_bindings(checks, st.node_root,
                           hook_env(st.node_root, bare, item.status, step.id),
                           policy.timeout, f"{step.id} pre")
        if err:
            print(f"tcw work stage: {err}; nothing resolved", file=sys.stderr)
            return 1

    try:
        res = resolve_prompts(policy, step.id, item, st.node_root,
                              load_builtins(),
                              artifacts=st.artifacts(bare), env=dict(os.environ),
                              execute=not args.no_exec,
                              documentation=st.documentation())
    except ResolveError as e:
        print(f"tcw work stage: {e}", file=sys.stderr)
        return 1

    if args.no_exec:
        # The plan is a diagnostic, so it goes to stderr: a caller piping stdout
        # should get the (partial) prompt, never a plan they might act on.
        print(f"tcw work stage {step.id}: --no-exec, nothing was executed",
              file=sys.stderr)
        for b in select(policy.stage_checks(step.id), item):
            print(f"  pre check would run: {b.ref}", file=sys.stderr)
        for entry in res.plan:
            state = "matched" if entry.matched else "skipped (condition)"
            detail = f": {entry.ref}" if entry.kind != "builtin" else ""
            print(f"  prompt {entry.kind} — {state}{detail}", file=sys.stderr)

    if res.text:
        print(res.text)
    return 0


# Which stage writes each artifact, inverted from the one table that says so.
# `intake` is absent on purpose: no stage produces it, so it has no legality row
# and scaffolding it is legal wherever the item is.
_STAGE_FOR_ARTIFACT = {name: step.id for step in LIFECYCLE_STEPS
                       for name in step.produces}


def _scaffold(args: argparse.Namespace) -> int:
    """Write a starting point for a lifecycle document — never the document.

    The draft is a resource of its own, named for its artifact and reported by
    nothing as one, so `tcw work list` still shows the stage as unwritten until
    someone writes it. The store owns that naming; this verb composes no path.

    **Resolve fully, then write.** A hook failure leaves nothing behind and a
    retry is clean; a write failure puts nothing on stdout, so a caller reading
    stdout for a path never gets one for a file that does not exist.
    """
    if args.artifact not in WORK_ARTIFACTS:
        print(f"tcw work scaffold: unknown artifact '{args.artifact}'; expected "
              f"one of {', '.join(WORK_ARTIFACTS)}", file=sys.stderr)
        return 1

    resolved = _resolve(args.slug, "scaffold")
    if resolved is None:
        return 1
    st, bare = resolved
    try:
        item = st.get(bare)
    except MultipleMatch as e:
        print(f"tcw work scaffold: {e}", file=sys.stderr)
        return 1
    if item is None:
        print(f"tcw work scaffold: no such work item: {args.slug}", file=sys.stderr)
        return 1

    # The canonical presence rule, through `artifacts()` — the same answer the
    # board gives. A whitespace-only `spec.md` reads as absent there, so it must
    # read as absent here too, or the two disagree about what exists.
    artifacts = st.artifacts(bare)
    if any(a.name == args.artifact and a.present for a in artifacts):
        print(f"tcw work scaffold: {args.artifact} is already written "
              f"({st.artifact_locator(bare, args.artifact)}); a draft beside it "
              f"would only compete with it", file=sys.stderr)
        return 1

    stage = _STAGE_FOR_ARTIFACT.get(args.artifact)
    if stage is not None and item.status not in STAGE_STATUSES[stage]:
        print(f"tcw work scaffold: '{args.artifact}' is written by the "
              f"'{stage}' stage, which is not legal for an item in "
              f"'{item.status}'; it runs in "
              f"{', '.join(STAGE_STATUSES[stage])}", file=sys.stderr)
        return 1

    policy = st.lifecycle_policy()
    builtins = load_builtins()
    try:
        res = resolve_artifact(policy, args.artifact, item, st.node_root,
                               builtins, artifacts=artifacts,
                               env=dict(os.environ))
    except ResolveError as e:
        print(f"tcw work scaffold: {e}; nothing written", file=sys.stderr)
        return 1

    # `resolve_artifact` has no implicit fallback: a project that declares no
    # binding gets an empty `Resolution`, which is every project today. The
    # built-in is the fallback when *nothing won* — a binding that won and
    # resolved to empty text asked for an empty template and keeps it.
    text = (res.text if any(e.matched for e in res.plan)
            else builtins.artifact_templates.get(args.artifact, ""))

    try:
        locator = st.write_draft(bare, args.artifact, text, force=args.force)
    except (*_ERRORS, OSError) as e:
        print(f"tcw work scaffold: {e}", file=sys.stderr)
        return 1
    print(locator)
    return 0


def _docs(args: argparse.Namespace) -> int:
    """`tcw work docs` — the node's documentation entries, read-only.

    Exists because the documentation gate runs at **three** points and only two
    are stages: `plan`, the end of `implement`, and the version offer *after*
    `complete`. The third has no stage to hang off — `tcw work stage implement`
    on a completed item is refused by the status check, correctly — so it needs a
    verb of its own.

    `source` is what lets a caller branch without guessing: `agent-guide` means
    the node configured nothing and the old behavior applies unchanged.
    """
    st = _store()
    if st is None:
        return 1
    entries = st.documentation()
    source = "config" if entries else "agent-guide"

    if args.json:
        print(json.dumps({"schema": 1, "source": source,
                          "entries": [{"path": e.path, "trigger": e.trigger,
                                       "description": e.description}
                                      for e in entries]}, indent=2))
        return 0

    if not entries:
        # stdout stays empty: there is nothing to list, and a caller piping this
        # should get no rows rather than a sentence pretending to be one.
        print("tcw work docs: this node declares no `work.documentation`; "
              "documentation entries come from the project's agent guide "
              "(`AGENTS.md` or `CLAUDE.md`).", file=sys.stderr)
        return 0

    width = max(len(e.path) for e in entries)
    trigger_width = max(len(e.trigger) for e in entries) + 2
    for e in entries:
        description = " ".join(e.description.split())
        print(f"{e.path:<{width}}  {'[' + e.trigger + ']':<{trigger_width}}  "
              f"{description}")
    return 0


def _lifecycle(args: argparse.Namespace) -> int:
    # A work ref resolves the item's *owning* node, so a qualified descendant
    # reports its own policy rather than the anchor's.
    if args.slug:
        resolved = _resolve(args.slug, "lifecycle")
        if resolved is None:
            return 1
        st, _bare = resolved
    else:
        st = _store()
        if st is None:
            return 1
    try:
        policy = st.lifecycle_policy()
    except _ERRORS as e:
        print(f"tcw work lifecycle: {e}", file=sys.stderr)
        return 1

    # `--phase` filters what is reported. Legal phases differ by kind: a stage has
    # `pre` checks and `prompt` bindings and no `post` at all (exit checks live on
    # the next stage's `pre`), while a transition has `pre` and `post`. An illegal
    # combination is an error naming the reason rather than empty output, because
    # silence reads as "nothing is configured".
    phase = getattr(args, "phase", None)
    if phase:
        wanted_kind = "stage" if args.stage else "transition" if args.transition else None
        legal = {"stage": ("pre", "prompt"), "transition": ("pre", "post")}
        if wanted_kind is None:
            print("tcw work lifecycle: --phase needs --stage or --transition",
                  file=sys.stderr)
            return 1
        if phase not in legal[wanted_kind]:
            reason = ("stages have no 'post' phase — a stage's exit checks belong "
                      "on the next stage's 'pre'"
                      if wanted_kind == "stage" and phase == "post" else
                      f"transitions have no '{phase}' phase")
            print(f"tcw work lifecycle: --phase {phase} is not valid for a "
                  f"{wanted_kind}: {reason}; expected one of "
                  f"{', '.join(legal[wanted_kind])}", file=sys.stderr)
            return 1

    def bindings_for(step):
        if step.kind == "stage":
            # "bind:" keeps its exact meaning — the stage's prompts. Stage
            # bindings were never executed, so what they always were is what
            # `prompt` names; the label stays so legacy output does not move.
            rows = [("bind:", policy.stage(step.id))]
            checks = policy.stage_checks(step.id)
            if checks:                        # new key, absent from legacy output
                rows.insert(0, ("pre:", checks))
        else:
            tb = policy.transition(step.id)
            rows = [("pre:", tb.pre), ("post:", tb.post)]
        if not phase:
            return rows
        want = "bind:" if (step.kind == "stage" and phase == "prompt") else f"{phase}:"
        return [(label, bs) for label, bs in rows if label == want]

    if args.directive:
        # Exactly one of --stage/--transition, enforced by argparse; an unknown
        # id is an *error*, not an empty directive, so a typo in an injected
        # command never renders as silence.
        wanted = args.stage or args.transition
        step = LIFECYCLE_STEPS_BY_ID.get(wanted)
        kind = "stage" if args.stage else "transition"
        if step is None or step.kind != kind:
            legal = [s.id for s in LIFECYCLE_STEPS if s.kind == kind]
            print(f"tcw work lifecycle: unknown {kind} '{wanted}'; expected one "
                  f"of {', '.join(legal)}", file=sys.stderr)
            return 1
        flat = [b for _label, bs in bindings_for(step) for b in bs]
        grouped = step.kind != "stage" or policy.stage_is_legacy(step.id)
        text = _directive_text(step, flat, grouped)
        if text:                                   # empty = print nothing at all
            print(text)
        return 0

    steps = [s for s in LIFECYCLE_STEPS
             if not args.stage and not args.transition
             or (args.stage and s.id == args.stage and s.kind == "stage")
             or (args.transition and s.id == args.transition and s.kind == "transition")]
    if not steps:
        print(f"tcw work lifecycle: unknown id "
              f"'{args.stage or args.transition}'", file=sys.stderr)
        return 1

    if args.json:
        payload = [{
            "id": s.id, "kind": s.kind, "objective": s.objective,
            "moves": s.moves, "inputs": list(s.inputs),
            "produces": s.produces_note, "gates": list(s.gates),
            "bindings": {label.rstrip(":"): [_binding_json(b) for b in bs]
                         for label, bs in bindings_for(s)},
        } for s in steps]
        # A superset, the same discipline the JSON projection applied to `serve`:
        # every key a legacy config produced is still here with the same value,
        # and the new ones appear only when the feature is configured — so a
        # legacy node's payload is byte-identical.
        doc = {"timeout": policy.timeout, "steps": payload}
        if policy.output_cap != DEFAULT_OUTPUT_CAP:
            doc["output-cap"] = policy.output_cap
        if policy.artifacts:
            doc["artifacts"] = {name: [_binding_json(b) for b in bs]
                                for name, bs in policy.artifacts.items()}
        print(json.dumps(doc, indent=2))
        return 0

    for i, step in enumerate(steps):
        if i:
            print()
        print("\n".join(_lifecycle_lines(step, bindings_for)))
    return 0


def _edit(args: argparse.Namespace) -> int:
    resolved = _resolve(args.slug, "edit")
    if resolved is None:
        return 1
    st, bare = resolved                           # blocker refs are node-local to `st`
    try:
        current = st.get(bare)
        if current is None:
            print(f"tcw work edit: no such work item: {args.slug}", file=sys.stderr)
            return 1
        # Recompute the tag set only when --tag/--untag were given (else _UNSET).
        tags_kw = _UNSET
        if args.tag or args.untag:
            untag = set(args.untag or [])
            final = [t for t in current.tags if t not in untag]
            for t in (args.tag or []):
                if t not in final:
                    final.append(t)
            tags_kw = final
        blocks = _split(args.blocks)
        for ref in blocks:
            if st.get(ref) is None:
                print(f"tcw work edit: no such work item: {ref}", file=sys.stderr)
                return 1
        # Removals first: they fail closed, so a bad --unblocked-by ref aborts
        # before any --blocked-by/--blocks write lands (same spirit as the
        # up-front --blocks validation above).
        for ref in (args.unblocked_by or []):
            st.remove_blocker(bare, ref)
        for ref in (args.blocked_by or []):
            st.add_blocker(bare, ref)
        for ref in blocks:
            st.add_blocker(ref, bare)             # reverse link: bare into ref's blocked_by
        # Use composite update for field changes
        st.update_work(
            bare,
            title=_provided(args.title),
            initiative=_provided(args.initiative),
            priority=_provided(args.priority),
            effort=_provided(args.effort),
            complexity=_provided(args.complexity),
            tags=tags_kw,
        )
    except _ERRORS as e:
        print(f"tcw work edit: {e}", file=sys.stderr)
        return 1
    print(f"edited {args.slug}")
    return 0


def _tags_list(args: argparse.Namespace) -> int:
    st = _store()
    if st is None:
        return 1
    for tag in st.registered_tags():
        print(tag)
    return 0


def _tags_add(args: argparse.Namespace) -> int:
    st = _store()
    if st is None:
        return 1
    try:
        result = st.register_tags(args.tag)
    except _ERRORS as e:
        print(f"tcw work tags add: {e}", file=sys.stderr)
        return 1
    for tag in result:
        print(tag)
    return 0


def _tombstone_add(args: argparse.Namespace) -> int:
    st = _store()
    if st is None:
        return 1
    try:
        ts = st.record_tombstone(args.slug, args.resolution or "",
                                 args.resolved or "")
    except _ERRORS as e:
        print(f"tcw work tombstone add: {e}", file=sys.stderr)
        return 1
    print(f"recorded {ts.slug}"
          + (f" ({ts.resolution})" if ts.resolution else "")
          + f", resolved {ts.resolved}")
    return 0


def _tags_rm(args: argparse.Namespace) -> int:
    st = _store()
    if st is None:
        return 1
    try:
        result = st.unregister_tags(args.tag)
    except _ERRORS as e:
        print(f"tcw work tags rm: {e}", file=sys.stderr)
        return 1
    for problem in st.check():                     # warn about now-stale item tags
        print(f"warning: {problem}", file=sys.stderr)
    for tag in result:
        print(tag)
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
    # Refuse a completion run from inside the item's *own* worktree. Left alone
    # it exits 0 having done nothing: `merge_worktree` merges the work branch
    # into itself, and `remove_worktree` looks for `<worktree>/.worktrees/<slug>`,
    # misses, and swallows the miss as "already absent" — so the command claims a
    # completion that did not happen. Refusing is the whole fix: `git worktree
    # remove` deletes the worktree you are standing in, so completing from inside
    # is not a flow worth engineering. Completing from an *unrelated* worktree is
    # not this defect, hence the equality against this item's own path.
    if has_worktree and (anchors := worktree_anchors(st.node_root)):
        top, main = anchors
        own = (main / st.node_root.resolve().relative_to(top) / item.worktree).resolve()
        if top == own:
            print(f"tcw work complete: {args.slug} cannot be completed from inside its "
                  f"own worktree — the merge-back and teardown act on the primary "
                  f"checkout. Re-run from {main}.", file=sys.stderr)
            return 1
    # `[prompted]`: an obligation on the CLI to say something, not a gate and not
    # an interactive prompt. Completing straight from `active` skips the verify
    # stage, which is legal and often right for a small change — the point is
    # that it not happen without anyone noticing. Read before the transition;
    # afterwards the status is terminal and the branch is unreachable.
    if item.status == "active":
        print(f"tcw work complete: completing {args.slug} directly from active; "
              f"the verify stage was skipped", file=sys.stderr)
    # A discard is not a shipment: the blocker check, the Definition-of-Done
    # checklist, the capability gate, and the worktree merge-back all exist to
    # police shipped work, so none of them apply. `--confirm` still does —
    # closing is terminal.
    shipping = resolution_status(args.resolution) == "completed"
    # The binding keys on the **move**, not the verb: `complete --resolution done`
    # fires `complete`'s hooks and any other resolution fires `discard`'s. One
    # binding firing for both "we shipped it" and "we gave up on it" would erase
    # exactly the distinction `discard` exists to preserve.
    transition_id = "complete" if shipping else "discard"
    policy = st.lifecycle_policy()
    if shipping and not args.force:
        blockers = st.unresolved_blockers(item)
        if blockers:
            print(f"tcw work complete: blocked by: {', '.join(blockers)} "
                  f"(use --force to override)", file=sys.stderr)
            return 1
    checklist = st.dod_checklist() if shipping else []
    if shipping:
        print("Definition of Done — acknowledge each item:")
        for c in checklist:
            print(f"  [ ] {c}")
        if not args.confirm:
            print("Refused: re-run with --confirm once the checklist is satisfied.",
                  file=sys.stderr)
            return 1
    elif not args.confirm:
        print(f"Refused: discarding {args.slug} as '{args.resolution}' is "
              f"permanent. Re-run with --confirm.", file=sys.stderr)
        return 1
    if args.already_integrated and not has_worktree:
        # Accepting it silently would teach the wrong model: the flag exists to
        # skip a merge-back that only a TCW-created worktree ever performs.
        print(f"tcw work complete: --already-integrated applies to an item started "
              f"with --worktree; {args.slug} has none.", file=sys.stderr)
        return 1
    if shipping and has_worktree and branch and not args.already_integrated:
        err = merge_worktree(st.node_root, branch)
        if err:
            print(f"tcw work complete: {err}", file=sys.stderr)
            return 1
        item = st.get(bare)                           # re-read: the sidecar's declared
                                                      # list may have changed on the branch
    # Capabilities gate — after merge-back so both the declared list and the
    # capability statuses are read from the merged primary tree. On a discard it
    # degrades to a warning: blocking abandonment on reconciliation would put
    # friction on the very path this exists to smooth.
    if not args.force:
        problems = capability_gate(st, item)
        if problems and shipping:
            print("tcw work complete: declared capabilities not reconciled:",
                  file=sys.stderr)
            for p in problems:
                print(f"  - {p}", file=sys.stderr)
            print("Reconcile them (tcw capabilities set <path> --status <S>) "
                  "or re-run with --force.", file=sys.stderr)
            return 1
        for p in problems:
            print(f"warning: unreconciled capability: {p}", file=sys.stderr)
        if problems:
            print("Mark them Omitted (tcw capabilities set <path> --status Omitted) "
                  "if they will never be built.", file=sys.stderr)
    # Last thing before the store is touched. A `pre` hook may refuse the
    # completion, and a refusal has to mean the item is untouched — so the hook
    # runs before `complete()` is entered at all, not somewhere inside it.
    if (err := run_pre(policy, transition_id, st.node_root, bare, item.status,
                       item)):
        print(f"tcw work complete: {err}; {bare} not closed", file=sys.stderr)
        return 1
    try:
        st.complete(bare, args.resolution, dod_ack=checklist, force=args.force)
    except _ERRORS as e:
        print(f"tcw work complete: {e}", file=sys.stderr)
        return 1
    post_err = run_post(policy, transition_id, st.node_root, bare,
                        "completed" if shipping else "discarded", item)
    loc = st.locate(bare)
    print(f"{'completed' if shipping else 'discarded'} {args.slug} "
          f"({args.resolution})" + (f" → {loc}" if loc else ""))
    if has_worktree:
        if not shipping and branch and not args.already_integrated:
            # The branch is deliberately kept: a discard decides the work isn't
            # wanted, which is not authority to destroy an unmerged branch.
            # Suppressed under --already-integrated, where the branch *was*
            # merged — just not by TCW.
            print(f"tcw work complete: work branch '{branch}' was not merged and "
                  f"is left intact; delete it with "
                  f"`git branch -D {branch}` if you're sure.", file=sys.stderr)
        for w in remove_worktree(st.node_root, bare, branch if shipping else None):
            print(f"tcw work complete: {w}", file=sys.stderr)
    return _post_result(post_err, transition_id, args.slug)


def _drop(args: argparse.Namespace) -> int:
    resolved = _resolve(args.slug, "drop")
    if resolved is None:
        return 1
    st, bare = resolved
    # `drop` is the only destructive verb with no record behind it — `complete`
    # preserves the item, `discard` preserves the item. Gate it the way `complete`
    # gates a discard, and name what goes so the refusal is informative.
    if not args.confirm:
        loc = st.locate(bare)
        # Resolve existence BEFORE gating: advising `--confirm` on an item that
        # does not exist sends the user to a second, different error.
        if loc is None:
            print(f"tcw work drop: no such work item: {args.slug}", file=sys.stderr)
            return 1
        # Both lines on stderr: nothing succeeded, and splitting a refusal across
        # two streams lets a terminal interleave them out of order.
        print(f"Refused: dropping {args.slug} erases it outright and leaves no "
              f"record. Re-run with --confirm.", file=sys.stderr)
        print(f"Would delete {args.slug} ({loc})", file=sys.stderr)
        return 1
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

    pi = g.add_parser("init", help="create raw inbox plus backlog/active/completed/discarded work storage")
    pi.add_argument("--id", help="canonical project ID (required for new/legacy nodes)")
    pi.add_argument("--path", help="filesystem location for the work store")
    pi.set_defaults(func=_init)

    pin = g.add_parser("inbox", help="inspect and accept raw work intake")
    ing = pin.add_subparsers(dest="inbox_cmd", required=True)
    ing.add_parser("list", help="list raw inbox entries").set_defaults(func=_inbox_list)
    ing.add_parser("path", help="print the work inbox folder path").set_defaults(
        func=_inbox_path)
    pins = ing.add_parser("show", help="show one raw inbox entry")
    pins.add_argument("entry")
    pins.set_defaults(func=_inbox_show)
    pina = ing.add_parser("accept", help="accept one raw entry into backlog")
    pina.add_argument("entry")
    pina.add_argument("--title", help="override the derived work-item title")
    pina.set_defaults(func=_inbox_accept)

    g.add_parser("nodes", help="list this node's parent + child nodes").set_defaults(func=_nodes)

    pr = g.add_parser("reconcile", help="scan child nodes → write the epic rollup")
    pr.add_argument("slug")
    pr.add_argument("--commit", action="store_true", help="also commit the rollup")
    pr.add_argument("--complete-when-ready", action="store_true",
                    help="auto-complete the epic if all its children are resolved")
    pr.set_defaults(func=_reconcile)

    pdg = g.add_parser("delegate", help="write a request into a child node's inbox/")
    pdg.add_argument("child", help="child node's canonical project id (`tcw work nodes` lists them)")
    pdg.add_argument("title")
    pdg.add_argument("--initiative", help="stamp the request with an initiative slug")
    pdg.set_defaults(func=_delegate)

    pes = g.add_parser("escalate", help="write a request into the parent node's inbox/")
    pes.add_argument("title")
    pes.add_argument("--initiative", help="stamp the request with an initiative slug")
    pes.set_defaults(func=_escalate)

    ptg = g.add_parser("tags", help="manage this node's registered tag set")
    ptgs = ptg.add_subparsers(dest="tags_cmd", required=True)
    ptgs.add_parser("list", help="print the registered tags").set_defaults(func=_tags_list)
    ptga = ptgs.add_parser("add", help="register one or more tags")
    ptga.add_argument("tag", nargs="+", help="tag(s) to register")
    ptga.set_defaults(func=_tags_add)
    ptgr = ptgs.add_parser("rm", help="unregister one or more tags")
    ptgr.add_argument("tag", nargs="+", help="tag(s) to unregister")
    ptgr.set_defaults(func=_tags_rm)

    pts = g.add_parser(
        "tombstone",
        help="records of items this store resolved before it kept any")
    ptss = pts.add_subparsers(dest="tombstone_cmd", required=True)
    ptsa = ptss.add_parser(
        "add",
        help="record that a slug was a work item here, so references to it resolve")
    ptsa.add_argument("slug")
    ptsa.add_argument("--resolution",
                      help="done|wontfix|duplicate|superseded; omit if unknown")
    ptsa.add_argument("--resolved", help="ISO date it was resolved (default: today)")
    ptsa.set_defaults(func=_tombstone_add)

    pn = g.add_parser("new", help="create a backlog item; prints its slug")
    pn.add_argument("title")
    pn.add_argument("--priority", type=int, help="integer priority (higher = higher)")
    pn.add_argument("--effort", type=_work_level,
                    help="estimated effort: low|medium|high|very-high (or L/M/H/VH)")
    pn.add_argument("--complexity", type=_work_level,
                    help="estimated complexity: low|medium|high|very-high (or L/M/H/VH)")
    pn.add_argument("--blocked-by", action="append",
                    help="a slug or external text that blocks it (repeatable)")
    pn.add_argument("--tag", action="append", type=_tag,
                    help="apply a registered tag (repeatable)")
    pn.add_argument("--epic", action="store_true", help="mark as an epic (type: epic)")
    pn.add_argument("--parent", help="create as a child nested under this item's slug")
    pn.add_argument("--initiative", help="back-pointer slug to an owning epic")
    pn.set_defaults(func=_new)

    pl = g.add_parser("list", help="the board (hides completed + discarded unless --status/--all)")
    pl.add_argument("--status", choices=WORK_STATUSES)
    pl.add_argument("--tag", action="append", type=_tag,
                    help="only items carrying this tag (repeatable = match any)")
    pl.add_argument("--all", action="store_true", help="include completed and discarded items")
    pl.add_argument("-i", "--incl-desc", "--include-descendants",
                    dest="include_descendants", action="store_true",
                    help="also list every descendant work node's board, grouped by node")
    pl.set_defaults(func=_list)

    psh = g.add_parser("show", help="resolve slug → item; print state + body")
    psh.add_argument("slug")
    psh.add_argument("--json", action="store_true",
                     help="emit the item as a versioned JSON document")
    psh.set_defaults(func=_show)

    pp = g.add_parser("path", help="print the work store or a work item folder path")
    pp.add_argument("slug", nargs="?")
    pp.set_defaults(func=_path)

    pst = g.add_parser("start", help="backlog → active")
    pst.add_argument("slug")
    pst.add_argument("--force", action="store_true", help="start despite unresolved blockers")
    pst.add_argument("--owner", help="claimant identity (then TCW_WORK_OWNER, Git email/name)")
    pst.add_argument("--take-over", action="store_true", help="replace an existing active claim")
    pst.add_argument("--worktree", action="store_true",
                     help="isolate the item in its own git worktree + branch")
    pst.set_defaults(func=_start)

    psb = g.add_parser("submit", help="active → review (implemented, acceptance pending)")
    psb.add_argument("slug")
    psb.set_defaults(func=_submit)

    prw = g.add_parser("rework", help="review → active (verification rejected the work)")
    prw.add_argument("slug")
    prw.set_defaults(func=_rework)

    plc = g.add_parser("lifecycle",
                       help="print the stage/transition contract and configured bindings")
    plc.add_argument("slug", nargs="?",
                     help="report the owning node's policy for this item (default: local node)")
    plc.add_argument("--json", action="store_true", help="machine-readable output")
    plc.add_argument("--directive", action="store_true",
                     help="emit one instruction line for an agent, or nothing when unbound")
    pdoc = g.add_parser("docs",
                        help="print the node's documentation entries")
    pdoc.add_argument("--json", action="store_true", help="machine-readable output")
    pdoc.set_defaults(func=_docs)
    pstg = g.add_parser("stage",
                        help="print a stage's instructions after its checks pass")
    pstg.add_argument("stage_id", metavar="stage")
    # Optional here and required in the handler: argparse cannot express
    # "required for six values of another positional, refused for the seventh".
    pstg.add_argument("slug", nargs="?",
                      help="the work item; omitted for `inbox`, which runs "
                           "before an item exists")
    pstg.add_argument("--no-exec", action="store_true",
                      help="report what would run and run none of it")
    pstg.set_defaults(func=_stage)

    pscf = g.add_parser("scaffold",
                        help="write a draft of a lifecycle artifact from its template")
    pscf.add_argument("artifact", help=f"one of: {', '.join(WORK_ARTIFACTS)}")
    pscf.add_argument("slug")
    pscf.add_argument("--force", action="store_true",
                      help="replace a draft that is already there")
    pscf.set_defaults(func=_scaffold)

    plc.add_argument("--phase", choices=("pre", "post", "prompt"),
                     help="limit to one phase; a stage has 'pre' and 'prompt', "
                          "a transition has 'pre' and 'post'")
    sel = plc.add_mutually_exclusive_group()
    sel.add_argument("--stage", help="limit to one stage id")
    sel.add_argument("--transition", help="limit to one transition id")
    plc.set_defaults(func=_lifecycle)

    pe = g.add_parser("edit", help="change an item's title, estimates, tags, or blocking links")
    pe.add_argument("slug")
    pe.add_argument("--title", type=_nonempty, help="set the item title (the slug is unchanged)")
    pe.add_argument("--blocked-by", action="append",
                    help="a slug or external text that blocks this item (repeatable)")
    pe.add_argument("--blocks", help="comma-separated items this item blocks")
    pe.add_argument("--unblocked-by", action="append",
                    help="a blocker to remove (repeatable; accepts the "
                         "'external: …' form shown by show/list)")
    pe.add_argument("--priority", type=int, help="set integer priority (higher = higher)")
    pe.add_argument("--effort", type=_work_level,
                    help="set estimated effort: low|medium|high|very-high (or L/M/H/VH)")
    pe.add_argument("--complexity", type=_work_level,
                    help="set estimated complexity: low|medium|high|very-high (or L/M/H/VH)")
    pe.add_argument("--initiative", help='set the owning-epic back-pointer (use "" to clear)')
    pe.add_argument("--tag", action="append", type=_tag, help="apply a registered tag (repeatable)")
    pe.add_argument("--untag", action="append", type=_tag, help="remove a tag (repeatable)")
    pe.set_defaults(func=_edit)

    pc = g.add_parser("complete", help="close an item: --resolution done → completed (DoD gate), anything else → discarded")
    pc.add_argument("slug")
    pc.add_argument("--resolution", required=True, choices=sorted(WORK_RESOLUTIONS))
    pc.add_argument("--confirm", action="store_true")
    pc.add_argument("--force", action="store_true", help="complete despite unresolved blockers")
    pc.add_argument("--already-integrated", action="store_true",
                    help="the work branch was merged outside TCW (e.g. a merged PR): "
                         "skip the merge-back, keep every other gate")
    pc.set_defaults(func=_complete)

    pd = g.add_parser("drop", help="backlog → deleted")
    pd.add_argument("slug")
    pd.add_argument("--confirm", action="store_true")
    pd.set_defaults(func=_drop)
