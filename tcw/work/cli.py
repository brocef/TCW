"""`tcw work` — the changes. Single-node state machine per phase-5-work B.2."""

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

from tcw.store.base import (
    DEFAULT_OUTPUT_CAP, RESOLVED_STATUSES, STAGE_IDS, STAGE_STATUSES, WORK_ARTIFACTS,
    WORK_RESOLUTIONS, WORK_STATUSES, _UNSET,
    IllegalTransition, LIFECYCLE_STEPS, LIFECYCLE_STEPS_BY_ID, MultipleMatch,
    StoreNotProvisioned, TransitionCommitError, WorkItem,
    normalize_tag, AlreadyClaimed,
    normalize_work_level, resolution_status, StaleRevision,
)
from tcw.store.fs import (
    COMPONENTS, NOT_A_REPOSITORY, WORKTREES_DIR, FsWorkStore, add_worktree,
    child_nodes, descendant_nodes, ensure_worktree_ignored, find_node,
    declared_repository, git_commit_result, git_root, merge_worktree,
    nearest_work_ancestor,
    parent_node, registered_children, registered_parent,
    unreachable_children, unreachable_parent,
    qualified_work_ref_problem, registered_project_id, remove_worktree,
    resolve_qualified_work_ref,
)
from tcw.stdin import read_piped_stdin
from tcw.store.project import worktree_anchors
from tcw.work.hooks import hook_env, run_bindings, run_post, run_pre
from tcw.work.projection import work_item_json
from tcw.work.resolve import (
    ResolveError, bookend, load_builtins, resolve_artifact, resolve_prompts,
    select,
)
from tcw.work.recursion import capability_gate, delegate, escalate, reconcile

NAME = "work"
SUBCOMMANDS = {"init", "inbox", "new", "list", "show", "path", "start", "submit",
               "rework", "edit", "complete", "drop", "delete", "nodes", "reconcile",
               "delegate",
               "escalate", "tags", "lifecycle", "stage", "scaffold", "docs",
               "tracker"}
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


def _tag_list(value: str) -> list[str]:
    """One tag value is a comma-separated *list*, normalized to canonical slugs.

    A comma can never occur inside a tag — ``normalize_tag`` admits only
    ``[a-z0-9-]`` — so reading it as a separator costs nothing and closes the
    hole where ``--tag cli,docs`` silently became the single tag ``cli-docs``.
    Blank segments are ignored, matching ``_split``; a value that yields no tag
    at all is refused, so a typo cannot quietly apply nothing.

    Raises ``ValueError``, which is what the command handlers already catch.
    """
    tags = [normalize_tag(t) for t in _split(value)]
    if not tags:
        # Distinct wording from ``normalize_tag``'s own empty-tag message, which
        # this can otherwise be confused with: that one fires when a *token*
        # normalizes away, this one when the value holds no token at all.
        raise ValueError(f"invalid tag {value!r}: names no tag")
    return tags


def _tags(value: str) -> list[str]:
    """argparse ``type=`` for every option that takes a tag. Only the exception
    type differs from ``_tag_list``: argparse reports its own, and a handler
    catching ``ValueError`` would not see it."""
    try:
        return _tag_list(value)
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


def _tracker_text(value: dict, *, row: bool) -> str:
    """A binding as `show` prints it, or as a board row's `ticket:` segment.

    From `WorkItem.tracker` alone, so reading a binding needs no tracker configured
    and loads no tracker code. A row stays one short line: the default part and the
    reason a binding cannot be read are left to `show`.
    """
    if "problem" in value:
        return "unreadable" if row else f"tracker.yaml cannot be read ({value['problem']})"
    key, part = value["ticket"]["key"], value["part"]
    if row:
        sync = value.get("sync")
        notes = [f"part {part}"] if part != "default" else []
        if sync:
            notes.append("unreadable sync record" if "problem" in sync else sync["state"])
        return f"{key} ({', '.join(notes)})" if notes else key
    url = value["ticket"]["url"]
    return f"{key} ({value['provider']}, part {part})" + (f" {url}" if url else "")


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
    if item.tracker is not None:
        print(f"tracker: {_tracker_text(item.tracker, row=False)}")
        sync = item.tracker.get("sync")
        if sync and "problem" in sync:
            print(f"tracker sync: record cannot be read ({sync['problem']})")
        elif sync:
            owed = "; the claim is still owed" if sync["claim"] == "owed" else ""
            print(f"tracker sync: {sync['state']} after {sync['move']} ({sync['at']}): "
                  f"{sync['reason']}{owed}")
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
    if parent is not None:
        print(f"parent: {registered_project_id(node, parent)}")
    else:
        # A registered parent that keeps no board is not the top of the graph,
        # and printing "(none — root)" for it hid a whole node from the reader.
        registered = registered_parent(node)
        if registered is not None:
            print(f"parent: {registered_project_id(node, registered)}"
                  f"{_no_store_note(registered)}")
        elif (absent := unreachable_parent(node)) is not None:
            # Declared, and not here. `registered_parent` cannot report it — it
            # answers with a path, and a project this checkout does not have has
            # none — so this line used to read `(none — root)` for a node whose
            # config plainly names a parent.
            print(f"parent: {absent.id}  (not in this checkout)")
        else:
            print("parent: (none — root)")
    # Every registered child, not only the ones keeping a board. A routing node
    # is still a child, and filtering it out made a node with one read as a leaf.
    # Marked the same way the parent line marks its own case, so the two halves
    # of this output describe the graph alike.
    children = registered_children(node)
    absent_children = unreachable_children(node)
    if children or absent_children:
        print("children:")
        with_store = {c.resolve() for c in child_nodes(node)}
        for c in children:
            print(f"  {registered_project_id(node, c)}"
                  f"{'' if c.resolve() in with_store else _no_store_note(c)}")
        for entry in absent_children:
            print(f"  {entry.id}  (not in this checkout)")
    else:
        print("children: (none — leaf)")
    return 0


def _no_store_note(child: Path) -> str:
    """Why a registered child keeps no usable board here.

    Two different situations that used to look identical by being omitted: a
    routing node genuinely has no board, while a declared one has a board this
    machine has not obtained — and only the second is something the reader can
    act on.
    """
    try:
        declaration, _ = declared_repository(child, "work")
    except Exception:
        declaration = None
    if declaration is not None:
        return "  (work store not provisioned here)"
    return "  (no work store)"


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


def _strict_says_no(verb: str, what: str, reason: str) -> int:
    """Print a strict-mode refusal, which always leads with what did not happen."""
    print(f"tcw work {verb}: refused under strict tracker mode; {what}. {reason}",
          file=sys.stderr)
    return 1


_STRICT_BROKEN = ("The tracker configuration has problems, and strict mode refuses "
                  "until it is fixed. Run `tcw validate`.")


def _strict_refusal(st, bare: str, change: str) -> str | None:
    """Why strict tracker mode refuses `change` (a lifecycle move) of `bare`, or
    `None`. Loads no tracker code unless the node is strict; epics are not gated."""
    if not st.tracker_strict():
        return None
    item = st.get(bare)
    if item is None or item.type == "epic":
        return None
    config = st.tracker_config()
    if config is None:
        return _STRICT_BROKEN
    value = item.tracker
    if not isinstance(value, dict) or "problem" in value:
        return (f"{bare} is not bound to a readable ticket. Link it with "
                f"`tcw work tracker link {bare} <ticket>` first.")
    from tcw.store.base import target_status
    from tcw.tracker.jira import JiraClient
    from tcw.tracker.sync import MOVE_STATUS, authorize
    target = target_status(config.statuses, MOVE_STATUS[change], None)
    return authorize(st, bare, JiraClient(config), config, target=target)


def _strict_claim(st, bare: str, item, args) -> tuple[int | None, bool]:
    """Under strict mode, claim a bound item's ticket before `start` moves it.

    Returns `(exit code of a refusal already printed, or None to go ahead, whether
    the ticket was claimed)`. The checks the store would certainly refuse run first, so a start that
    cannot happen does not take a ticket.
    """
    config = st.tracker_config()
    if config is None:
        return _strict_says_no("start", f"{bare} was not started", _STRICT_BROKEN), False
    value = item.tracker
    if not isinstance(value, dict) or "problem" in value:
        return _strict_says_no("start", f"{bare} was not started",
                               f"{bare} is not bound to a readable ticket. Link it with "
                               f"`tcw work tracker link {bare} <ticket>` first."), False
    if item.status != "backlog" and not (item.status == "active" and args.take_over):
        return None, False                # the store refuses it, and names why
    if not args.force and st.unresolved_blockers(item):
        return None, False                # likewise, before any ticket is taken
    from tcw.tracker.intake import binding_of, claim, read_ticket, same_site
    from tcw.tracker.jira import JiraClient, TrackerError
    from tcw.tracker.sync import claim_refusal
    bound, _revision = binding_of(st, bare)
    key = value["ticket"]["key"]
    if not same_site(bound.ticket_url, config.base_url):
        return _strict_says_no("start", f"{bare} was not started",
                               f"{key}'s binding is not on {config.base_url}."), False
    if value.get("sync") is not None:
        return _strict_says_no("start", f"{bare} was not started",
                               f"{key} has a change that has not reached the tracker. "
                               f"Run `tcw work tracker sync {bare}` first."), False
    client = JiraClient(config)
    try:
        outcome = claim(client, read_ticket(client, bound.ticket_id))
    except TrackerError as error:
        return _strict_says_no("start", f"{bare} was not started",
                               f"The tracker could not answer ({error}), so {key} may "
                               f"or may not have been claimed. Run it again once the "
                               f"tracker answers."), False
    if not outcome.claimed:
        detail = f" ({outcome.detail})" if outcome.detail else ""
        return _strict_says_no("start", f"{bare} was not started",
                               outcome.message + detail), False
    refusal = claim_refusal(client, config, bound.ticket_id, outcome)
    if refusal:
        return _strict_says_no("start", f"{bare} was not started", refusal), True
    return None, True


def _new(args: argparse.Namespace) -> int:
    st = _store()
    if st is None:
        return 1
    if st.tracker_strict() and not args.epic:
        return _strict_says_no("new", "nothing was created",
                               "Create work from a ticket with "
                               "`tcw work tracker import <ticket>`.")
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
    if st.tracker_strict():
        return _strict_says_no("inbox accept", f"{args.entry} was not accepted",
                               "Create work from a ticket with "
                               "`tcw work tracker import <ticket>`.")
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
    # Last, so no segment before it moves for a bound item.
    ticket = (f" | ticket: {_tracker_text(it.tracker, row=True)}"
              if it.tracker is not None else "")
    print(f"{'  ' * depth}{prefix}{it.slug} | {it.status} | {stages or '-'} | "
          f"{pri} | {it.title}{tag_seg}{ready}{suffix}{claim}{ticket}")


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
                candidate_root = nearest_work_ancestor(candidate_root)
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
        grave = st.tombstone(bare)
        if grave is not None:
            if getattr(args, "json", False):
                # There is no item document to project, and this branch sat
                # ahead of the `--json` one — so a caller piping to `jq` got the
                # human block on stdout under a success exit. Empty stdout and a
                # non-zero exit is the only answer that cannot be misread. The
                # message still names the case, so a person reading a failed
                # pipeline learns what `jq` could not be told; projecting the
                # tombstone instead would mean a second document shape under a
                # schema that is closed by construction, and `tcw serve` returns
                # the same document, so that is a contract change rather than a
                # fix. See the follow-up item.
                said = ", ".join(x for x in (grave.resolution, grave.resolved) if x)
                print(f"tcw work show: {grave.slug} was resolved"
                      + (f" ({said})" if said else "")
                      + " and removed; there is no item document to project.",
                      file=sys.stderr)
                return 1
            # The item is gone from the store but the store remembers it. Saying
            # "no such work item" here would call finished work a typo.
            print(f"{grave.slug}  (resolved)")
            if grave.resolution:
                print(f"resolution: {grave.resolution}")
            if grave.resolved:
                print(f"resolved:   {grave.resolved}")
            # Always, not only when a location was recorded. Resolved before it
            # is shown, *against this slug*, because the whole reason a locator
            # was once refused here is that a pointer must not fail silently —
            # which includes a commit this clone has and which never held the
            # item. Guarding on a non-empty location skipped the one case the
            # reader most needs told: an item whose documents were never
            # retained anywhere, which now says so instead of saying nothing.
            print(f"content:    {st.describe_location(grave.location, bare)}")
            return 0
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


def _removed(st, slug: str) -> bool:
    """Whether the store no longer holds `slug`. Never raises.

    Asked at *every* exit from `_auto_delete`, including the `pre`-failure one —
    the binding that just failed is the one thing in that function able to move
    the item, so hard-coding "still there" there reproduced exactly the symptom
    asking the store was introduced to end.

    `get()` can raise `MultipleMatch`, which is an `Exception` and not a
    `ValueError`, so a bare call escapes the CLI as a traceback and — from
    inside an `except` handler — skips the completion report and the worktree
    cleanup `_complete` still owes. Anything it cannot answer is treated as
    removed, because the consequence of this answer is whether a *location* is
    printed, and printing a path that may not exist is the failure being fixed.
    """
    try:
        return st.get(slug) is None
    except Exception:
        return True


def _auto_delete(st, slug: str, status: str, resolution: str) -> "tuple[int, bool]":
    """Run the `auto-delete` bindings around removing a resolved item.

    Ordered so the archive sees a complete, already-committed artifact and a
    failure costs nothing: the resolving commit has landed, `pre` runs while the
    item is still on disk, the removal and its commit come next, `post` last.

    A `pre` failure leaves the item wherever the binding left it — usually
    exactly where it was, and sometimes moved, since relocating the item is a
    supported thing for an archive command to do. Either way the state is
    finishable, and the message says which one it is, because the user's first
    question is whether their work is safe.

    Returns `(exit code, removed)`. The two are not the same question and the
    caller needs both: a publication failure after the removal landed is a real
    failure to report *and* an item that is genuinely gone, so a caller that read
    the exit code as "still there" would print a location for a folder that no
    longer exists and skip the cleanup it still owes.
    """
    policy = st.lifecycle_policy()
    item_path = st.path(slug)
    item = st.get(slug)
    if (err := run_pre(policy, "auto-delete", st.node_root, slug, status, item,
                       item_path=item_path, resolution=resolution)):
        gone = _removed(st, slug)
        print(f"tcw work: {err}; {slug} was resolved and committed but its "
              + ("removal was not recorded — the binding moved the item before "
                 "it failed" if gone else "folder was not removed")
              + f". Fix the binding and run `tcw work delete {slug}`.",
              file=sys.stderr)
        return 1, gone
    try:
        location = st.delete_resolved(slug, status)
    except _ERRORS as e:
        # Whether the folder went is a question for the store, not for the
        # exception type. A push that failed, a removal commit a hook refused,
        # and a `pre` guard that refused before anything moved all arrive here,
        # and the first two leave the item gone. Inferring "still there" from a
        # non-zero result is what sent the caller on to print a location for a
        # folder that no longer exists.
        print(f"tcw work: {e}", file=sys.stderr)
        return 1, _removed(st, slug)
    print(f"deleted {slug}; " + (
        f"its documents remain in commit {location}" if location else
        "no commit held its documents, so none is recorded"))
    post_err = run_post(policy, "auto-delete", st.node_root, slug, status, item,
                        item_path=item_path, resolution=resolution)
    return _post_result(post_err, "auto-delete", slug), True


def _delete(args: argparse.Namespace) -> int:
    """`tcw work delete <slug>` — finish a removal an archive failure left pending.

    The same code path the automatic step takes, under a name that reads as
    something a person types. Refuses anything that is not a resolved item this
    node has stopped retaining, so it can never be mistaken for `drop`.
    """
    resolved = _resolve(args.slug, "delete")
    if resolved is None:
        return 1
    st, bare = resolved
    try:
        item = st.get(bare)
    except MultipleMatch as e:
        # Wrapped exactly as `_show` and `_complete` wrap it. `MultipleMatch` is
        # an `Exception`, not a `ValueError`, so `main()`'s catch-all does not
        # see it and an unguarded read here left a raw traceback where every
        # other subcommand reports and exits 1.
        print(f"tcw work delete: {e}", file=sys.stderr)
        return 1
    if item is None:
        # The half-deleted state: the folder is gone and the record does not yet
        # say where it went, because a `pre` binding moved the item away or an
        # earlier attempt was interrupted. Refusing it here made
        # `delete_resolved`'s documented "safe to re-run" unreachable through the
        # CLI and left the tree holding an unstaged deletion forever — which is
        # the one state this command exists to finish.
        grave = st.tombstone(bare)
        if grave is None:
            print(f"tcw work delete: no such work item: {args.slug}",
                  file=sys.stderr)
            return 1
        if not st.pending_removal(bare):
            print(f"{bare} is already removed; its documents are "
                  f"{st.describe_location(grave.location, bare)}")
            return 0
        code, _ = _auto_delete(st, bare, "", grave.resolution)
        return code
    if item.status not in RESOLVED_STATUSES:
        print(f"tcw work delete: {bare} is {item.status}, not resolved. "
              f"`tcw work drop` deletes a backlog item; this finishes the "
              f"removal of one already resolved.", file=sys.stderr)
        return 1
    if not st.pending_deletion(bare):
        print(f"tcw work delete: work.retain.{item.status} keeps resolved items "
              f"in this project, so {bare} is not pending removal.",
              file=sys.stderr)
        return 1
    code, _ = _auto_delete(st, bare, item.status, item.resolution or "")
    return code


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


def _local_owner(st, explicit: str | None = None) -> str:
    """This machine's claimant identity: `--owner`, then `TCW_WORK_OWNER`, then the
    Git email, then the Git name. `""` when none is set."""
    owner = (explicit or os.environ.get("TCW_WORK_OWNER", "")).strip()
    if not owner:
        for key in ("user.email", "user.name"):
            probe = subprocess.run(["git", "-C", str(st.node_root), "config", "--get", key],
                                   stdin=subprocess.DEVNULL,
                                   capture_output=True, text=True)
            if probe.returncode == 0 and probe.stdout.strip():
                owner = probe.stdout.strip()
                break
    return owner


def _deliver_after(st, bare: str, verb: str, move: str, previous_status: str) -> int:
    """Send a transition that has already happened to the item's ticket, if it has one.

    Returns 0 when there is nothing to send or the ticket followed, 1 when it did not.
    The move itself is never undone. An item without a readable binding, or a node
    with no tracker configured, returns 0 before `tcw.tracker` is imported, so a
    project without a tracker loads none of it.
    """
    try:
        item = st.get(bare)
    except MultipleMatch:
        return 0
    value = item.tracker if item is not None else None
    if not isinstance(value, dict) or "problem" in value:
        return 0
    config = st.tracker_config()
    problems = [] if config is not None else st.tracker_problems()
    if config is None and not problems:
        return 0
    from tcw.tracker.sync import CONFLICTING, HELD, PENDING, deliver, record_unsent
    key = value["ticket"]["key"]
    try:
        if config is None:
            outcome = record_unsent(st, bare, move=move, reason=(
                "the tracker configuration has problems: " + "; ".join(problems)
                + ". Run `tcw validate`."))
        else:
            from tcw.tracker.jira import JiraClient
            outcome = deliver(st, bare, JiraClient(config), config, move=move,
                              previous_status=previous_status)
    except _LOCAL_WRITE_ERRORS as e:
        print(f"tcw work {verb}: {bare} moved to {item.status}, but whether {key} "
              f"followed could not be recorded: {e}. Run `tcw work tracker sync "
              f"{bare}`.", file=sys.stderr)
        return 1
    if outcome.claimed:
        print(f"→ {outcome.claimed}", file=sys.stderr)
    if outcome.state == HELD:
        print(f"→ {outcome.reason}", file=sys.stderr)
    if outcome.state not in (PENDING, CONFLICTING):
        return 0
    reason = outcome.reason.rstrip()
    reason += "" if reason.endswith((".", "!", "?")) else "."
    print(f"tcw work {verb}: {bare} moved to {item.status} and was committed; {key} was "
          f"not updated in the tracker ({outcome.state}): {reason} Run "
          f"`tcw work tracker sync {bare}` once that is resolved.", file=sys.stderr)
    return 1


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
                       st.get(bare), item_path=st.path(bare))):
        print(f"tcw work start: {err}; {bare} not started", file=sys.stderr)
        return 1
    owner = _local_owner(st, args.owner)
    if not owner:
        print("tcw work start: claimant identity required; pass --owner or set TCW_WORK_OWNER",
              file=sys.stderr)
        return 1
    before = st.get(bare)
    previous = before.status if before is not None else "backlog"
    strict = (before is not None and before.type != "epic" and st.tracker_strict())
    claimed = False
    if strict:
        code, claimed = _strict_claim(st, bare, before, args)
        if code is not None:
            return code
    try:
        st.start(bare, force=args.force, owner=owner, take_over=args.take_over)
    except _ERRORS as e:
        print(f"tcw work: {e}", file=sys.stderr)
        if claimed and not isinstance(e, TransitionCommitError):
            print(f"tcw work start: under strict tracker mode the ticket was claimed "
                  f"before the start was refused, and is left claimed. Run "
                  f"`tcw work start {bare}` again once that is fixed.", file=sys.stderr)
        if isinstance(e, TransitionCommitError):      # the item did move
            _deliver_after(st, bare, "start", "start", previous)
        return 1
    post_err = run_post(st.lifecycle_policy(), "start", st.node_root, bare, "active",
                        st.get(bare), item_path=st.path(bare))
    # Before any worktree setup, so a failure there cannot skip the claim.
    delivered = _deliver_after(st, bare, "start", "start", previous)
    if not args.worktree:
        loc = st.locate(bare)
        print(f"started {args.slug}" + (f" → {loc}" if loc else ""))
        _complete_hint(args.slug)
        return _post_result(post_err, "start", args.slug) or delivered
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
    return _post_result(post_err, "start", args.slug) or delivered


def _submit(args: argparse.Namespace) -> int:
    resolved = _resolve(args.slug, "submit")
    if resolved is None:
        return 1
    st, bare = resolved
    if (err := run_pre(st.lifecycle_policy(), "submit", st.node_root, bare, "active",
                       st.get(bare), item_path=st.path(bare))):
        print(f"tcw work submit: {err}; {bare} not moved", file=sys.stderr)
        return 1
    if reason := _strict_refusal(st, bare, "submit"):
        return _strict_says_no("submit", f"{bare} was not changed", reason)
    try:
        st.submit(bare)
    except _ERRORS as e:
        print(f"tcw work: {e}", file=sys.stderr)
        if isinstance(e, TransitionCommitError):      # the item did move
            _deliver_after(st, bare, "submit", "submit", "active")
        return 1
    post_err = run_post(st.lifecycle_policy(), "submit", st.node_root, bare, "review",
                        st.get(bare), item_path=st.path(bare))
    delivered = _deliver_after(st, bare, "submit", "submit", "active")
    print(f"submitted {args.slug} → review")
    print(f"→ next: verify the work, then either "
          f"`tcw work complete {args.slug} --resolution done --confirm` or, to "
          f"send it back, delete refined-outcome.md and run "
          f"`tcw work rework {args.slug}`", file=sys.stderr)
    return _post_result(post_err, "submit", args.slug) or delivered


def _rework(args: argparse.Namespace) -> int:
    resolved = _resolve(args.slug, "rework")
    if resolved is None:
        return 1
    st, bare = resolved
    if (err := run_pre(st.lifecycle_policy(), "rework", st.node_root, bare, "review",
                       st.get(bare), item_path=st.path(bare))):
        print(f"tcw work rework: {err}; {bare} not moved", file=sys.stderr)
        return 1
    if reason := _strict_refusal(st, bare, "rework"):
        return _strict_says_no("rework", f"{bare} was not changed", reason)
    try:
        st.rework(bare)
    except _ERRORS as e:
        print(f"tcw work: {e}", file=sys.stderr)
        if isinstance(e, TransitionCommitError):      # the item did move
            _deliver_after(st, bare, "rework", "rework", "review")
        return 1
    post_err = run_post(st.lifecycle_policy(), "rework", st.node_root, bare, "active",
                        st.get(bare), item_path=st.path(bare))
    delivered = _deliver_after(st, bare, "rework", "rework", "review")
    print(f"reworking {args.slug} → active")
    print(f"→ next: address rework.md, then `tcw work submit {args.slug}`",
          file=sys.stderr)
    return _post_result(post_err, "rework", args.slug) or delivered


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


class _HidesRemovedSpellings(argparse.ArgumentParser):
    """Keeps the removed per-stage parsers out of argparse's "choose from" list.

    They are registered as subparsers so the old `tcw work stage <id> <ref>`
    spelling gets a migration message instead of a bare "invalid choice", and
    `help=` is omitted so they stay out of `--help`. But `_check_value` builds
    its "choose from" list straight off the action's choices, so a plain typo was
    told the seven removed spellings were valid verbs — the opposite of what
    registering them is for.

    The guard is narrow on purpose: it fires only for the action that actually
    offers both real verbs, so every other subcommand group keeps argparse's own
    message unchanged.
    """

    def _check_value(self, action, value):
        choices = getattr(action, "choices", None) or ()
        if value not in choices and {"prompt", "gate"} <= set(choices):
            real = [c for c in choices if c not in STAGE_IDS]
            raise argparse.ArgumentError(
                action, f"invalid choice: {value!r} (choose from "
                        f"{', '.join(repr(c) for c in real)})")
        super()._check_value(action, value)


def _stage_tail(args: argparse.Namespace, step, st, item, slug: str,
                display: str) -> int:
    """Everything `tcw work stage prompt` does once it knows what to resolve.

    Shared by the path that has a work item and the path that does not, so the
    two cannot drift: the `--no-exec` plan, the failure messages, and the stdout
    discipline have exactly one definition. The caller decides *what* is being
    resolved — an item or nothing, this node or another — and decides it before
    calling; this function decides none of it.

    It runs no checks. It used to take a `run_checks` flag, from when one verb
    both gated and printed; `gate` resolves no prompt, so the two share no tail
    any more and the flag is gone rather than left as a parameter a single
    caller never passes.

    `item` is `None` on the itemless path, which `resolve_prompts` and
    `hook_env` both already accept. A `when:`-condition then never matches
    (`Condition.matches` answers False for no item), so a project's conditioned
    binding does not fire on nothing.

    `slug` addresses the item in `st` and is always **bare**, because `_resolve`
    strips any `<project-id>/` qualifier by contract. `display` is what the user
    typed, and is the only thing that may appear in a command this prints: the
    bookend quotes a `tcw work stage gate` line back, and a bare slug there would
    send a cross-node reader to their own node. Slugs are date-prefixed and
    derived from titles, so two nodes filing the same request on one day collide.

    Stream discipline: stdout carries the resolved prompt and nothing else,
    emitted once at the end after everything that could fail has succeeded, and
    nothing at all under `--no-exec`.
    """
    policy = st.lifecycle_policy()
    try:
        res = resolve_prompts(policy, step.id, item, st.node_root,
                              load_builtins(),
                              artifacts=st.artifacts(slug) if item is not None
                              else (),
                              env=dict(os.environ),
                              execute=not args.no_exec,
                              documentation=st.documentation())
    except ResolveError as e:
        print(f"tcw work stage prompt: {e}", file=sys.stderr)
        return 1

    if args.no_exec:
        # A plan, never text: printing the partial resolution on stdout is the
        # thing this flag was once refused for. stdout stays empty.
        print(f"tcw work stage prompt {step.id}: --no-exec, nothing was "
              f"resolved", file=sys.stderr)
        for entry in res.plan:
            state = "matched" if entry.matched else "skipped (condition)"
            detail = f": {entry.ref}" if entry.kind != "builtin" else ""
            print(f"  prompt {entry.kind} — {state}{detail}", file=sys.stderr)
        return 0

    # Bookended here rather than in the resolver: a stage that resolves to
    # nothing prints nothing, and a header wrapped around an empty middle would
    # make silence look like a stage that failed to resolve.
    if res.text:
        print(bookend(res.text, step.id, display or "<slug>"))
    return 0


def _stage_gate(args: argparse.Namespace, step, st, item, slug: str,
                status: str, display: str) -> int:
    """`tcw work stage gate` once it knows what it is gating.

    The whole verb: the stage's `pre` bindings, and nothing else. It resolves no
    prompt — not even to discard it — so a `generate:` binding does not run a
    script for output nobody reads.

    **stdout stays empty on success.** The pointer to the verb that does print
    goes to stderr with every other diagnostic, so a caller piping this verb gets
    nothing rather than a line it would have to strip. Silence on stdout is the
    contract; the exit code is the answer.

    `slug` is bare and addresses the item; it is what the hook environment
    carries. `display` is what the user typed and is the only thing that may
    appear in the `tcw work stage prompt` line this prints, for the same reason
    the bookend needs it: a stripped qualifier names a different node's item.
    """
    policy = st.lifecycle_policy()
    declared = policy.stage_checks(step.id)
    checks = select(declared, item)
    if args.no_exec:
        # A plan, so stderr — and only this verb's own bindings. The prompt
        # bindings are `tcw work stage prompt --no-exec`'s to report now, and
        # `tcw work lifecycle --stage <id> --phase prompt` lists them without
        # resolving at all.
        print(f"tcw work stage gate {step.id}: --no-exec, nothing was executed",
              file=sys.stderr)
        # Conditioned-out checks are named rather than omitted, the way the
        # reading verb already names its skipped prompt bindings. Silence here
        # is ambiguous between "you bound none" and "yours did not match" — and
        # on `inbox` there is no item at all, so every `when:` is filtered and a
        # bare list would report a project's own bindings as though absent.
        kept = {id(b) for b in checks}
        for b in declared:
            state = "would run" if id(b) in kept else "skipped (condition)"
            print(f"  pre check {state}: {b.ref}", file=sys.stderr)
        return 0

    err = run_bindings(checks, st.node_root,
                       hook_env(st.node_root, slug, status, step.id),
                       policy.timeout, f"{step.id} pre")
    if err:
        print(f"tcw work stage gate: {err}", file=sys.stderr)
        return 1

    ref = "" if step.id == "inbox" else f" {display}"
    print(f"tcw work stage gate {step.id}: checks passed; run "
          f"`tcw work stage prompt {step.id}{ref}` for the instructions",
          file=sys.stderr)
    return 0


def _stage_step(verb: str, stage_id: str):
    """The `LifecycleStep` for a stage id, or None after reporting why not."""
    step = LIFECYCLE_STEPS_BY_ID.get(stage_id)
    if step is None or step.kind != "stage":
        legal = [s.id for s in LIFECYCLE_STEPS if s.kind == "stage"]
        print(f"tcw work stage {verb}: unknown stage '{stage_id}'; expected one "
              f"of {', '.join(legal)}", file=sys.stderr)
        return None
    return step


def _stage_removed_form(args: argparse.Namespace) -> int:
    """`tcw work stage <stage> <slug>` — removed in 2.0.0, reported not run.

    A usage error rather than an operation that failed, so it exits 2 like every
    other malformed command line. It deliberately does **not** run the stage:
    accepting the old spelling here would be the alias this release decided
    against, and a migration nobody is forced to make is one nobody makes.
    """
    # `inbox` runs before an item exists and both verbs refuse a reference for
    # it, so the placeholder every other stage wants would advise a command that
    # is itself refused — two wrong turns for someone migrating off the old
    # spelling. The one stage that takes no reference is shown none.
    if args.removed_stage == "inbox":
        ref = ""
    else:
        ref = f" {args.rest[0]}" if args.rest else " <slug>"
    print(f"tcw work stage: '{args.removed_stage}' is not a subcommand; run "
          f"`tcw work stage gate {args.removed_stage}{ref}` to check the "
          f"stage and run its checks, or `tcw work stage prompt "
          f"{args.removed_stage}{ref}` for its instructions", file=sys.stderr)
    return 2


def _stage_prompt(args: argparse.Namespace) -> int:
    """`tcw work stage prompt <stage> [ref]` — the instructions, nothing else.

    Runs no gate of its own: no status-legality check and no `pre` bindings. It
    still resolves `file:` and `generate:` bindings, because those are how the
    text is produced — so the promise is "no check TCW decides to run", not "no
    process is started", which would be false.

    The reference is optional and does two things, not one. Without it,
    resolution runs against the local anchor node with `item=None`. With it, the
    reference goes through `_resolve`, so a `<project-id>/<slug>` qualifier
    selects **that node's** configuration — a different `tcw-config.yaml`, its
    `prompt:` bindings, and its documentation entries.

    An illegal stage still prints. The built-in prompts carry state-changing
    instructions — `verify` opens with `tcw work submit` — so reading one out of
    context is worth a warning, but the warning goes to stderr and the exit code
    stays 0: a caller piping stdout asked for the text and gets exactly it.

    `--no-exec` is accepted here, and was once refused. The refusal's reason was
    that suppressing `file:` and `generate:` would leave *incomplete
    instructions* on stdout — which is only true if it prints any. It prints
    none: the plan goes to stderr and stdout stays empty. Refusing it now would
    drop the conditioned matched/skipped diagnostic from the CLI entirely, since
    `gate` reports only its own bindings.
    """
    step = _stage_step("prompt", args.stage_id)
    if step is None:
        return 1
    if args.slug is None:
        st = _store()
        if st is None:
            return 1
        return _stage_tail(args, step, st, None, "", "")

    if step.id == "inbox":
        print(f"tcw work stage prompt: '{step.id}' runs before an item exists "
              f"and takes no work item; run it with no argument",
              file=sys.stderr)
        return 1

    resolved = _resolve(args.slug, "stage prompt")
    if resolved is None:
        return 1
    st, bare = resolved
    try:
        item = st.get(bare)
    except MultipleMatch as e:
        print(f"tcw work stage prompt: {e}", file=sys.stderr)
        return 1
    if item is None:
        print(f"tcw work stage prompt: no such work item: {args.slug}",
              file=sys.stderr)
        return 1

    legal = STAGE_STATUSES[step.id]
    if legal and item.status not in legal:
        print(f"tcw work stage prompt: note — '{step.id}' is not legal for an "
              f"item in '{item.status}'; it runs in {', '.join(legal)}. Printing "
              f"its instructions anyway because you asked to read them, not to "
              f"enter the stage.", file=sys.stderr)

    return _stage_tail(args, step, st, item, bare, args.slug)


def _stage_without_item(args: argparse.Namespace, step) -> int:
    """The `inbox` half of `tcw work stage gate`: same contract, no item.

    Every step the item path takes that *reads* the item is skipped rather than
    fed a placeholder — no `get`, no status-legality check. The empty slug and
    status are what the hook environment carries when there is no item to name.
    The stage's `pre` bindings still run: `inbox` skips the *legality* check,
    which has no status to judge, not the checks the project bound.

    **An unconditioned binding, though.** `select` answers False for every
    `when:` when the item is `None`, so a conditioned `inbox` check can never
    fire — there is no item to condition on, which is the stage's whole nature.
    That is not a bug to fix here, but it is silent, so `--no-exec` names the
    skipped ones rather than printing a list that looks like "you bound none".
    """
    st = _store()
    if st is None:
        return 1
    return _stage_gate(args, step, st, None, "", "", "")


def _stage(args: argparse.Namespace) -> int:
    """`tcw work stage gate <id> [ref]` — may this stage run, and run its checks.

    Order matters and is the contract: id → item → legality → checks. Legality is
    decided **before any hook runs** — not before any read, which is impossible,
    since the item's status is the thing being judged.

    It prints no instructions. `tcw work stage prompt` is the only verb that
    resolves them, so the text exists in one place and nothing has to explain why
    two commands printed the same bytes. What this verb supplies that `prompt`
    does not is the refusal.
    """
    step = _stage_step("gate", args.stage_id)
    if step is None:
        return 1

    # `inbox` runs before an item exists, so it resolves against the node alone.
    # Branching on the **stage id**, never on `STAGE_STATUSES[step.id]` being
    # empty: that emptiness says "no work-item status applies", which is a true
    # statement about this stage and not a licence to read it as "any status".
    if step.id == "inbox":
        if args.slug is not None:
            print(f"tcw work stage gate: '{step.id}' runs before an item exists "
                  f"and takes no work item; run it with no argument",
                  file=sys.stderr)
            return 1
        return _stage_without_item(args, step)
    if args.slug is None:
        print(f"tcw work stage gate: '{step.id}' needs a work item; run "
              f"`tcw work stage gate {step.id} <slug>`, or "
              f"`tcw work stage prompt {step.id}` to read its instructions "
              f"without gating them", file=sys.stderr)
        return 1

    resolved = _resolve(args.slug, "stage gate")
    if resolved is None:
        return 1
    st, bare = resolved
    try:
        item = st.get(bare)
    except MultipleMatch as e:
        print(f"tcw work stage gate: {e}", file=sys.stderr)
        return 1
    if item is None:
        print(f"tcw work stage gate: no such work item: {args.slug}",
              file=sys.stderr)
        return 1

    legal = STAGE_STATUSES[step.id]
    if item.status not in legal:
        print(f"tcw work stage gate: '{step.id}' is not legal for an item in "
              f"'{item.status}'; it runs in {', '.join(legal)}", file=sys.stderr)
        return 1

    return _stage_gate(args, step, st, item, bare, item.status, args.slug)


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
    `complete`. The third has no stage to hang off —
    `tcw work stage gate implement` on a completed item is refused by the status
    check, correctly — so it needs a verb of its own.

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


def _tag_args(values: list[str]) -> list[str]:
    """Flatten ``tags add|rm`` positionals: argparse does not apply a
    list-returning ``type=`` under ``nargs``, so the split happens here."""
    return [tag for value in values for tag in _tag_list(value)]


def _tracker_client(label: str):
    """The configured tracker client, or None after printing why not.

    A tracker that is absent and a tracker that is misconfigured are different
    failures and get different messages: one tells you to configure it, the other
    tells you what is wrong. `tracker_config` fails closed, so a misconfigured
    block reads as absent — `tracker_problems` is the only way to tell them apart.
    """
    st = _store()
    if st is None:
        return None
    config = st.tracker_config()
    if config is None:
        problems = st.tracker_problems()
        if problems:
            print(f"tcw work tracker {label}: the tracker configuration has "
                  f"problems:", file=sys.stderr)
            for problem in problems:
                print(f"  - {problem}", file=sys.stderr)
        else:
            print(f"tcw work tracker {label}: no tracker is configured. Add a "
                  f"work.tracker block to tcw-config.yaml.", file=sys.stderr)
        return None
    from tcw.tracker.jira import JiraClient
    return JiraClient(config)


def _tracker_list(args: argparse.Namespace) -> int:
    client = _tracker_client("list")
    if client is None:
        return 1
    from tcw.tracker.jira import TrackerError
    try:
        result = client.search(client.config.candidate_query)
    except TrackerError as e:
        print(f"tcw work tracker list: {e}", file=sys.stderr)
        return 1
    for issue in result.issues:
        fields = issue.get("fields") or {}
        status = (fields.get("status") or {}).get("name", "?")
        assignee = (fields.get("assignee") or {}).get("displayName", "unassigned")
        summary = fields.get("summary", "")
        print(f"{issue.get('key', '?')} | {status} | {assignee} | {summary}")
    if not result.issues:
        print("No tickets matched the configured query.")
    if result.truncated:
        # Never silently short: a user would conclude they have nothing else. No
        # total is printed because the endpoint does not report one.
        print(f"Showing the first {len(result.issues)}; there are more. "
              f"Narrow work.tracker.candidate-query to see the rest.",
              file=sys.stderr)

    return 0


def _tracker_show(args: argparse.Namespace) -> int:
    client = _tracker_client("show")
    if client is None:
        return 1
    from tcw.tracker.claim import assess
    from tcw.tracker.jira import TrackerError
    try:
        issue = client.issue(args.ticket)
        offered = client.transitions(args.ticket)
    except TrackerError as e:
        print(f"tcw work tracker show: {e}", file=sys.stderr)
        return 1

    fields = issue.get("fields") or {}
    status = (fields.get("status") or {}).get("name", "?")
    assignee = (fields.get("assignee") or {}).get("displayName", "unassigned")
    print(f"{issue.get('key', args.ticket)}  [{status}]")
    print(f"summary: {fields.get('summary', '')}")
    print(f"assignee: {assignee}")

    result = assess(client.config.claim_transition,
                    current_status=status, offered=offered)
    # Two words, deliberately never one. "claimable" is this ticket right now;
    # "exclusive" is whether the workflow would refuse a second claimant. A reader
    # told "claimable" about a ticket on a non-excluding workflow has been told
    # something true and misleading at once.
    print(f"claimable: {result.claimable}")
    print(f"workflow: {result.exclusivity}")
    if result.detail:
        print(f"note: {result.detail}")
    return 0


def _project_id(st) -> str:
    return registered_project_id(st.node_root, st.node_root)


def _print_refusal(label: str, outcome) -> None:
    """A claim refusal: a fixed first line, and the tracker's own text only on a
    `detail:` line, so it is never read as the explanation."""
    print(f"tcw work tracker {label}: {outcome.message}", file=sys.stderr)
    if outcome.detail:
        print(f"  detail: {outcome.detail}", file=sys.stderr)


def _intake_text(outcome, description: str, today: str) -> str:
    body = description.strip() or "The ticket has no description."
    return (f"# {outcome.key} — {outcome.summary}\n\n"
            f"Imported on {today} from [{outcome.key}]({outcome.url}) (jira-cloud).\n\n"
            f"{body}\n")


def _binding_for(provider: str, project: str, ticket_id: str, ticket_key: str,
                 ticket_url: str, part: str, today: str, unlinked: list) -> str:
    """The binding document. `provider` and `project` are the values the ticket was
    looked up with, passed in rather than read again: tracker settings can come from
    parent nodes' files, and one changed or broken mid-run would otherwise fail here,
    after the tracker has already been read (and, for `import`, the ticket claimed)."""
    from tcw.tracker.intake import binding_document
    return binding_document(
        provider=provider, project=project, part=part,
        ticket_id=ticket_id, ticket_key=ticket_key, ticket_url=ticket_url,
        bound=today, unlinked=unlinked)


def _claim_summary(outcome) -> str:
    how = "claimed by this run" if outcome.transitioned else "already assigned to you"
    return f"{outcome.key} is in '{outcome.status}', {how}"


# The failures a local write can raise once the tracker has answered. Wider than
# `_ERRORS` on purpose: a held Git index lock surfaces as `CalledProcessError`, and
# `import`'s claimed ticket has to be reported whichever way the write failed.
_LOCAL_WRITE_ERRORS = (*_ERRORS, StaleRevision, OSError, subprocess.CalledProcessError)


def _tracker_import(args: argparse.Namespace) -> int:
    """Claim a ticket, then create a backlog item bound to it.

    No item is created unless the claim ends with the ticket in the status the claim
    leads to and assigned to this account. A claim that succeeds and then fails
    locally is finished by running the command again: the ticket is then already
    assigned to this account, which the claim accepts without a second transition.
    """
    from datetime import date

    from tcw.tracker.intake import (BINDING_SIDECAR, BindingProblem, claim,
                                    find_binding, read_ticket, validate_part)
    from tcw.tracker.jira import TrackerError

    client = _tracker_client("import")
    if client is None:
        return 1
    try:
        part = validate_part(args.part)
    except ValueError as e:
        print(f"tcw work tracker import: {e}", file=sys.stderr)
        return 1
    if args.title is not None and not args.title.strip():
        print("tcw work tracker import: --title is empty; give a title or omit it "
              "to use the ticket's key and summary.", file=sys.stderr)
        return 1
    st = _store()
    today = date.today().isoformat()
    try:
        ticket = read_ticket(client, args.ticket)
        project = _project_id(st)
        existing = find_binding(st, project=project,
                                provider=client.config.provider,
                                ticket_id=ticket.issue_id, part=part,
                                base_url=client.config.base_url)
        if existing is not None:
            print(existing)
            if ticket.assignee_id == ticket.me_id:
                print(f"→ already bound: {ticket.key} (part {part}) is {existing}",
                      file=sys.stderr)
                return 0
            if not ticket.assignee_id:
                # What `link` leaves behind: bound, never claimed. Normal, not drift.
                print(f"tcw work tracker import: {existing} is already linked to "
                      f"{ticket.key} (part {part}), but the ticket is not claimed — it "
                      f"is unassigned in '{ticket.status}'. `import` does not claim a "
                      f"ticket that is already bound; move and assign it in the "
                      f"tracker yourself.", file=sys.stderr)
                return 1
            holder = ticket.assignee_name
            print(f"tcw work tracker import: {existing} is bound here, but the tracker "
                  f"says {ticket.key} is assigned to {holder} in '{ticket.status}'.",
                  file=sys.stderr)
            return 1
        outcome = claim(client, ticket)
    except (TrackerError, BindingProblem, ValueError) as e:
        print(f"tcw work tracker import: {e}", file=sys.stderr)
        return 1
    if not outcome.claimed:
        _print_refusal("import", outcome)
        return 1
    if client.config.strict:
        from tcw.tracker.sync import claim_refusal
        if refusal := claim_refusal(client, client.config, outcome.issue_id, outcome):
            return _strict_says_no("tracker import", "no item was created", refusal)
    try:
        description = client.description(outcome.issue_id)
    except TrackerError as e:
        print(f"tcw work tracker import: claimed {outcome.key}, but its description "
              f"could not be read: {e}. Run this command again.", file=sys.stderr)
        return 1

    title = args.title.strip() if args.title else f"{outcome.key} — {outcome.summary}"
    try:
        slug = st.create_work(title, intake=_intake_text(outcome, description, today)
                              ).item.slug
    except _LOCAL_WRITE_ERRORS as e:
        print(f"tcw work tracker import: claimed {outcome.key}, but the item could not "
              f"be created: {e}. Fix that and run this command again.", file=sys.stderr)
        return 1
    try:
        st.write_sidecar(slug, BINDING_SIDECAR,
                         _binding_for(client.config.provider, project,
                                      outcome.issue_id, outcome.key, outcome.url,
                                      part, today, []), revision="")
    except _LOCAL_WRITE_ERRORS as e:
        try:
            st.drop(slug)
        except _LOCAL_WRITE_ERRORS as drop_error:
            print(f"tcw work tracker import: claimed {outcome.key}, but the binding "
                  f"could not be written: {e}. The item {slug} was created unbound and "
                  f"could not be removed either ({drop_error}). Run "
                  f"`tcw work drop {slug} --confirm` before importing again, or a "
                  f"second item will be created.", file=sys.stderr)
            return 1
        print(f"tcw work tracker import: claimed {outcome.key}, but the binding could "
              f"not be written: {e}. Run this command again.", file=sys.stderr)
        return 1
    print(slug)
    print(f"→ {_claim_summary(outcome)}; bound to {slug}", file=sys.stderr)
    if not outcome.transitioned:
        print(f"→ {outcome.message}", file=sys.stderr)
    return 0


def _item_or_reason(st, slug: str, label: str):
    """The item `slug` names in this node, or None after saying it is not there. A
    bare slug only: a tracker configuration and a project id belong to one node.

    Every status is bindable, resolved ones included: finished work can be linked to
    the ticket that tracked it, and a wrong binding on it can be repaired. Such a
    binding lives wherever the rest of the resolved item does: where resolved folders
    are gitignored (the default) it is on disk but never committed. Once a store has
    removed a resolved item this slug refuses as unknown; before that — a resolved
    item not retained but not yet deleted — it binds like any other."""
    # ponytail: no warning when a binding lands in a gitignored resolved folder;
    # add one in the filesystem adapter if local-only bindings surprise anyone.
    item = st.get(slug)
    if item is None:
        print(f"tcw work tracker {label}: no such work item in this node: {slug}",
              file=sys.stderr)
        return None
    return item


def _tracker_link(args: argparse.Namespace) -> int:
    """Record that an existing item and a ticket are the same work.

    The binding sidecar is the whole effect. The ticket is read — which is what
    proves the key exists and yields the canonical key, id and URL the binding
    stores — and is otherwise left exactly as it was: no transition, no assignee
    change. Nothing in the item but `tracker.yaml` is written either, so its
    status, owner, intake and request are untouched.
    """
    from datetime import date

    from tcw.tracker.intake import (BINDING_SIDECAR, BindingProblem, Bound, Malformed,
                                    binding_of, find_binding, read_ticket,
                                    unlinked_history, validate_part)
    from tcw.tracker.jira import TrackerError

    client = _tracker_client("link")
    if client is None:
        return 1
    try:
        part = validate_part(args.part)
    except ValueError as e:
        print(f"tcw work tracker link: {e}", file=sys.stderr)
        return 1
    st = _store()
    if _item_or_reason(st, args.slug, "link") is None:
        return 1
    current, revision = binding_of(st, args.slug)
    if isinstance(current, Malformed):
        print(f"tcw work tracker link: {args.slug} has a {BINDING_SIDECAR} that cannot "
              f"be read ({current.reason}).", file=sys.stderr)
        return 1
    if isinstance(current, Bound):
        print(f"tcw work tracker link: {args.slug} is already bound to "
              f"{current.ticket_key} (part {current.part}). Run `tcw work tracker "
              f"unlink {args.slug} --reason <text>` first.", file=sys.stderr)
        return 1
    try:
        ticket = read_ticket(client, args.ticket)
        project = _project_id(st)
        holder = find_binding(st, project=project,
                              provider=client.config.provider,
                              ticket_id=ticket.issue_id, part=part,
                              base_url=client.config.base_url)
        if holder is not None:
            print(f"tcw work tracker link: {ticket.key} (part {part}) is already bound "
                  f"to {holder}.", file=sys.stderr)
            return 1
    except (TrackerError, BindingProblem, ValueError) as e:
        print(f"tcw work tracker link: {e}", file=sys.stderr)
        return 1
    existing = st.read_sidecar(args.slug, BINDING_SIDECAR)
    today = date.today().isoformat()
    document = _binding_for(client.config.provider, project, ticket.issue_id,
                            ticket.key, ticket.url, part, today,
                            unlinked_history(existing.content if existing else None))
    try:
        st.write_sidecar(args.slug, BINDING_SIDECAR, document, revision=revision or "")
    except _LOCAL_WRITE_ERRORS as e:
        print(f"tcw work tracker link: the binding could not be written: {e}. "
              f"Run this command again.", file=sys.stderr)
        return 1
    print(f"→ bound {args.slug} to {ticket.key} ({ticket.url}). The ticket is "
          f"unchanged in the tracker.", file=sys.stderr)
    return 0


def _tracker_unlink(args: argparse.Namespace) -> int:
    """Remove an item's binding, keeping the record of it and the reason.

    A local repair: no tracker call and no tracker configuration needed, so a
    binding can be removed after `work.tracker` itself is gone.
    """
    from datetime import date

    from tcw.tracker.intake import (BINDING_SIDECAR, Bound, Malformed, binding_of,
                                    unlink_document)

    if not args.reason.strip():
        print("tcw work tracker unlink: --reason is empty; say why the binding is "
              "being removed.", file=sys.stderr)
        return 1
    st = _store()
    if st is None or _item_or_reason(st, args.slug, "unlink") is None:
        return 1
    current, revision = binding_of(st, args.slug)
    if isinstance(current, Malformed):
        print(f"tcw work tracker unlink: {args.slug} has a {BINDING_SIDECAR} that "
              f"cannot be read ({current.reason}).", file=sys.stderr)
        return 1
    if not isinstance(current, Bound):
        print(f"tcw work tracker unlink: {args.slug} is not bound to a ticket.",
              file=sys.stderr)
        return 1
    content = st.read_sidecar(args.slug, BINDING_SIDECAR).content
    document = unlink_document(content, reason=args.reason.strip(),
                               today=date.today().isoformat())
    try:
        st.write_sidecar(args.slug, BINDING_SIDECAR, document, revision=revision)
    except _LOCAL_WRITE_ERRORS as e:
        print(f"tcw work tracker unlink: {e}", file=sys.stderr)
        return 1
    print(f"→ unlinked {args.slug} from {current.ticket_key}. The ticket is unchanged "
          f"in the tracker.", file=sys.stderr)
    return 0


def _tracker_sync(args: argparse.Namespace) -> int:
    """Retry delivery for one bound item, or every item with a sync record."""
    if bool(args.slug) == bool(args.all):
        print("tcw work tracker sync: name one slug, or pass --all.", file=sys.stderr)
        return 1
    client = _tracker_client("sync")
    if client is None:
        return 1
    from tcw.tracker.intake import Bound, binding_of
    from tcw.tracker.sync import CURRENT, HELD, NONE, deliver
    st = _store()
    if args.all:
        slugs = [item.slug for item in st.query()
                 if isinstance(item.tracker, dict) and item.tracker.get("sync")]
    else:
        if _item_or_reason(st, args.slug, "sync") is None:
            return 1
        if not isinstance(binding_of(st, args.slug)[0], Bound):
            print(f"tcw work tracker sync: {args.slug} is not bound to a ticket.",
                  file=sys.stderr)
            return 1
        slugs = [args.slug]
    me = _local_owner(st)
    code = 0
    for slug in slugs:
        item = st.get(slug)
        if item.owner and item.owner != me:
            print(f"{slug}: skipped — started by {item.owner}")
            continue
        recorded = item.tracker.get("sync")
        usable = isinstance(recorded, dict) and "problem" not in recorded
        try:
            outcome = deliver(st, slug, client, client.config, move=None,
                              previous_status=None, check_only=not usable)
        except _LOCAL_WRITE_ERRORS as e:
            print(f"{slug}: the record could not be written: {e}")
            code = 1
            continue
        if outcome.state in (CURRENT, NONE):
            print(f"{slug}: current")
        elif outcome.state == HELD:
            print(f"{slug}: held — {outcome.reason}")
        else:
            print(f"{slug}: {outcome.state} — {outcome.reason}")
            code = 1
    return code


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
        result = st.register_tags(_tag_args(args.tag))
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
        result = st.unregister_tags(_tag_args(args.tag))
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
    # Before the merge-back, which runs ahead of the `pre` hook: a refusal must leave
    # the item, its branch and its worktree exactly as they were. Discards are never
    # refused — abandoning work authorizes none.
    if shipping and (reason := _strict_refusal(st, bare, "complete")):
        return _strict_says_no("complete", f"{bare} was not changed", reason)
    if shipping and has_worktree and branch and not args.already_integrated:
        err = merge_worktree(st.node_root, branch)
        if err:
            print(f"tcw work complete: {err}", file=sys.stderr)
            staged = subprocess.run(
                ["git", "-C", str(st.store_git_root), "diff", "--cached", "--name-only",
                 "--", str(st.path(bare) / "tracker.yaml")],
                stdin=subprocess.DEVNULL, capture_output=True, text=True).stdout.strip()
            if staged and isinstance(item.tracker, dict) and item.tracker.get("sync"):
                # A delivery record is staged, never committed, and git will not
                # merge over a staged file the branch also carries.
                print(f"tcw work complete: {bare}'s tracker.yaml holds a record of a "
                      f"ticket move that did not reach the tracker, staged but not "
                      f"committed. Run `tcw work tracker sync {bare}` to clear it once "
                      f"the ticket follows, or commit it, then complete again.",
                      file=sys.stderr)
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
                       item, item_path=st.path(bare),
                       resolution=args.resolution)):
        print(f"tcw work complete: {err}; {bare} not closed", file=sys.stderr)
        return 1
    previous = item.status
    try:
        st.complete(bare, args.resolution, dod_ack=checklist, force=args.force)
    except _ERRORS as e:
        print(f"tcw work complete: {e}", file=sys.stderr)
        if isinstance(e, TransitionCommitError):      # the item did move
            _deliver_after(st, bare, "complete", transition_id, previous)
        return 1
    resolved_status = "completed" if shipping else "discarded"
    post_err = run_post(policy, transition_id, st.node_root, bare,
                        resolved_status, item, item_path=st.path(bare),
                        resolution=args.resolution)
    # Before any removal: a record of what did not reach the tracker lives in the
    # item's folder, and removing the folder would lose it.
    delivered = _deliver_after(st, bare, "complete", transition_id, previous)
    loc = st.locate(bare)
    delete_code = 0
    if delivered and st.pending_deletion(bare):
        ticket = (st.get(bare).tracker or {}).get("ticket", {}).get("key", "its ticket")
        print(f"tcw work complete: {bare} was kept rather than removed: {ticket} was not "
              f"updated, and a record of that cannot be kept in a folder about to be "
              f"removed. Move {ticket} in the tracker yourself, then run "
              f"`tcw work delete {bare}`.", file=sys.stderr)
    elif st.pending_deletion(bare):
        # Never an early return. The completion has already landed and its `post`
        # result, its own report line and the worktree cleanup are all still owed
        # — `merge_worktree` ran further up, so returning here orphaned the
        # worktree and its branch with nothing left to remove them.
        delete_code, removed = _auto_delete(st, bare, resolved_status,
                                            args.resolution)
        if removed:
            loc = None
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
    return _post_result(post_err, transition_id, args.slug) or delete_code or delivered


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
    if st.tracker_strict():
        from tcw.tracker.intake import ever_bound
        if ever_bound(st, bare):
            return _strict_says_no("drop", f"{bare} was not dropped",
                                   f"It is, or was, bound to a ticket, and dropping would "
                                   f"erase that record. Discard it instead: `tcw work "
                                   f"complete {bare} --resolution wontfix --confirm`.")
    try:
        st.drop(bare)
    except _ERRORS as e:
        print(f"tcw work: {e}", file=sys.stderr)
        return 1
    print(f"dropped {args.slug}")
    return 0


def add_subparser(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser(NAME, help="the changes — work items through a state machine")
    g = p.add_subparsers(dest="cmd", required=True,
                         parser_class=_HidesRemovedSpellings)

    # A positional has no flag to hint at its meaning, so every one of them says
    # what it wants. These three recur; the rest are written where they are added.
    SLUG_HELP = "the work item's slug; `<project-id>/<slug>` reaches another node"
    BARE_SLUG_HELP = "a work item slug in this node; a tracker belongs to one node, "\
                     "so this one is never node-qualified"
    TICKET_HELP = "a ticket key, e.g. EX-123"
    ENTRY_HELP = "a raw inbox entry (`tcw work inbox list` prints them)"

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
    pins.add_argument("entry", help=ENTRY_HELP)
    pins.set_defaults(func=_inbox_show)
    pina = ing.add_parser("accept", help="accept one raw entry into backlog")
    pina.add_argument("entry", help=ENTRY_HELP)
    pina.add_argument("--title", help="override the derived work-item title")
    pina.set_defaults(func=_inbox_accept)

    g.add_parser("nodes", help="list this node's parent + child nodes").set_defaults(func=_nodes)

    pr = g.add_parser("reconcile", help="scan child nodes → write the epic rollup")
    pr.add_argument("slug", help="the epic's slug, in this node")
    pr.add_argument("--commit", action="store_true", help="also commit the rollup")
    pr.add_argument("--complete-when-ready", action="store_true",
                    help="auto-complete the epic if all its children are resolved")
    pr.set_defaults(func=_reconcile)

    pdg = g.add_parser("delegate", help="write a request into a child node's inbox/")
    pdg.add_argument("child", help="child node's canonical project id (`tcw work nodes` lists them)")
    pdg.add_argument("title", help="the request's title, as the child node will see it")
    pdg.add_argument("--initiative", help="stamp the request with an initiative slug")
    pdg.set_defaults(func=_delegate)

    pes = g.add_parser("escalate", help="write a request into the parent node's inbox/")
    pes.add_argument("title", help="the request's title, as the parent node will see it")
    pes.add_argument("--initiative", help="stamp the request with an initiative slug")
    pes.set_defaults(func=_escalate)

    ptg = g.add_parser("tags", help="manage this node's registered tag set")
    ptgs = ptg.add_subparsers(dest="tags_cmd", required=True)
    ptgs.add_parser("list", help="print the registered tags").set_defaults(func=_tags_list)
    ptga = ptgs.add_parser("add", help="register one or more tags")
    ptga.add_argument("tag", nargs="+",
                         help="tag(s) to register (a value may be a,b,c)")
    ptga.set_defaults(func=_tags_add)
    ptgr = ptgs.add_parser("rm", help="unregister one or more tags")
    ptgr.add_argument("tag", nargs="+",
                         help="tag(s) to unregister (a value may be a,b,c)")
    ptgr.set_defaults(func=_tags_rm)

    # Every description below states what the command changes in the tracker and
    # what it changes in the work store, in that order, because a command reaching
    # a system outside the repository is the one place a surprise is expensive.
    ptr = g.add_parser("tracker",
                       help="read the configured external tracker, and take its tickets")
    ptrs = ptr.add_subparsers(dest="tracker_cmd", required=True)
    ptrs.add_parser(
        "list", help="list tickets the configured query selects",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description="Print the tickets work.tracker.candidate-query selects, one per line,\n"
                    "as KEY | status | assignee | summary.\n\n"
                    "Reads only: nothing changes in the tracker or in this node.",
        epilog="Refuses when no tracker is configured for this node.\n\n"
               "A long result is cut short and says so; narrow the query to see the\n"
               "rest.\n\n"
               "  tcw work tracker list\n",
    ).set_defaults(func=_tracker_list)

    ptrsh = ptrs.add_parser(
        "show", help="show one ticket and whether it is claimable",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description="Print one ticket's status, summary and assignee, then whether the\n"
                    "claim transition is on offer from its status now and whether the\n"
                    "workflow would keep a second claimant out.\n\n"
                    "Reads only: nothing changes in the tracker or in this node.",
        epilog="'claimable' is whether this status offers the claim right now; it does\n"
               "not look at the assignee, which import also checks. 'workflow' is\n"
               "whether claiming excludes anyone else. They are reported separately\n"
               "on purpose.\n\n"
               "Refuses when no tracker is configured, or when the key does not exist.\n\n"
               "  tcw work tracker show EX-123\n",
    )
    ptrsh.add_argument("ticket", help=TICKET_HELP)
    ptrsh.set_defaults(func=_tracker_show)

    ptri = ptrs.add_parser(
        "import", help="claim a ticket and create a backlog item bound to it",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description="Claim a ticket, then create a work item for it.\n\n"
                    "In the tracker: moves the ticket through the configured claim\n"
                    "transition and assigns it to you.\n\n"
                    "In this node: creates a backlog item whose intake is the ticket's\n"
                    "description, and binds the two.\n\n"
                    "No item is created unless the claim succeeds. A run that fails\n"
                    "locally is finished by running it again; the error says so when\n"
                    "it is not.",
        epilog="Use --part when one ticket is split across several items; each part\n"
               "is bound separately and the name is yours to choose.\n\n"
               "Running it again for a ticket and part already bound here, while the\n"
               "ticket is assigned to you, prints that item rather than a second.\n\n"
               "Refuses when: no tracker is configured; --part or --title is invalid;\n"
               "the key does not exist; the ticket is resolved or assigned to somebody\n"
               "else; the claim transition name matches more than one transition; the\n"
               "claim transition is not offered and the ticket is not already yours;\n"
               "the ticket is bound here but not assigned to you (a linked ticket is\n"
               "never claimed by import); a tracker.yaml on an open item cannot be\n"
               "read; or the tracker does not show the claim afterwards.\n\n"
               "  tcw work tracker import EX-123\n"
               "  tcw work tracker import EX-123 --part api --title 'The API half'\n",
    )
    ptri.add_argument("ticket", help=TICKET_HELP)
    ptri.add_argument("--part", help="name one of several items for this ticket "
                                     "(lowercase letters, digits, hyphens; "
                                     "default: default)")
    ptri.add_argument("--title", help="the item's title (default: '<KEY> — <summary>')")
    ptri.set_defaults(func=_tracker_import)

    ptrl = ptrs.add_parser(
        "link", help="record that an existing item and a ticket are the same work",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description="Write down that a work item and a ticket are the same piece of work.\n\n"
                    "In the tracker: nothing. The ticket keeps its status and whoever holds\n"
                    "it, and it may be held by anyone. It is read — which is how a key that\n"
                    "does not exist is refused — and not written to.\n\n"
                    "In this node: the binding sidecar is the only file written, so the\n"
                    "item's status, owner, intake and request are left alone.",
        epilog="Any status can be linked, a finished item included. Where finished\n"
               "items' folders are gitignored (the default), that binding stays on\n"
               "this machine and is never committed. Nothing moves the ticket for you\n"
               "afterwards — do that in the tracker yourself.\n\n"
               "Use --part when one ticket is split across several items.\n\n"
               "Refuses when: no tracker is configured; --part is invalid; the slug\n"
               "is not an item here; the key does not exist; the item is already\n"
               "bound (unlink it first); another open item already holds this ticket\n"
               "and part; or a tracker.yaml on this item or any open item cannot be\n"
               "read.\n\n"
               "  tcw work tracker link 2026-09-14-rename-the-widget EX-123\n"
               "  tcw work tracker link 2026-09-14-rename-the-widget EX-123 --part api\n",
    )
    ptrl.add_argument("slug", help=BARE_SLUG_HELP)
    ptrl.add_argument("ticket", help=TICKET_HELP)
    ptrl.add_argument("--part", help="which of several items for this ticket "
                                     "(lowercase letters, digits, hyphens; "
                                     "default: default)")
    ptrl.set_defaults(func=_tracker_link)

    ptru = ptrs.add_parser(
        "unlink", help="remove an item's binding, keeping a record "
                       "of it; the ticket is not changed",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description="Remove an item's binding.\n\n"
                    "In the tracker: nothing. No call is made and none needs to be\n"
                    "configured, so a binding can be removed after work.tracker itself is\n"
                    "gone.\n\n"
                    "In this node: the sidecar is kept rather than deleted — what was\n"
                    "bound, when, and why it stopped move into its unlinked history.",
        epilog="Any status can be unlinked, a finished item included, so a wrong\n"
               "binding is repairable wherever it is found.\n\n"
               "Refuses when the slug is not an item here, when its tracker.yaml\n"
               "cannot be read, when it is not bound, or when --reason is blank.\n\n"
               "  tcw work tracker unlink 2026-09-14-rename-the-widget \\\n"
               "      --reason 'bound to the wrong ticket'\n",
    )
    ptru.add_argument("slug", help=BARE_SLUG_HELP)
    ptru.add_argument("--reason", required=True, help="why the binding is removed")
    ptru.set_defaults(func=_tracker_unlink)

    ptrsy = ptrs.add_parser(
        "sync", help="bring bound items' tickets to where the items' statuses say, "
                     "retrying what did not reach the tracker",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description="Retry what a lifecycle command could not send to the tracker.\n\n"
                    "In the tracker: for an item whose claim is still owed, claims the\n"
                    "ticket; otherwise moves the ticket to the status work.tracker.statuses\n"
                    "maps the item's status to — only when it is assigned to you and still\n"
                    "where the item left it. A ticket moved on by someone else is reported,\n"
                    "never moved back.\n\n"
                    "In this node: removes the item's sync record once its ticket is where\n"
                    "it should be, and updates it when not.",
        epilog="--all visits every item here with a sync record, finished ones the store\n"
               "still holds included. An item started by another identity (its owner is\n"
               "not TCW_WORK_OWNER or, without it, your Git identity) is skipped, because\n"
               "sync acts as whoever runs it. An item with no record is checked and never\n"
               "moved.\n\n"
               "Exits 1 while any item it acted on is pending or conflicting. Refuses when\n"
               "no tracker is configured, or the slug is not a bound item here.\n\n"
               "  tcw work tracker sync 2026-09-14-rename-the-widget\n"
               "  tcw work tracker sync --all\n",
    )
    ptrsy.add_argument("slug", nargs="?", help=BARE_SLUG_HELP)
    ptrsy.add_argument("--all", action="store_true",
                       help="every item here with a sync record")
    ptrsy.set_defaults(func=_tracker_sync)

    pts = g.add_parser(
        "tombstone",
        help="records of items this store resolved before it kept any")
    ptss = pts.add_subparsers(dest="tombstone_cmd", required=True)
    ptsa = ptss.add_parser(
        "add",
        help="record that a slug was a work item here, so references to it resolve")
    ptsa.add_argument("slug", help="the slug to record; an item this store no longer "
                                    "holds, not a current one")
    ptsa.add_argument("--resolution",
                      help="done|wontfix|duplicate|superseded; omit if unknown")
    ptsa.add_argument("--resolved", help="ISO date it was resolved (default: today)")
    ptsa.set_defaults(func=_tombstone_add)

    pn = g.add_parser("new", help="create a backlog item; prints its slug")
    pn.add_argument("title", help="the item's title")
    pn.add_argument("--priority", type=int, help="integer priority (higher = higher)")
    pn.add_argument("--effort", type=_work_level,
                    help="estimated effort: low|medium|high|very-high (or L/M/H/VH)")
    pn.add_argument("--complexity", type=_work_level,
                    help="estimated complexity: low|medium|high|very-high (or L/M/H/VH)")
    pn.add_argument("--blocked-by", action="append",
                    help="a slug or external text that blocks it (repeatable)")
    pn.add_argument("--tag", "--tags", action="extend", type=_tags,
                    help="apply a registered tag (repeatable; a value may be a,b,c)")
    pn.add_argument("--epic", action="store_true", help="mark as an epic (type: epic)")
    pn.add_argument("--parent", help="create as a child nested under this item's slug")
    pn.add_argument("--initiative", help="back-pointer slug to an owning epic")
    pn.set_defaults(func=_new)

    pl = g.add_parser("list", help="the board (hides completed + discarded unless --status/--all)")
    pl.add_argument("--status", choices=WORK_STATUSES)
    pl.add_argument("--tag", "--tags", action="extend", type=_tags,
                    help="only items carrying this tag (repeatable = match any; a value may be a,b,c)")
    pl.add_argument("--all", action="store_true", help="include completed and discarded items")
    pl.add_argument("-i", "--incl-desc", "--include-descendants",
                    dest="include_descendants", action="store_true",
                    help="also list every descendant work node's board, grouped by node")
    pl.set_defaults(func=_list)

    psh = g.add_parser("show", help="resolve slug → item; print state + body")
    psh.add_argument("slug", help=SLUG_HELP)
    psh.add_argument("--json", action="store_true",
                     help="emit the item as a versioned JSON document")
    psh.set_defaults(func=_show)

    pp = g.add_parser("path", help="print the work store or a work item folder path")
    pp.add_argument("slug", nargs="?",
                    help="optional; the item whose folder to print, else the store's")
    pp.set_defaults(func=_path)

    pst = g.add_parser("start", help="backlog → active")
    pst.add_argument("slug", help=SLUG_HELP)
    pst.add_argument("--force", action="store_true", help="start despite unresolved blockers")
    pst.add_argument("--owner", help="claimant identity (then TCW_WORK_OWNER, Git email/name)")
    pst.add_argument("--take-over", action="store_true", help="replace an existing active claim")
    pst.add_argument("--worktree", action="store_true",
                     help="isolate the item in its own git worktree + branch")
    pst.set_defaults(func=_start)

    psb = g.add_parser("submit", help="active → review (implemented, acceptance pending)")
    psb.add_argument("slug", help=SLUG_HELP)
    psb.set_defaults(func=_submit)

    prw = g.add_parser("rework", help="review → active (verification rejected the work)")
    prw.add_argument("slug", help=SLUG_HELP)
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
                        help="read a stage's instructions, or enter the stage")
    # The metavar is written out rather than left to argparse: the default would
    # list the hidden migration parsers below as if they were verbs, and setting
    # it to a bare "verb" would hide the real two from `--help` — which is also
    # where `tests/test_documented_cli_surface.py` discovers the CLI surface.
    stg = pstg.add_subparsers(dest="stage_verb", required=True,
                              metavar="{prompt,gate}")

    # Optional slug on both, required in the handlers: argparse cannot express
    # "required for six values of another positional, refused for the seventh".
    ppr = stg.add_parser("prompt",
                         help="print a stage's instructions, running no checks")
    ppr.add_argument("stage_id", metavar="stage",
                     help="a lifecycle stage id (`tcw work lifecycle` lists them)")
    ppr.add_argument("slug", nargs="?",
                     help="optional; without one the instructions resolve "
                          "generically, with one they resolve for that item")
    ppr.add_argument("--no-exec", action="store_true",
                     help="report what would resolve and resolve none of it; "
                          "prints nothing on stdout")
    ppr.set_defaults(func=_stage_prompt)

    pbg = stg.add_parser("gate",
                         help="check the stage is legal and run its checks; "
                              "prints no instructions")
    pbg.add_argument("stage_id", metavar="stage",
                     help="a lifecycle stage id (`tcw work lifecycle` lists them)")
    pbg.add_argument("slug", nargs="?",
                     help="the work item; omitted for `inbox`, which runs "
                          "before an item exists")
    pbg.add_argument("--no-exec", action="store_true",
                     help="report what would run and run none of it")
    pbg.set_defaults(func=_stage)

    # The removed form. Registered so it fails with the command to run instead
    # of argparse's bare "invalid choice", and hidden so it is not offered as a
    # third verb — from `--help` by the metavar above, and from the
    # invalid-choice error by `_HidesRemovedSpellings`, which is what makes that
    # claim true. It never resolves anything: a migration message, not an alias.
    for _sid in STAGE_IDS:
        # No `help=`: omitting it keeps the parser out of the choices list
        # entirely, where `help=SUPPRESS` would print a literal "==SUPPRESS==".
        pold = stg.add_parser(_sid)
        pold.add_argument("rest", nargs="*",
                          help="accepted and ignored; this spelling only reports the "
                               "command that replaced it")
        pold.add_argument("--no-exec", action="store_true",
                          help=argparse.SUPPRESS)
        pold.set_defaults(func=_stage_removed_form, removed_stage=_sid)

    pscf = g.add_parser("scaffold",
                        help="write a draft of a lifecycle artifact from its template")
    pscf.add_argument("artifact", help=f"one of: {', '.join(WORK_ARTIFACTS)}")
    pscf.add_argument("slug", help=SLUG_HELP)
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
    pe.add_argument("slug", help=SLUG_HELP)
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
    pe.add_argument("--tag", "--tags", action="extend", type=_tags,
                    help="apply a registered tag (repeatable; a value may be a,b,c)")
    pe.add_argument("--untag", "--untags", action="extend", type=_tags,
                    help="remove a tag (repeatable; a value may be a,b,c)")
    pe.set_defaults(func=_edit)

    pc = g.add_parser("complete", help="close an item: --resolution done → completed (DoD gate), anything else → discarded")
    pc.add_argument("slug", help=SLUG_HELP)
    pc.add_argument("--resolution", required=True, choices=sorted(WORK_RESOLUTIONS))
    pc.add_argument("--confirm", action="store_true")
    pc.add_argument("--force", action="store_true", help="complete despite unresolved blockers")
    pc.add_argument("--already-integrated", action="store_true",
                    help="the work branch was merged outside TCW (e.g. a merged PR): "
                         "skip the merge-back, keep every other gate")
    pc.set_defaults(func=_complete)

    pd = g.add_parser("drop", help="backlog → deleted")
    pd.add_argument("slug", help=SLUG_HELP)
    pd.add_argument("--confirm", action="store_true")
    pd.set_defaults(func=_drop)

    pdel = g.add_parser(
        "delete",
        help="finish removing a resolved item this project does not retain")
    pdel.add_argument("slug", help=SLUG_HELP)
    pdel.set_defaults(func=_delete)
