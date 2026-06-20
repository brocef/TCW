# Cross-node recursion (work Spec 2) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add the cross-node recursion layer on top of the shipped single-node `tcw work` core — node topology, epics + `initiative:` back-pointers, `reconcile`, the escalate/delegate inbox channel, and `tcw work start --worktree`.

**Architecture:** The single-node `WorkStore` ABC stays untouched. Cross-node is a **layer above it** (`tcw/work/recursion.py`) that reads each node through the abstract store and does FS-flavored node discovery + body/worktree writes. Node topology lives in `tcw/store/fs.py` beside `find_node`. See the spec (`spec.md`, same folder) for the full rationale.

**Tech Stack:** Python 3 (stdlib `argparse`, `subprocess`, `pathlib`, `re`) + PyYAML + git/`git worktree` via subprocess. Tests: pytest over `tmp_path` git repos.

## Global Constraints

- **Litmus test (prime directive):** never add a method to `WorkStore` that only the FS adapter could honor. reconcile/delegate/worktrees stay in the recursion layer or fs.py, not the ABC.
- **Stage-only default** for transitions, EXCEPT `start --worktree`, which must commit (a `git worktree add` needs a commit to branch from). Scope every commit with an explicit pathspec (`-- docs/work .gitignore`) so it never sweeps unrelated staged changes.
- **Mechanism only** — no judgment (when to decompose/escalate, ledger flips, canonical wording). reconcile is **read-only** on capabilities.
- **Single-owner invariant:** after `start --worktree`, the item's `state.yaml` is owned by the work branch until merge-back; trunk does no `set_field` on it until post-merge `complete`.
- Slugs are minted per-node and collide across nodes — key all cross-node rows by **(node-relative-path, slug)**.
- Python with type hints; follow existing fs.py/cli.py idioms (`_split`, `_ERRORS`, `git_*` helpers, `_safe_yaml` tolerant degradation).

---

## File Structure

- `tcw/store/fs.py` — **modify**: add `_git_common_dir`, `child_nodes`, `parent_node` (node topology); `WORKTREES_DIR`, `git_commit`, `ensure_worktree_ignored`, `add_worktree`, `remove_worktree` (worktree plumbing).
- `tcw/store/base.py` — **modify**: add `initiative`, `type`, `worktree`, `branch` fields to `WorkItem`.
- `tcw/work/recursion.py` — **create**: `reconcile`, `delegate`, `escalate` + private renderers.
- `tcw/work/cli.py` — **modify**: new subcommands `nodes`/`reconcile`/`delegate`/`escalate`; flags `new --epic/--initiative`, `edit --initiative`, `start --worktree`; complete teardown; extend `SUBCOMMANDS`.
- `tests/test_recursion.py` — **create**: all cross-node tests.
- Docs — **modify**: `README.md`, `docs/release-notes/upcoming.md`, `docs/changelogs/upcoming.md`, `docs/plan/phase-6-beyond.md`, `docs/plan/phase-5-work.md`.

**Test helper** (top of `tests/test_recursion.py`):

```python
import subprocess
from pathlib import Path

import pytest

# Imports grow per task — start with Task 1's, add each task's symbols when you
# write that task's test. This keeps every per-task pytest checkpoint runnable:
# its failure is the expected "cannot import name <this task's symbol>", not a
# collection error from a not-yet-built later task. Add as you go:
#   Task 3: from tcw.work.recursion import reconcile
#   Task 4: from tcw.work.recursion import delegate, escalate, reconcile
#   Task 5: from tcw.store.fs import (add_worktree, ensure_worktree_ignored,
#                                     git_commit, remove_worktree)
from tcw.store.fs import FsWorkStore, child_nodes, init, parent_node


def mk_node(base: Path, name: str) -> Path:
    """A git repo with docs/work/ initialized, at base/name."""
    root = base / name
    root.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init", "-q", "--initial-branch=main", str(root)], check=True)
    subprocess.run(["git", "-C", str(root), "config", "user.email", "t@t"], check=True)
    subprocess.run(["git", "-C", str(root), "config", "user.name", "t"], check=True)
    init(["work"], root)
    return root


def commit_all(root: Path, msg: str = "init") -> None:
    subprocess.run(["git", "-C", str(root), "add", "-A"], check=True)
    subprocess.run(["git", "-C", str(root), "commit", "-q", "-m", msg], check=True)
```

---

## Task 1: Node topology (`child_nodes` / `parent_node` + `tcw work nodes`)

**Files:**
- Modify: `tcw/store/fs.py` (after `find_node`, ~line 57)
- Modify: `tcw/work/cli.py` (`SUBCOMMANDS`, new `_nodes`, subparser)
- Test: `tests/test_recursion.py`

**Interfaces:**
- Produces: `child_nodes(root: Path) -> list[Path]` (resolved absolute paths), `parent_node(root: Path) -> Path | None`.

- [ ] **Step 1: Write the failing test**

```python
def test_child_nodes_finds_children_excludes_own_worktree_keeps_nested_repo(tmp_path):
    parent = mk_node(tmp_path, "parent")
    subprocess.run(["git", "-C", str(parent), "add", "docs"], check=True)   # commit parent's
    subprocess.run(["git", "-C", str(parent), "commit", "-qm", "init"], check=True)  # OWN files
    child = mk_node(parent, "child")                       # direct child node
    deep = mk_node(parent / "group", "deep")              # under a non-node folder
    plain_repo = parent / "lib"                            # a git repo WITHOUT docs/work
    plain_repo.mkdir()
    subprocess.run(["git", "init", "-q", str(plain_repo)], check=True)
    # NB: never `git add -A` the parent now — it holds uncommitted nested repos
    # (child/deep/lib) and git would abort ("does not have a commit checked out").
    subprocess.run(["git", "-C", str(parent), "worktree", "add", "-q",
                    "-b", "work/x", str(parent / ".worktrees" / "x")], check=True)

    found = {p.resolve() for p in child_nodes(parent)}
    assert child.resolve() in found
    assert deep.resolve() in found                         # skips intermediate non-node folder
    assert (parent / ".worktrees" / "x").resolve() not in found   # own worktree excluded
    assert plain_repo.resolve() not in found               # repo without docs/work is not a node


def test_parent_node(tmp_path):
    parent = mk_node(tmp_path, "parent")
    child = mk_node(parent, "child")
    assert parent_node(child).resolve() == parent.resolve()
    assert parent_node(parent) is None                     # root has no parent node
```

- [ ] **Step 2: Run to verify it fails**

Run: `python -m pytest tests/test_recursion.py -k "child_nodes or parent_node" -v`
Expected: FAIL — `ImportError: cannot import name 'child_nodes'`.

- [ ] **Step 3: Implement in `tcw/store/fs.py`** (insert after `find_node`)

```python
def _git_common_dir(path: Path) -> Path | None:
    """Absolute shared `.git` dir for the repo containing `path` (None if outside
    a work-tree). A linked worktree resolves to its MAIN repo's `.git`; a
    standalone repo resolves to its own — the basis for excluding own worktrees.
    --path-format=absolute is required: the default is cwd-relative and would
    mis-compare (spec §3.1)."""
    try:
        out = subprocess.run(
            ["git", "-C", str(path), "rev-parse", "--path-format=absolute",
             "--git-common-dir"],
            capture_output=True, text=True, check=True,
        ).stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None
    return Path(out).resolve()


def child_nodes(root: Path) -> list[Path]:
    """Nearest descendant nodes (git work-tree + docs/work/) under `root`.

    Descent stops at each found node (its children are its own — A.2). Excludes
    `root`'s own linked worktrees: a candidate whose git-common-dir equals
    `root`'s is the same logical node, not a child. FS-adapter-local.
    ponytail: shells out per dir and walks the whole tree — fine for a docs
    repo; prune by .gitignore only if it ever bites.
    """
    root = root.resolve()
    own_common = _git_common_dir(root)
    found: list[Path] = []

    def walk(d: Path) -> None:
        for child in sorted(p for p in d.iterdir() if p.is_dir() and p.name != ".git"):
            top = git_root(child)
            is_node = (top is not None and top.resolve() == child.resolve()
                       and (child / "docs" / "work").is_dir())
            if is_node and _git_common_dir(child) != own_common:
                found.append(child)        # genuine child node — don't descend
            else:
                walk(child)                # plain subdir or our own worktree
    walk(root)
    return found


def parent_node(root: Path) -> Path | None:
    """Nearest ancestor node above `root`, or None. FS-adapter-local."""
    root = root.resolve()
    search = git_root(root.parent)
    while search is not None:
        search = search.resolve()
        if search != root and (search / "docs" / "work").is_dir():
            return search
        nxt = git_root(search.parent)      # climb above this enclosing repo
        if nxt is None or nxt.resolve() == search:
            return None
        search = nxt
    return None
```

- [ ] **Step 4: Add the `nodes` CLI command in `tcw/work/cli.py`**

Extend the import from `tcw.store.fs` to include `child_nodes, parent_node`. Add `"nodes"` to `SUBCOMMANDS`. Add:

```python
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
```

In `add_subparser`, register it:

```python
    g.add_parser("nodes", help="list this node's parent + child nodes").set_defaults(func=_nodes)
```

- [ ] **Step 5: Run to verify it passes**

Run: `python -m pytest tests/test_recursion.py -k "child_nodes or parent_node" -v`
Expected: PASS (2 tests).

- [ ] **Step 6: Commit**

```bash
git add tcw/store/fs.py tcw/work/cli.py tests/test_recursion.py
git commit -m "feat(work): node topology (child_nodes/parent_node) + tcw work nodes"
```

---

## Task 2: Epic / initiative fields + `new`/`edit` flags

**Files:**
- Modify: `tcw/store/base.py` (`WorkItem` dataclass, ~line 176)
- Modify: `tcw/store/fs.py` (`FsWorkStore.get`, ~line 587)
- Modify: `tcw/work/cli.py` (`_new`, `_edit`, subparsers)
- Test: `tests/test_recursion.py`

**Interfaces:**
- Produces: `WorkItem.initiative: str`, `WorkItem.type: str`, `WorkItem.worktree: str`, `WorkItem.branch: str` (all default `""`); CLI flags `new --epic`, `new --initiative <slug>`, `edit --initiative <slug|"">`.

- [ ] **Step 1: Write the failing test**

```python
def test_new_epic_and_initiative_fields(tmp_path, monkeypatch, capsys):
    root = mk_node(tmp_path, "repo")
    monkeypatch.chdir(root)
    from tcw.cli import main
    assert main(["work", "new", "Build it", "--epic", "--initiative", "2026-01-01-epic"]) == 0
    slug = capsys.readouterr().out.strip()
    item = FsWorkStore.open(root).get(slug)
    assert item.type == "epic"
    assert item.initiative == "2026-01-01-epic"


def test_edit_sets_and_clears_initiative(tmp_path):
    st = FsWorkStore.open(mk_node(tmp_path, "repo"))
    item = st.create("Task", created="2026-01-01")
    st.set_field(item.slug, "initiative", "2026-01-01-epic")
    assert st.get(item.slug).initiative == "2026-01-01-epic"
    st.set_field(item.slug, "initiative", "")
    assert st.get(item.slug).initiative == ""
```

- [ ] **Step 2: Run to verify it fails**

Run: `python -m pytest tests/test_recursion.py -k "epic_and_initiative or clears_initiative" -v`
Expected: FAIL — `AttributeError: 'WorkItem' object has no attribute 'type'` / unrecognized arg `--epic`.

- [ ] **Step 3: Add fields to `WorkItem` in `tcw/store/base.py`**

```python
@dataclass
class WorkItem:
    """A unit of work; status is *where it lives*, not a stored field (A.3)."""
    slug: str
    title: str
    status: str
    phase: str = ""
    created: str = ""
    resolution: str | None = None
    body: str = ""
    blocked_by: list[dict] = field(default_factory=list)
    capabilities: object = None     # opaque blob in Spec 1 (B.4)
    initiative: str = ""            # cross-node back-pointer to an epic (Spec 2)
    type: str = ""                  # optional recursion sugar; only value: "epic"
    worktree: str = ""             # node-relative worktree path (start --worktree)
    branch: str = ""               # work branch name (start --worktree)
```

- [ ] **Step 4: Populate them in `FsWorkStore.get` (`tcw/store/fs.py`)**

In the `return WorkItem(...)` block, add after `capabilities=...`:

```python
            initiative=state.get("initiative", ""),
            type=state.get("type", ""),
            worktree=state.get("worktree", ""),
            branch=state.get("branch", ""),
```

- [ ] **Step 5: Wire the CLI flags in `tcw/work/cli.py`**

In `_new`, after the blocker loop and before `print(item.slug)`:

```python
    if args.epic:
        st.set_field(item.slug, "type", "epic")
    if args.initiative:
        st.set_field(item.slug, "initiative", args.initiative)
```

In `_edit`, inside the `try` block (before the success print), add:

```python
        if args.initiative is not None:
            st.set_field(args.slug, "initiative", args.initiative)
```

In `add_subparser`, extend the `new` and `edit` parsers:

```python
    pn.add_argument("--epic", action="store_true", help="mark as an epic (type: epic)")
    pn.add_argument("--initiative", help="back-pointer slug to an owning epic")
    # ...
    pe.add_argument("--initiative", help='set the owning-epic back-pointer (use "" to clear)')
```

- [ ] **Step 6: Run to verify it passes**

Run: `python -m pytest tests/test_recursion.py -k "epic_and_initiative or clears_initiative" -v`
Expected: PASS (2 tests).

- [ ] **Step 7: Commit**

```bash
git add tcw/store/base.py tcw/store/fs.py tcw/work/cli.py tests/test_recursion.py
git commit -m "feat(work): initiative/type/worktree/branch fields + new/edit flags"
```

---

## Task 3: `reconcile` (cross-node rollup)

**Files:**
- Create: `tcw/work/recursion.py`
- Modify: `tcw/work/cli.py` (`_reconcile`, subparser, `SUBCOMMANDS`)
- Test: `tests/test_recursion.py`

**Interfaces:**
- Consumes: `child_nodes`, `parent_node` (Task 1); `WorkItem.initiative` (Task 2); `FsWorkStore.open/query/get/path`; `topo_order`; `git_stage`, `slugify`.
- Produces: `reconcile(node_root: Path, epic_slug: str, commit: bool = False) -> str` (returns the rendered block; raises `ValueError` on unknown epic).

- [ ] **Step 1: Write the failing test**

```python
def _child_task(child, initiative, title="Slice", caps=None):
    s = FsWorkStore.open(child)
    t = s.create(title, created="2026-01-01")
    s.set_field(t.slug, "initiative", initiative)
    if caps is not None:
        (s.path(t.slug) / "capabilities.yaml").write_text(caps, encoding="utf-8")
    return t.slug


def test_reconcile_rollup_keys_by_node_and_is_idempotent(tmp_path):
    parent = mk_node(tmp_path, "parent")
    epic = FsWorkStore.open(parent).create("Redesign", created="2026-01-01")
    a, b = mk_node(parent, "child-a"), mk_node(parent, "child-b")
    _child_task(a, epic.slug)
    _child_task(b, epic.slug)                              # same slug as child-a's task
    block = reconcile(parent, epic.slug)
    assert "child-a" in block and "child-b" in block
    # both colliding slugs appear, disambiguated by node in the table rows
    # (assert rows, not a raw count — the slug also recurs in the **Next:** line)
    assert "| child-a | 2026-01-01-slice |" in block
    assert "| child-b | 2026-01-01-slice |" in block
    assert reconcile(parent, epic.slug) == block          # idempotent
    content = (FsWorkStore.open(parent).path(epic.slug) / "content.md").read_text()
    assert content.count("<!-- tcw:rollup -->") == 1      # no duplicate block


def test_reconcile_unknown_epic_errors(tmp_path):
    parent = mk_node(tmp_path, "parent")
    with pytest.raises(ValueError):
        reconcile(parent, "2026-01-01-nope")


def test_reconcile_surfaces_capability_deltas(tmp_path):
    parent = mk_node(tmp_path, "parent")
    epic = FsWorkStore.open(parent).create("E", created="2026-01-01")
    a = mk_node(parent, "child-a")
    _child_task(a, epic.slug,
                caps="- file: routes/login\n  heading: sso\n  from: Missing\n  to: Supported\n")
    block = reconcile(parent, epic.slug)
    assert "routes/login#sso" in block
    assert "Missing" in block and "Supported" in block


def test_reconcile_tolerates_malformed_capabilities(tmp_path):
    parent = mk_node(tmp_path, "parent")
    epic = FsWorkStore.open(parent).create("E", created="2026-01-01")
    a = mk_node(parent, "child-a")
    _child_task(a, epic.slug, caps="just: a-mapping\n")   # not a list
    block = reconcile(parent, epic.slug)                   # must not raise
    assert "skipped" in block.lower()
```

- [ ] **Step 2: Run to verify it fails**

Run: `python -m pytest tests/test_recursion.py -k reconcile -v`
Expected: FAIL — `ImportError: cannot import name 'reconcile'`.

- [ ] **Step 3: Create `tcw/work/recursion.py`**

```python
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


def _render(epic_slug: str, tasks: list[tuple[str, WorkItem]]) -> str:
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
        ready = _ready(tasks)
        lines += ["", "**Next:** " + (", ".join(ready) if ready else "all blocked or complete")]
    lines.append("<!-- /tcw:rollup -->")
    return "\n".join(lines)


def reconcile(node_root: Path, epic_slug: str, commit: bool = False) -> str:
    """Scan children for `initiative == epic_slug`; write a consolidated rollup
    into the epic's content.md managed block. Read-only on capabilities."""
    store = FsWorkStore.open(node_root)
    if store.get(epic_slug) is None:
        raise ValueError(f"no such epic: {epic_slug}")
    block = _render(epic_slug, _tasks_for(node_root, epic_slug))
    content = store.path(epic_slug) / "content.md"
    original = content.read_text(encoding="utf-8") if content.exists() else ""
    text = ROLLUP_RE.sub(block, original) if ROLLUP_RE.search(original) \
        else f"{original.rstrip()}\n\n{block}\n"
    if text != original:                       # idempotent at the git level too:
        content.write_text(text, encoding="utf-8")   # don't stage/commit an
        git_stage(node_root, content)                # unchanged rollup (an empty
        if commit:                                   # commit would fail)
            from tcw.store.fs import git_commit
            git_commit(node_root, f"tcw work: reconcile {epic_slug}", "docs/work")
    return block
```

> Note: `git_commit` is added in Task 5; the `--commit` path is exercised only after that task lands. If implementing Task 3 standalone, the import-inside-`if` keeps the default (`commit=False`) path working now.

- [ ] **Step 4: Wire the CLI in `tcw/work/cli.py`**

Add `"reconcile"` to `SUBCOMMANDS`. Add `from tcw.work.recursion import reconcile` (and later `delegate, escalate`). Add:

```python
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
```

In `add_subparser`:

```python
    pr = g.add_parser("reconcile", help="scan child nodes → write the epic rollup")
    pr.add_argument("slug")
    pr.add_argument("--commit", action="store_true", help="also commit the rollup")
    pr.set_defaults(func=_reconcile)
```

- [ ] **Step 5: Run to verify it passes**

Run: `python -m pytest tests/test_recursion.py -k reconcile -v`
Expected: PASS (4 tests).

- [ ] **Step 6: Commit**

```bash
git add tcw/work/recursion.py tcw/work/cli.py tests/test_recursion.py
git commit -m "feat(work): reconcile — cross-node epic rollup (read-only capabilities)"
```

---

## Task 4: Inbox channel (`delegate` / `escalate`)

**Files:**
- Modify: `tcw/work/recursion.py` (add `delegate`, `escalate`, `_inbox_write`)
- Modify: `tcw/work/cli.py` (`_delegate`, `_escalate`, subparsers, `SUBCOMMANDS`)
- Test: `tests/test_recursion.py`

**Interfaces:**
- Produces: `delegate(node_root, child_ref, title, body="", initiative=None) -> Path`; `escalate(node_root, title, body="", initiative=None) -> Path`. Both raise `ValueError` (unknown child / no parent).

- [ ] **Step 1: Write the failing test**

```python
def _no_items(node: Path) -> bool:
    work = node / "docs" / "work"
    return all(not [d for d in (work / s).iterdir() if d.is_dir()]
               for s in ("backlog", "active", "completed"))


def test_delegate_writes_child_inbox_only(tmp_path):
    parent = mk_node(tmp_path, "parent")
    child = mk_node(parent, "child")
    doc = delegate(parent, "child", "Do a thing", body="details", initiative="2026-01-01-epic")
    assert doc.parent == (child / "docs" / "work" / "inbox")
    text = doc.read_text()
    assert "from: ." in text and "initiative: 2026-01-01-epic" in text and "details" in text
    assert _no_items(child)                                # boundary: never touches backlog/active/completed


def test_delegate_unknown_child_errors(tmp_path):
    parent = mk_node(tmp_path, "parent")
    mk_node(parent, "child")
    with pytest.raises(ValueError):
        delegate(parent, "nope", "x")


def test_delegate_filename_collision_suffix(tmp_path):
    parent = mk_node(tmp_path, "parent")
    mk_node(parent, "child")
    d1 = delegate(parent, "child", "Same title")
    d2 = delegate(parent, "child", "Same title")
    assert d1 != d2


def test_escalate_writes_parent_inbox_and_root_errors(tmp_path):
    parent = mk_node(tmp_path, "parent")
    child = mk_node(parent, "child")
    doc = escalate(child, "Cross-repo scope")
    assert doc.parent == (parent / "docs" / "work" / "inbox")
    assert "from: child" in doc.read_text()
    with pytest.raises(ValueError):
        escalate(parent, "x")                              # parent is the root
```

- [ ] **Step 2: Run to verify it fails**

Run: `python -m pytest tests/test_recursion.py -k "delegate or escalate" -v`
Expected: FAIL — `ImportError: cannot import name 'delegate'`.

- [ ] **Step 3: Implement in `tcw/work/recursion.py`** (append)

```python
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
```

- [ ] **Step 4: Wire the CLI in `tcw/work/cli.py`**

Add `"delegate"`, `"escalate"` to `SUBCOMMANDS`; extend the recursion import to `from tcw.work.recursion import delegate, escalate, reconcile`. Add:

```python
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
```

In `add_subparser`:

```python
    pdg = g.add_parser("delegate", help="write a request into a child node's inbox/")
    pdg.add_argument("child", help="child node path (relative to this node)")
    pdg.add_argument("title")
    pdg.add_argument("--initiative", help="stamp the request with an initiative slug")
    pdg.set_defaults(func=_delegate)

    pes = g.add_parser("escalate", help="write a request into the parent node's inbox/")
    pes.add_argument("title")
    pes.add_argument("--initiative", help="stamp the request with an initiative slug")
    pes.set_defaults(func=_escalate)
```

- [ ] **Step 5: Run to verify it passes**

Run: `python -m pytest tests/test_recursion.py -k "delegate or escalate" -v`
Expected: PASS (4 tests).

- [ ] **Step 6: Commit**

```bash
git add tcw/work/recursion.py tcw/work/cli.py tests/test_recursion.py
git commit -m "feat(work): delegate/escalate inbox channel (boundary: inbox only)"
```

---

## Task 5: Worktrees — `start --worktree` + `complete` teardown

**Files:**
- Modify: `tcw/store/fs.py` (worktree plumbing: `WORKTREES_DIR`, `git_commit`, `ensure_worktree_ignored`, `add_worktree`, `remove_worktree`)
- Modify: `tcw/work/cli.py` (`_start` rewrite, `_complete` teardown, `start --worktree` flag)
- Test: `tests/test_recursion.py`

**Interfaces:**
- Consumes: `WorkItem.worktree`/`branch` (Task 2).
- Produces: `git_commit(node_root, message, *paths)`; `ensure_worktree_ignored(node_root)`; `add_worktree(node_root, slug) -> tuple[Path, str]`; `remove_worktree(node_root, slug, branch=None) -> list[str]`; `WORKTREES_DIR = ".worktrees"`.

- [ ] **Step 1: Write the failing test**

```python
def test_start_worktree_places_item_in_worktree(tmp_path, monkeypatch, capsys):
    root = mk_node(tmp_path, "repo")
    commit_all(root)
    monkeypatch.chdir(root)
    from tcw.cli import main
    main(["work", "new", "Build it"]); slug = capsys.readouterr().out.strip()
    assert main(["work", "start", slug, "--worktree"]) == 0
    capsys.readouterr()
    wt = root / ".worktrees" / slug
    assert (wt / "docs" / "work" / "active" / slug / "state.yaml").is_file()  # item IS in the worktree
    item = FsWorkStore.open(root).get(slug)
    assert item.status == "active" and item.branch == f"work/{slug}"
    assert ".worktrees/" in (root / ".gitignore").read_text()


def test_worktree_edit_merges_back_clean(tmp_path, monkeypatch, capsys):
    root = mk_node(tmp_path, "repo")
    commit_all(root)
    monkeypatch.chdir(root)
    from tcw.cli import main
    main(["work", "new", "Feature"]); slug = capsys.readouterr().out.strip()
    main(["work", "start", slug, "--worktree"]); capsys.readouterr()
    wt = root / ".worktrees" / slug
    monkeypatch.chdir(wt)                                  # work on the branch
    main(["work", "edit", slug, "--blocked-by", "external: upstream"])
    subprocess.run(["git", "-C", str(wt), "commit", "-q", "-am", "edit"], check=True)
    subprocess.run(["git", "-C", str(root), "merge", "-q", "--no-edit", f"work/{slug}"],
                   check=True)                             # clean merge — single-owner invariant
    item = FsWorkStore.open(root).get(slug)
    assert any("upstream" in b.get("external", "") for b in item.blocked_by)


def test_complete_tears_down_worktree(tmp_path, monkeypatch, capsys):
    root = mk_node(tmp_path, "repo")
    commit_all(root)
    monkeypatch.chdir(root)
    from tcw.cli import main
    main(["work", "new", "Ship"]); slug = capsys.readouterr().out.strip()
    main(["work", "start", slug, "--worktree"]); capsys.readouterr()
    assert main(["work", "complete", slug, "--resolution", "done", "--confirm"]) == 0
    assert not (root / ".worktrees" / slug).exists()
    branches = subprocess.run(["git", "-C", str(root), "branch", "--list", f"work/{slug}"],
                              capture_output=True, text=True).stdout.strip()
    assert branches == ""
    assert FsWorkStore.open(root).get(slug).status == "completed"
```

- [ ] **Step 2: Run to verify it fails**

Run: `python -m pytest tests/test_recursion.py -k "worktree or tears_down" -v`
Expected: FAIL — `unrecognized arguments: --worktree`.

- [ ] **Step 3: Add worktree plumbing to `tcw/store/fs.py`** (after the `git_mv` helper)

```python
WORKTREES_DIR = ".worktrees"


def git_commit(node_root: Path, message: str, *paths: str) -> None:
    """Commit staged changes. With paths, a scoped (partial) commit so unrelated
    staged changes are left alone — used by start --worktree (spec §3.4)."""
    cmd = ["git", "-C", str(node_root), "commit", "-q", "-m", message]
    if paths:
        cmd += ["--", *paths]
    subprocess.run(cmd, check=True)


def ensure_worktree_ignored(node_root: Path) -> None:
    """Add `.worktrees/` to the node's .gitignore (a linked worktree dir is
    untracked otherwise and would clutter/be staged). Idempotent; stages it."""
    gi = node_root / ".gitignore"
    line = f"{WORKTREES_DIR}/"
    existing = gi.read_text(encoding="utf-8") if gi.exists() else ""
    if line not in existing.splitlines():
        gi.write_text((existing.rstrip("\n") + "\n" if existing else "") + line + "\n",
                      encoding="utf-8")
        git_stage(node_root, gi)


def add_worktree(node_root: Path, slug: str) -> tuple[Path, str]:
    """Create the item's git worktree + branch from HEAD. Returns (path, branch)."""
    wt = node_root / WORKTREES_DIR / slug
    branch = f"work/{slug}"
    subprocess.run(["git", "-C", str(node_root), "worktree", "add", "-q",
                    "-b", branch, str(wt)], check=True)
    return wt, branch


def remove_worktree(node_root: Path, slug: str, branch: str | None = None) -> list[str]:
    """Best-effort teardown (spec §3.4): `git worktree remove` refuses on a dirty
    worktree — the safety net against losing uncommitted work. Returns warnings."""
    warns: list[str] = []
    wt = node_root / WORKTREES_DIR / slug
    r = subprocess.run(["git", "-C", str(node_root), "worktree", "remove", str(wt)],
                       capture_output=True, text=True)
    if r.returncode != 0:
        warns.append(f"worktree remove failed for {slug}: {r.stderr.strip()}")
    elif branch:
        rb = subprocess.run(["git", "-C", str(node_root), "branch", "-D", branch],
                            capture_output=True, text=True)
        if rb.returncode != 0:
            warns.append(f"branch delete failed for {branch}: {rb.stderr.strip()}")
    return warns
```

- [ ] **Step 4: Rewrite `_start` and extend `_complete` in `tcw/work/cli.py`**

Extend the fs import to include `add_worktree, ensure_worktree_ignored, git_commit, remove_worktree, WORKTREES_DIR`. Replace `_start`:

```python
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
    return 0
```

Add `import subprocess` at the top of `cli.py`. In `_complete`, capture the worktree info before completing and tear down after the success print:

```python
    branch = item.branch or None
    has_worktree = bool(item.worktree)
    # ... existing checklist + st.complete(...) ...
    print(f"completed {args.slug} ({args.resolution})")
    if has_worktree:
        for w in remove_worktree(st.node_root, args.slug, branch):
            print(f"tcw work complete: {w}", file=sys.stderr)
    return 0
```

(Place the two captures right after the `item is None` guard, where `item` is in scope.)

In `add_subparser`, add to the `start` parser:

```python
    pst.add_argument("--worktree", action="store_true",
                     help="isolate the item in its own git worktree + branch")
```

- [ ] **Step 5: Run to verify it passes**

Run: `python -m pytest tests/test_recursion.py -k "worktree or tears_down" -v`
Expected: PASS (3 tests).

- [ ] **Step 6: Run the full suite**

Run: `python -m pytest -q`
Expected: PASS (all prior tests + the new `test_recursion.py`).

- [ ] **Step 7: Commit**

```bash
git add tcw/store/fs.py tcw/work/cli.py tests/test_recursion.py
git commit -m "feat(work): start --worktree + complete teardown (split ownership rule)"
```

---

## Task 6: Documentation sync + version

**Files:**
- Modify: `README.md`, `docs/release-notes/upcoming.md`, `docs/changelogs/upcoming.md`, `docs/plan/phase-6-beyond.md`, `docs/plan/phase-5-work.md`
- Run the `skill-cefailures:documentation-sync` skill to confirm coverage.

- [ ] **Step 1: README** — under the `tcw work` section, document the new commands and flags:
  - `tcw work nodes` — list parent + child nodes.
  - `tcw work reconcile <epic-slug> [--commit]` — write the cross-node rollup into an epic.
  - `tcw work delegate <child> "<title>"` / `tcw work escalate "<title>"` — the inbox channel (body via stdin).
  - `tcw work new --epic --initiative <slug>`, `tcw work edit --initiative <slug>`, `tcw work start --worktree`.
  - A short "Cross-node / epics" subsection: an epic is an ordinary item other nodes' tasks point at via `initiative:`; `reconcile` consolidates them; worktree-isolated items follow the split-ownership rule (transitions on trunk, edits on the work branch).

- [ ] **Step 2: `docs/release-notes/upcoming.md`** — plain language: "Work items can now span repositories. An epic in one repo gathers tasks in child repos; `tcw work reconcile` builds a live rollup. `delegate`/`escalate` pass requests between repos. `start --worktree` runs an item in its own isolated checkout."

- [ ] **Step 3: `docs/changelogs/upcoming.md`** — Added: node topology, `reconcile`, `delegate`/`escalate`, `nodes`, `initiative`/`type`/`worktree`/`branch` fields, `start --worktree`. Include the commit-hash range (`git rev-parse --short HEAD` before/after).

- [ ] **Step 4: `docs/plan/phase-6-beyond.md`** — change the "Cross-node / recursion (work Spec 2)" status from deferred to built; link this work folder.

- [ ] **Step 5: `docs/plan/phase-5-work.md`** — reconcile the B.4 ("No type field") vs A.6 (`type: epic`) wording: add a one-line note that Spec 2 introduces `type` as **optional recursion sugar** (only value `epic`); the product/technical/meta axes still classify, there is no *mandatory* type field.

- [ ] **Step 6: Invoke the documentation-sync skill** to verify every triggered entry is covered, then commit:

```bash
git add README.md docs/
git commit -m "docs(work): cross-node recursion — README, release notes, changelog, phase docs"
```

---

## Self-Review (done while writing)

- **Spec coverage:** §3.1 → Task 1; §3.3 → Task 2; §3.2 reconcile → Task 3; §3.2 delegate/escalate → Task 4; §3.4 worktrees → Task 5; §6 docs → Task 6. All §5 test cases are mapped into the task tests (topology incl. nested-repo + worktree exclusion; reconcile keying/idempotency/deltas/malformed/unknown-epic; inbox boundary/collision/root-error; worktree placement/merge-back/teardown; field set+clear).
- **Type consistency:** `child_nodes`/`parent_node` return `Path`/`Path|None`; `reconcile`→`str` raising `ValueError`; `delegate`/`escalate`→`Path`; worktree helpers as declared. `_ERRORS` in cli.py already includes `ValueError`, so reconcile/delegate/escalate errors are caught.
- **No placeholders:** every code/test step carries real content. The one forward-reference (`git_commit` used by reconcile's `--commit`) is added in Task 5 and guarded by an import-inside-`if` so Task 3 lands green on its own.

## Execution note

After the final task, run `tcw work start 2026-06-19-cross-node-recursion-work-spec-2` as the **first implementation commit** per CLAUDE.md (moves the item `backlog → active`). Do this before Task 1's code commit if you want the status transition to lead; otherwise it can ride with Task 1.
