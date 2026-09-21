"""The cross-node recursion layer (work Spec 2).

Sits ABOVE the single-node WorkStore: per-node reads go through the abstract
store; node discovery + body/inbox writes are FS-flavored (spec §2). Ships the
FS realization only — a remote recursion layer would be additive.
"""

import re
from datetime import date
from pathlib import Path
from typing import NamedTuple

from tcw.store.base import (
    RESOLVED_STATUSES, RefError, SidecarError, WorkItem, declared_capabilities,
    topo_order,
)
from tcw.store.fs import (
    FsCapabilitiesStore, FsProjectRegistry, FsWorkStore, child_nodes,
    nearest_work_ancestor, parent_node, registered_parent,
    registered_project_id, slugify, unreachable_children, unreachable_parent,
    unreachable_project_note,
)

ROLLUP_RE = re.compile(r"<!-- tcw:rollup -->.*?<!-- /tcw:rollup -->", re.DOTALL)
ROLLUP_SIDECAR = "rollup.md"


def _open_ledger(node_root: Path) -> "tuple[FsCapabilitiesStore | None, str | None]":
    """This node's capabilities ledger: `(store, None)`, `(None, None)` when the
    node keeps none, or `(None, reason)` when it cannot be opened.

    Asked of the resolved store, the way `find_node` asks it, never of a literal
    `docs/capabilities` folder: a ledger moved by `capabilities.path` or kept in
    another repository by `capabilities.repository` is still a ledger. Every
    failure the store or the project registry reports while opening is a
    `ValueError` (`StoreNotProvisioned` and the rest), and becomes a reason
    rather than an exception, so a discard is never stopped by it."""
    try:
        store = FsCapabilitiesStore.open(node_root)
    except ValueError as e:
        return None, str(e)
    return (store, None) if store.root.is_dir() else (None, None)


def capability_gate(st: FsWorkStore, item: WorkItem) -> list[str]:
    """Check that `item`'s declared capability deltas were reconciled.

    Returns human-readable problems (empty = clean). A `new:` capability still
    reading Missing, or any declared path that doesn't resolve, is a problem; a
    `changed:` capability only fails if it no longer resolves. A `removed:`
    capability is the reverse: it fails while a local capability still resolves
    at that path.

    The sidecar is read first, so an item that declares nothing passes without
    any store being opened — a node with a broken capabilities declaration is
    not refused for an item that never mentions a capability. Once something is
    declared, a ledger that cannot be opened refuses every declared path with
    the store's own reason, as a problem line rather than an exception. Lives
    here (not in the abstract `WorkStore`) because it reaches into
    `FsCapabilitiesStore`; shared by the CLI `complete` path and
    `reconcile --complete-when-ready` so both enforce it."""
    try:
        deltas = declared_capabilities(item.capabilities)
    except SidecarError as e:
        return [f"capabilities.yaml is unreadable: {e}"]
    declared = [p for kind in ("new", "changed", "removed") for p in deltas[kind]]
    if not declared:
        return []
    own, reason = _open_ledger(st.node_root)
    if reason is None:
        try:
            registry = FsProjectRegistry.open(st.node_root).require_valid()
        except ValueError as e:
            reason = str(e)
    if reason is not None:
        return [f"{path}: {reason}" for path in declared]

    children: dict[str, "tuple[FsCapabilitiesStore | None, str | None]"] = {}

    def open_child(project_id: str) -> "FsCapabilitiesStore | str":
        if project_id not in children:
            project = registry.get(project_id)
            children[project_id] = (
                _open_ledger(Path(project.locator)) if project is not None
                else (None, unreachable_project_note(registry, project_id)
                      or f"project '{project_id}' is declared but not "
                         f"reachable in this checkout"))
        store, why = children[project_id]
        if why is not None:
            return why
        return store if store is not None else \
            f"project '{project_id}' keeps no capabilities ledger"

    problems: list[str] = []

    def check(kind: str, path: str) -> None:
        route = route_capability_path(path, own=own, registry=registry,
                                      node_id=registry.current.id,
                                      open_child=open_child)
        if isinstance(route, str):
            problems.append(route)
            return
        where = "" if route.owner is None else f" in project '{route.owner}'"
        if kind == "removed":
            # Local only: `rm` deletes only local capabilities, and once a local
            # one is gone its bare path may fall through to an inherited
            # capability at the same path, which `rm` refuses — a dead end if
            # that counted.
            if route.store.get_local(route.path) is not None:
                problems.append(f"{path}: declared (removed) but still resolves{where} "
                                f"(delete it with `tcw capabilities rm`)")
            return
        try:
            cap = route.store.get(route.path)
        except RefError as e:                              # ambiguous bare ref, etc.
            problems.append(f"{path}: {e}")
            return
        if cap is None:
            problems.append(f"{path}: declared ({kind}) but does not resolve{where}")
        elif kind == "new" and cap.status == "Missing":
            problems.append(f"{path}: still Missing{where} "
                            f"(declared new; flip it or mark Omitted)")

    for kind in ("new", "changed", "removed"):
        for path in deltas[kind]:
            check(kind, path)
    return problems


class Route(NamedTuple):
    """Which ledger answers for a declared capability path, and the path
    within it. `owner` is the child project's id, or None for the item's own
    node."""
    owner: str | None
    store: FsCapabilitiesStore
    path: str


def route_capability_path(path: str, *, own: "FsCapabilitiesStore | None",
                          registry, node_id: str,
                          open_child) -> "Route | str":
    """Route one declared `capabilities.yaml` path to the ledger that answers
    for it, or return a problem line.

    The one place this rule lives. `own` is the item's node's ledger (None when
    the node keeps none); `open_child(project_id)` returns a child's ledger or
    the reason it has none. In order:

    1. A first segment naming a project `own` extends is today's inheritance
       reading, even when that project is also a declared child — every
       existing sidecar keeps its meaning.
    2. A first segment naming a declared child (reachable here or not) routes
       the rest of the path to that child's own ledger, read the way the child
       reads it.
    3. Anything else is the node's own path; with no ledger of its own, nothing
       can check it.

    Uses only the registry's declared children and the stores it is handed, so
    a non-filesystem store could answer every question it asks."""
    head, _, rest = path.partition("/")
    if own is not None and head in own.extends:
        return Route(None, own, path)
    child_ids = registry.declared_child_ids()
    if head in child_ids:
        if not rest:
            return f"{path}: names project '{head}' but no capability"
        store = open_child(head)
        if isinstance(store, str):
            return f"{path}: {store}"
        return Route(head, store, rest)
    if own is not None:
        return Route(None, own, path)
    qualifiers = ", ".join(child_ids) or "it declares no child projects"
    return (f"{path}: this node ('{node_id}') keeps no capabilities ledger; "
            f"qualify the path with a child project id ({qualifiers})")


# ── reconcile ────────────────────────────────────────────────────────────────

def _tasks_for(node_root: Path, epic_slug: str) -> list[tuple[str, WorkItem]]:
    """(node-relative-path, item) for every item with initiative == epic_slug,
    across this node + its child nodes. Slugs collide across nodes, so the node
    path keys the rows."""
    node_root = node_root.resolve()
    out: list[tuple[str, WorkItem]] = []
    for r in [node_root, *child_nodes(node_root)]:
        rel = "." if r.resolve() == node_root else registered_project_id(node_root, r)
        for item in FsWorkStore.open(r).query():
            if item.initiative == epic_slug:
                out.append((rel, item))
    return out


def _blocker_labels(item: WorkItem) -> str:
    labels = [b.get("slug") or f"external: {b.get('external')}" for b in item.blocked_by]
    return ", ".join(labels) if labels else "-"


def _capability_deltas(tasks: list[tuple[str, WorkItem]]) -> list[str]:
    """Read-only surface of each task's capabilities.yaml.

    `declared_capabilities` is the ONLY reader of the canonical
    `new:`/`changed:`/`removed:` mapping here — the same one `capability_gate` uses, so the rollup and the gate
    cannot disagree about a sidecar again. They differ only in how they fail: the
    gate lets SidecarError propagate and fails closed, while this is a display
    surface spanning a whole epic, so one child node's broken sidecar degrades to
    a row instead of taking the rollup down (the _safe_yaml degrade-don't-crash
    idiom).

    The older reconcile-display list of {file, heading, from, to} mappings stays
    as a fallback. No sidecar in this repo still uses it, but `_tasks_for` reads
    items out of child nodes — separate repositories this one cannot inspect — so
    "no producer here" is not evidence of "no producer".
    """
    out: list[str] = []
    for rel, item in tasks:
        caps = item.capabilities
        try:
            deltas = declared_capabilities(caps)
        except SidecarError as e:
            out.append(f"- {rel}/{item.slug}: capabilities.yaml is unreadable: {e} — skipped")
            continue
        if any(deltas.values()):
            for kind in ("new", "changed", "removed"):
                for path in deltas[kind]:
                    out.append(f"- {rel}/{item.slug}: {kind} {path}")
        elif isinstance(caps, list):
            for e in caps:
                if isinstance(e, dict) and e.get("file"):
                    out.append(f"- {rel}/{item.slug}: {e.get('file')}#{e.get('heading', '')} "
                               f"{e.get('from', '?')} → {e.get('to', '?')}")
        elif caps:
            out.append(f"- {rel}/{item.slug}: "
                       f"capabilities.yaml has no new:/changed:/removed: entries — skipped")
    return out


def _ready(tasks: list[tuple[str, WorkItem]]) -> list[str]:
    # "Resolved", not "shipped": a discarded task is done being worked on, so it
    # neither needs doing nor holds back anything blocked on it.
    unresolved = {item.slug for _, item in tasks
                  if item.status not in RESOLVED_STATUSES}
    ready: list[str] = []
    for _rel, item in tasks:
        if item.status in RESOLVED_STATUSES:
            continue
        blocked = any(b.get("slug") in unresolved or "external" in b for b in item.blocked_by)
        if not blocked:
            ready.append(item.slug)
    return ready


def _render(epic_slug: str, tasks: list[tuple[str, WorkItem]],
            completable: bool = False) -> str:
    lines = ["<!-- tcw:rollup -->", f"### Rollup: {epic_slug}", ""]
    if not tasks:
        lines.append("_No tasks reference this initiative yet._")
    else:
        lines += ["| node | slug | status | blocked-by |", "|---|---|---|---|"]
        by_node: dict[str, list[WorkItem]] = {}
        for rel, item in tasks:
            by_node.setdefault(rel, []).append(item)
        for rel in sorted(by_node):                       # deterministic: node, then topo
            for item in topo_order(by_node[rel]):
                lines.append(f"| {rel} | {item.slug} | {item.status} | "
                             f"{_blocker_labels(item)} |")
        deltas = _capability_deltas(tasks)
        if deltas:
            lines += ["", "**Capability deltas:**", *deltas]
        if completable:
            lines += ["", f"**Ready to close:** all {len(tasks)} children resolved — "
                      f"run `tcw work complete {epic_slug} --resolution done --confirm`"]
        else:
            ready = _ready(tasks)
            lines += ["", "**Next:** " + (", ".join(ready) if ready else "all blocked or complete")]
    lines.append("<!-- /tcw:rollup -->")
    return "\n".join(lines)


def _evict_legacy_rollup(store: FsWorkStore, slug: str) -> None:
    """Strip a rollup block that an older release wrote into the request.

    Reconciling is not the `request` stage, so writing the block there created an
    `initial-request.md` nobody had written and lit `R` on the board for it. What
    a human wrote above the block is kept; a request that held nothing else is
    removed rather than left as an empty husk that still reads as a document.

    Goes through the artifact surface, so an adapter that never had the old
    layout simply finds nothing to strip.
    """
    request = store.read_artifact(slug, "initial-request")
    if request is None or not ROLLUP_RE.search(request.content):
        return
    remainder = ROLLUP_RE.sub("", request.content).strip()
    if remainder:
        store.write_artifact(slug, "initial-request", f"{remainder}\n")
    else:
        store.delete_artifact(slug, "initial-request")


def reconcile(node_root: Path, epic_slug: str, commit: bool = False,
              complete_when_ready: bool = False) -> str:
    """Scan children for `initiative == epic_slug`; write a consolidated rollup
    to the epic's `rollup.md` sidecar. Read-only on capabilities.

    When the epic's children are all resolved the rollup flags it "Ready to close";
    with `complete_when_ready` the epic is then auto-completed (the DoD/capability
    gates still run, so it can't skip a declared-Missing capability)."""
    from tcw.store.fs import git_commit_result
    store = FsWorkStore.open(node_root)
    epic = store.get(epic_slug)
    if epic is None:
        raise ValueError(f"no such epic: {epic_slug}")

    # Decide (and effect) auto-completion first, gate-guarded, so the rollup we
    # persist reflects the final state — a completed epic must not keep a stale
    # "Ready to close" instruction in its rollup.
    auto_completed = False
    if complete_when_ready and store.epic_completable(epic):
        problems = capability_gate(store, epic)               # same gate as CLI complete
        if problems:
            raise ValueError("declared capabilities not reconciled: "
                             + "; ".join(problems)
                             + " (reconcile them, or complete manually with --force)")
        store.complete(epic_slug, "done", store.dod_checklist())   # moves backlog→completed
        auto_completed = True

    completable = store.epic_completable(store.get(epic_slug))     # False once completed
    block = _render(epic_slug, _tasks_for(node_root, epic_slug), completable=completable)
    _evict_legacy_rollup(store, epic_slug)
    current = store.read_sidecar(epic_slug, ROLLUP_SIDECAR)
    text = f"{block}\n"
    changed = current is None or current.content != text
    if changed:                                # idempotent: don't stage an unchanged
        store.write_sidecar(epic_slug, ROLLUP_SIDECAR, text)   # rollup (an empty
                                               # commit would fail). write_sidecar
                                               # writes atomically and stages into
                                               # the store's repo, not the code node's.
    # No `changed or auto_completed` guard: that guard existed only to avoid an
    # empty commit, which used to *fail*. `git_commit_result` answers "nothing to
    # commit" benignly, and the guard actively broke recovery — after a refused
    # commit the rollup is already correct on disk, so a retry computed
    # `changed=False`, skipped the commit, and exited 0 with the change still
    # sitting staged. Reporting success for an uncommitted rollup is the one
    # thing this must never do.
    if commit:
        msg = f"auto-complete {epic_slug}" if auto_completed else f"reconcile {epic_slug}"
        work_pathspec = str(store.root.relative_to(store.store_git_root))
        # `git_commit_result`, like every other commit path in the codebase: it
        # separates a benign non-commit from a real refusal instead of raising
        # `CalledProcessError`, which is not in the CLI's `_ERRORS` and so
        # escaped as a traceback. The message says the rollup was *staged*,
        # because it was — written and staged above, before the commit was
        # attempted — so the user knows the change is in their index rather than
        # lost, and that re-running is the recovery.
        err = git_commit_result(store.store_git_root, f"tcw work: {msg}", work_pathspec)
        if err:
            raise ValueError(f"reconciled {epic_slug} and staged the rollup, but "
                             f"committing it failed:\n{err}")
    if auto_completed:
        block += f"\n\nAuto-completed {epic_slug} (all children resolved)."
    return block


# ── inbox channel ────────────────────────────────────────────────────────────

def _inbox_write(store: FsWorkStore, title: str, body: str, origin: str,
                 initiative: str | None) -> Path:
    """Write one request into `store`'s inbox. Bounded on purpose: it may restore
    a missing `inbox` leaf inside a store that already exists, but it must never
    manufacture the store root — that turns a misrouted request into a silent
    success in a directory nobody reads."""
    if not store.root.is_dir():
        raise ValueError(f"work store root does not exist: {store.root}")
    # The one write in the adapter that never stages, so it is also the one the
    # `_stage` guard cannot reach. Left unguarded it "succeeds" outside a
    # repository by dropping an untracked note into a store whose own
    # `inbox accept` will refuse it — a request that can never become work.
    # Checked against the *destination* store, which for `delegate` is the
    # child's repository and for `escalate` the parent's.
    store._require_repository()
    inbox = store.root / "inbox"
    inbox.mkdir(exist_ok=True)
    base = f"{date.today().isoformat()}-{slugify(title)}"
    name, n = base, 2
    while (inbox / f"{name}.md").exists():
        name, n = f"{base}-{n}", n + 1
    front = [f"from: {origin}"] + ([f"initiative: {initiative}"] if initiative else [])
    doc = inbox / f"{name}.md"
    doc.write_text("---\n" + "\n".join(front) + "\n---\n\n"
                   f"# {title}\n\n{body}\n", encoding="utf-8")
    return doc


def delegate(node_root: Path, child_ref: str, title: str, body: str = "",
             initiative: str | None = None) -> Path:
    """Write a request DOWN into a child node's inbox/ (boundary: inbox only)."""
    node_root = node_root.resolve()
    children = {registered_project_id(node_root, c): c for c in child_nodes(node_root)}
    if child_ref not in children:
        # A child declared here and not present is not "no such child". Saying so
        # sends the reader to add a declaration that is already in their config.
        registry = FsProjectRegistry.open(node_root).require_valid()
        if any(entry.id == child_ref for entry in unreachable_children(node_root)):
            raise ValueError(
                f"cannot delegate to '{child_ref}': "
                + (unreachable_project_note(registry, child_ref) or
                   f"project '{child_ref}' is declared but not reachable here"))
        raise ValueError(f"no child node '{child_ref}'. children: "
                         f"{', '.join(sorted(children)) or '(none)'}")
    origin = registered_project_id(node_root, node_root)
    return _inbox_write(FsWorkStore.open(children[child_ref]),
                        title, body, origin=origin, initiative=initiative)


def escalate(node_root: Path, title: str, body: str = "",
             initiative: str | None = None) -> Path:
    """Write a request UP into the parent node's inbox/ (boundary: inbox only)."""
    parent = nearest_work_ancestor(node_root)
    if parent is None:
        # Two different situations, and telling a user the node is the root when
        # it plainly has a parent sends them to fix the wrong thing.
        registered = registered_parent(node_root)
        if registered is not None:
            raise ValueError(
                "no parent node to escalate to: no registered ancestor keeps a "
                "work store")
        if (absent := unreachable_parent(node_root)) is not None:
            # A third situation, and the one that read as "this is the root" for
            # a config that names a parent outright: the parent is declared and
            # this checkout does not have it. That has a remedy, so the message
            # is the one that names it.
            registry = FsProjectRegistry.open(node_root).require_valid()
            raise ValueError(
                "no parent node to escalate to: "
                + (unreachable_project_note(registry, absent.id) or
                   f"project '{absent.id}' is declared but not reachable here"))
        raise ValueError("no parent node to escalate to (this is the root)")
    origin = registered_project_id(node_root, node_root)
    return _inbox_write(FsWorkStore.open(parent), title, body, origin, initiative)
