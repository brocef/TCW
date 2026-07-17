"""The cross-node recursion layer (work Spec 2).

Sits ABOVE the single-node WorkStore: per-node reads go through the abstract
store; node discovery + body/inbox writes are FS-flavored (spec §2). Ships the
FS realization only — a remote recursion layer would be additive.
"""

import re
from datetime import date
from pathlib import Path

from tcw.store.base import WorkItem, topo_order
from tcw.store.fs import (
    FsWorkStore, child_nodes, git_stage, parent_node, slugify,
)

ROLLUP_RE = re.compile(r"<!-- tcw:rollup -->.*?<!-- /tcw:rollup -->", re.DOTALL)


# ── reconcile ────────────────────────────────────────────────────────────────

def _tasks_for(node_root: Path, epic_slug: str) -> list[tuple[str, WorkItem]]:
    """(node-relative-path, item) for every item with initiative == epic_slug,
    across this node + its child nodes. Slugs collide across nodes, so the node
    path keys the rows."""
    node_root = node_root.resolve()
    out: list[tuple[str, WorkItem]] = []
    for r in [node_root, *child_nodes(node_root)]:
        rel = "." if r.resolve() == node_root else str(r.resolve().relative_to(node_root))
        for item in FsWorkStore.open(r).query():
            if item.initiative == epic_slug:
                out.append((rel, item))
    return out


def _blocker_labels(item: WorkItem) -> str:
    labels = [b.get("slug") or f"external: {b.get('external')}" for b in item.blocked_by]
    return ", ".join(labels) if labels else "-"


def _capability_deltas(tasks: list[tuple[str, WorkItem]]) -> list[str]:
    """Read-only surface of each task's capabilities.yaml. Expects an optional
    top-level list of {file, heading, from, to} mappings; tolerantly notes
    anything else (the _safe_yaml degrade-don't-crash idiom)."""
    out: list[str] = []
    for rel, item in tasks:
        caps = item.capabilities
        if isinstance(caps, list):
            for e in caps:
                if isinstance(e, dict) and e.get("file"):
                    out.append(f"- {rel}/{item.slug}: {e.get('file')}#{e.get('heading', '')} "
                               f"{e.get('from', '?')} → {e.get('to', '?')}")
        elif caps:
            out.append(f"- {rel}/{item.slug}: capabilities.yaml present but not a list — skipped")
    return out


def _ready(tasks: list[tuple[str, WorkItem]]) -> list[str]:
    incomplete = {item.slug for _, item in tasks if item.status != "completed"}
    ready: list[str] = []
    for _rel, item in tasks:
        if item.status == "completed":
            continue
        blocked = any(b.get("slug") in incomplete or "external" in b for b in item.blocked_by)
        if not blocked:
            ready.append(item.slug)
    return ready


def _render(epic_slug: str, tasks: list[tuple[str, WorkItem]],
            completable: bool = False) -> str:
    lines = ["<!-- tcw:rollup -->", f"### Rollup: {epic_slug}", ""]
    if not tasks:
        lines.append("_No tasks reference this initiative yet._")
    else:
        lines += ["| node | slug | status | phase | blocked-by |", "|---|---|---|---|---|"]
        by_node: dict[str, list[WorkItem]] = {}
        for rel, item in tasks:
            by_node.setdefault(rel, []).append(item)
        for rel in sorted(by_node):                       # deterministic: node, then topo
            for item in topo_order(by_node[rel]):
                lines.append(f"| {rel} | {item.slug} | {item.status} | "
                             f"{item.phase or '-'} | {_blocker_labels(item)} |")
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


def reconcile(node_root: Path, epic_slug: str, commit: bool = False,
              complete_when_ready: bool = False) -> str:
    """Scan children for `initiative == epic_slug`; write a consolidated rollup
    into the epic's initial-request.md managed block. Read-only on capabilities.

    When the epic's children are all resolved the rollup flags it "Ready to close";
    with `complete_when_ready` the epic is then auto-completed (the DoD/capability
    gates still run, so it can't skip a declared-Missing capability)."""
    store = FsWorkStore.open(node_root)
    epic = store.get(epic_slug)
    if epic is None:
        raise ValueError(f"no such epic: {epic_slug}")
    completable = store.epic_completable(epic)
    block = _render(epic_slug, _tasks_for(node_root, epic_slug), completable=completable)
    content = store.path(epic_slug) / "initial-request.md"
    original = content.read_text(encoding="utf-8") if content.exists() else ""
    text = ROLLUP_RE.sub(block, original) if ROLLUP_RE.search(original) \
        else f"{original.rstrip()}\n\n{block}\n"
    from tcw.store.fs import git_commit
    if text != original:                       # idempotent at the git level too:
        content.write_text(text, encoding="utf-8")   # don't stage/commit an
        git_stage(node_root, content)                # unchanged rollup (an empty
        if commit:                                   # commit would fail)
            git_commit(node_root, f"tcw work: reconcile {epic_slug}", "docs/work")
    if complete_when_ready and completable:
        store.complete(epic_slug, "done", store.dod_checklist())
        block += f"\n\nAuto-completed {epic_slug} (all children resolved)."
        if commit:
            git_commit(node_root, f"tcw work: auto-complete {epic_slug}", "docs/work")
    return block


# ── inbox channel ────────────────────────────────────────────────────────────

def _inbox_write(inbox: Path, title: str, body: str, origin: str,
                 initiative: str | None) -> Path:
    inbox.mkdir(parents=True, exist_ok=True)
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
    children = {str(c.resolve().relative_to(node_root)): c for c in child_nodes(node_root)}
    if child_ref not in children:
        raise ValueError(f"no child node '{child_ref}'. children: "
                         f"{', '.join(sorted(children)) or '(none)'}")
    return _inbox_write(children[child_ref] / "docs" / "work" / "inbox",
                        title, body, origin=".", initiative=initiative)


def escalate(node_root: Path, title: str, body: str = "",
             initiative: str | None = None) -> Path:
    """Write a request UP into the parent node's inbox/ (boundary: inbox only)."""
    parent = parent_node(node_root)
    if parent is None:
        raise ValueError("no parent node to escalate to (this is the root)")
    origin = str(node_root.resolve().relative_to(parent.resolve()))
    return _inbox_write(parent / "docs" / "work" / "inbox", title, body, origin, initiative)
