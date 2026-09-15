# Node sentinel + sentinel-based node detection — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Decouple TCW "node" identity from git-repo identity via a `tcw-config.yaml` sentinel, so one git repo can hold multiple project subfolders, each detected independently.

**Architecture:** A node is the nearest ancestor directory holding a `tcw-config.yaml` file. `find_node_root()` walks up to it; `find_node(component)` gates that on the component dir existing. `init()` writes the sentinel as part of scaffolding a node; `tcw init` scaffolds the **current directory**. All changes are FS-adapter-local (`tcw/store/fs.py`, `tcw/cli.py`, the three component CLIs) — no abstract store-interface method changes.

**Tech Stack:** Python 3 (type hints), pytest over `tmp_path` git repos, PyYAML, git CLI via `subprocess`.

## Global Constraints

- **Abstraction litmus (AGENTS.md):** detection stays an FS-adapter-local helper; add **no** method to any `*Store` ABC. `find_node_root` is a module-level function like `git_root`, never a store method.
- **Commit messages:** no co-authoring / trailer content (AGENTS.md generic instruction).
- **Reserved filename:** `tcw-config.yaml` is a node marker at any depth — never commit one except at a node root.
- **Sentinel content (v1):** comment-only stub; existence is what matters. Detection never parses it.
- **Create-don't-stage:** `init` creates the sentinel and the `docs/` skeleton without touching the git index (matches today's scaffolding).
- **Report determinism:** `tcw init` stdout must be byte-identical across repeated runs (existing idempotency tests compare it).
- **Lifecycle:** run `tcw work start 2026-06-22-node-sentinel-tcw-config-yaml-and-sentinel-based-node-detection` **before** Task 1 — that transition is the first implementation commit (bundling the committed `spec.md`/`plan.md`/`capabilities.yaml`). Run `tcw work complete … --resolution done --confirm` only after Task 6.

---

## File Structure

- **Modify** `tcw/store/fs.py` — add `SENTINEL`, `write_sentinel()`, `find_node_root()`; rewrite `find_node()`; `init()` writes the sentinel.
- **Modify** `tcw/cli.py` — `run_init()` targets cwd, emits a deterministic node-marker line.
- **Modify** `tcw/taxonomy/cli.py`, `tcw/capabilities/cli.py`, `tcw/work/cli.py` — guard-message wording.
- **Create** `tests/test_store_nodes.py` — unit tests for detection + sentinel.
- **Create** `tests/test_multiproject.py` — two-project monorepo integration (taxonomy extends + capabilities check).
- **Modify** `tests/test_taxonomy.py`, `tests/test_capabilities.py` — `node()` fixtures write the sentinel.
- **Create** `tcw-config.yaml` at the repo root — this repo's own migration.
- **Modify** `README.md`, `docs/release-notes/upcoming.md`, `docs/changelogs/upcoming.md`, `skills/tcw-work/SKILL.md` (+ verify `skills/tcw-work/docs/cross-node-epic.md`) — docs sync.

---

### Task 1: Sentinel detection in `tcw/store/fs.py` + fixture migration

The cohesive core: switching detection to the sentinel. It deliberately includes the fixture migration and this repo's own sentinel, so the **full suite stays green** within the task (rewriting `find_node` breaks the existing CLI tests until both land).

**Files:**
- Modify: `tcw/store/fs.py` (the `git + node helpers` block, ~line 28–57; `init`, ~line 207)
- Create: `tests/test_store_nodes.py`
- Modify: `tests/test_taxonomy.py:10-16` (the `node()` fixture), `tests/test_capabilities.py:10-15` (the `node()` fixture)
- Create: `tcw-config.yaml` (repo root)

**Interfaces:**
- Produces: `SENTINEL: str` (= `"tcw-config.yaml"`); `write_sentinel(root: Path) -> bool`; `find_node_root(start: Path | None = None) -> Path | None`; `find_node(component: str, start: Path | None = None) -> Path | None` (signature unchanged); `init(components, root)` now also writes the sentinel.
- Consumes: existing `git_root` (kept, no longer used by `find_node`).

- [ ] **Step 1: Write the failing unit tests**

Create `tests/test_store_nodes.py`:

```python
import subprocess
from pathlib import Path

from tcw.store.fs import SENTINEL, find_node, find_node_root, init, write_sentinel


def test_find_node_root_nearest(tmp_path):
    write_sentinel(tmp_path)
    sub = tmp_path / "a" / "b"
    sub.mkdir(parents=True)
    assert find_node_root(sub) == tmp_path.resolve()


def test_find_node_root_nested_resolves_innermost(tmp_path):
    write_sentinel(tmp_path)
    inner = tmp_path / "proj"
    inner.mkdir()
    write_sentinel(inner)
    deep = inner / "x"
    deep.mkdir()
    assert find_node_root(deep) == inner.resolve()


def test_find_node_root_none_when_absent(tmp_path):
    assert find_node_root(tmp_path) is None


def test_find_node_root_requires_a_file_not_a_dir(tmp_path):
    (tmp_path / SENTINEL).mkdir()       # a *directory* named tcw-config.yaml
    assert find_node_root(tmp_path) is None


def test_find_node_gates_on_component(tmp_path):
    write_sentinel(tmp_path)
    (tmp_path / "docs" / "work").mkdir(parents=True)
    assert find_node("work", tmp_path) == tmp_path.resolve()
    assert find_node("taxonomy", tmp_path) is None


def test_write_sentinel_idempotent(tmp_path):
    assert write_sentinel(tmp_path) is True
    assert write_sentinel(tmp_path) is False
    assert (tmp_path / SENTINEL).is_file()


def test_init_writes_sentinel(tmp_path):
    init(["work"], tmp_path)
    assert (tmp_path / SENTINEL).is_file()
```

- [ ] **Step 2: Run them to confirm they fail**

Run: `python -m pytest tests/test_store_nodes.py -q`
Expected: FAIL — `ImportError: cannot import name 'SENTINEL'` (and `write_sentinel`/`find_node_root`).

- [ ] **Step 3: Add the sentinel primitives + rewrite `find_node` in `tcw/store/fs.py`**

Replace the current `find_node` (lines ~47-57) and add the new helpers in the same `git + node helpers` block:

```python
SENTINEL = "tcw-config.yaml"
_SENTINEL_STUB = (
    "# tcw node marker — declares this folder a TCW project (node).\n"
    "# Future config (inheritance, etc.) goes here.\n"
)


def write_sentinel(root: Path) -> bool:
    """Create the node sentinel at `root` if absent; return True iff it wrote one.
    Create-don't-stage (mirrors how `init` scaffolds dirs) — never touches the index."""
    p = root / SENTINEL
    if p.exists():
        return False
    p.write_text(_SENTINEL_STUB, encoding="utf-8")
    return True


def find_node_root(start: Path | None = None) -> Path | None:
    """The nearest ancestor of `start` (cwd by default) holding a `tcw-config.yaml`
    *file* — the node root, or None. FS-adapter-local: realizes 'locate the node'.
    Resolves `start` (like `git_root`) so a symlinked cwd chains identically."""
    d = (start or Path.cwd()).resolve()
    while True:
        if (d / SENTINEL).is_file():
            return d
        if d == d.parent:                  # filesystem-root fixpoint
            return None
        d = d.parent


def find_node(component: str, start: Path | None = None) -> Path | None:
    """The node owning `docs/<component>/`, or None. A node is the nearest
    ancestor marked by a `tcw-config.yaml` sentinel (FS-adapter-local). Returns
    the node iff it has that component, preserving the prior contract."""
    nr = find_node_root(start)
    return nr if nr is not None and (nr / "docs" / component).is_dir() else None
```

Then update `init()` (line ~207) to write the sentinel first:

```python
def init(components: list[str], root: Path) -> list[Path]:
    """Scaffold `docs/<component>/` skeletons under `root` and mark it a node.
    Returns leaf dirs made. A `.gitkeep` lands in each leaf so the empty skeleton
    survives a commit (git doesn't track empty directories)."""
    write_sentinel(root)
    created: list[Path] = []
    for c in components:
        base = root / "docs" / c
        leaves = [base / s for s in WORK_STATUSES] if c == "work" else [base]
        for leaf in leaves:
            leaf.mkdir(parents=True, exist_ok=True)
            (leaf / ".gitkeep").touch()
            created.append(leaf)
    return created
```

Also update the module docstring line referencing the old detection (`fs.py:3`) if it names git-root detection — change "git_root/init (Phase 1) scaffold" to mention the sentinel marker. (Cosmetic; keep it short.)

- [ ] **Step 4: Run the unit tests — expect pass**

Run: `python -m pytest tests/test_store_nodes.py -q`
Expected: PASS (7 passed).

- [ ] **Step 5: Migrate the two direct-mkdir fixtures**

In `tests/test_taxonomy.py`, add the import and one line in `node()`:

```python
from tcw.store.fs import FsTaxonomyStore, write_sentinel   # add write_sentinel
```
```python
def node(tmp_path: Path, name: str) -> Path:
    """A repo root with docs/taxonomy/ (git-inited so add/rm can stage)."""
    root = tmp_path / name
    (root / "docs" / "taxonomy").mkdir(parents=True)
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    subprocess.run(["git", "-C", str(root), "config", "user.email", "t@t"], check=True)
    subprocess.run(["git", "-C", str(root), "config", "user.name", "t"], check=True)
    write_sentinel(root)                # mark it a node for CLI (find_node) tests
    return root
```

In `tests/test_capabilities.py`, the same — add `write_sentinel` to the import from `tcw.store.fs`, and call `write_sentinel(root)` before `return root` in `node()`.

(The `test_work.py`, `test_recursion.py`, and `test_skill_flow.py` fixtures build their node via `init(...)`, which now writes the sentinel — no edit needed.)

- [ ] **Step 6: Run the full suite — expect green**

Run: `python -m pytest -q`
Expected: PASS. If any CLI test still fails with the node guard, its fixture builds a node a third way — add `write_sentinel(root)` there too.

- [ ] **Step 7: Migrate this repo (own sentinel) so live `tcw` keeps resolving**

The editable install makes the new detection live immediately, so this repo needs its own marker. Create `tcw-config.yaml` at the repo root:

```
# tcw node marker — declares this folder a TCW project (node).
# Future config (inheritance, etc.) goes here.
```

Verify the live CLI still resolves this node:

Run: `tcw work list --status active`
Expected: the board prints (no "no tcw work node here" error).

- [ ] **Step 8: Commit**

```bash
git add tcw/store/fs.py tests/test_store_nodes.py tests/test_taxonomy.py tests/test_capabilities.py tcw-config.yaml
git commit -m "feat(store): sentinel-based node detection (tcw-config.yaml)"
```

---

### Task 2: `tcw init` targets cwd + deterministic report

**Files:**
- Modify: `tcw/cli.py` (`run_init`, lines ~22-38; add `from pathlib import Path` if absent)
- Modify: `tests/test_smoke.py` (add a subfolder-init test)

**Interfaces:**
- Consumes: `init()` (writes sentinel, Task 1), `git_root`.
- Produces: `run_init(components)` scaffolding at `Path.cwd()` with a deterministic trailing node-marker line.

- [ ] **Step 1: Write the failing test**

Add to `tests/test_smoke.py`:

```python
def test_init_scaffolds_in_current_subfolder(tmp_path, monkeypatch):
    _git_init(tmp_path)                       # one git repo
    proj = tmp_path / "project-b"
    proj.mkdir()
    monkeypatch.chdir(proj)                   # cwd is a subfolder, not the git root
    assert main(["init", "work"]) == 0
    assert (proj / "tcw-config.yaml").is_file()
    assert (proj / "docs" / "work").is_dir()
    assert not (tmp_path / "docs").exists()   # scaffolded at cwd, not the git root
```

- [ ] **Step 2: Run it — expect fail**

Run: `python -m pytest tests/test_smoke.py::test_init_scaffolds_in_current_subfolder -q`
Expected: FAIL — `docs/` lands at `tmp_path` (git root), `tmp_path/docs` exists / `proj/docs` missing.

- [ ] **Step 3: Rewrite `run_init` to target cwd**

In `tcw/cli.py`, ensure `from pathlib import Path` is imported, then:

```python
def run_init(components: list[str]) -> int:
    """Scaffold `docs/<component>/` trees under the current directory, mark it a
    node, and report. Shared by `tcw init` and each `tcw <component> init`."""
    root = Path.cwd()
    if git_root(root) is None:                 # returns the repo root for any dir inside it
        print("tcw init: not inside a git repository. Run `git init` first.", file=sys.stderr)
        return 1
    unknown = [c for c in components if c not in COMPONENTS]
    if unknown:
        print(f"tcw init: unknown component(s): {', '.join(unknown)}. "
              f"Choose from: {', '.join(COMPONENTS)}.", file=sys.stderr)
        return 2
    created = init(components, root)
    print(f"Scaffolded {len(created)} dir(s) under {root / 'docs'}:")
    for p in created:
        print(f"  {p.relative_to(root)}")
    print(f"Node marker: {SENTINEL}")          # deterministic across runs
    return 0
```

Add `SENTINEL` to the import: `from tcw.store.fs import COMPONENTS, SENTINEL, git_root, init`.

- [ ] **Step 4: Run the new test + the idempotency tests — expect pass**

Run: `python -m pytest tests/test_smoke.py tests/test_work.py::test_cli_work_init_mirrors_top_level tests/test_taxonomy.py::test_cli_taxonomy_init_mirrors_top_level -q`
Expected: PASS. (The `Node marker:` line is identical on repeat runs, so byte-equal-stdout holds.)

- [ ] **Step 5: Full suite + commit**

Run: `python -m pytest -q` → PASS.
```bash
git add tcw/cli.py tests/test_smoke.py
git commit -m "feat(cli): tcw init scaffolds the current directory and marks it a node"
```

---

### Task 3: Multi-project integration tests (the inheritance payoff)

Pure tests — proves a sibling subfolder inherits via `extends` and that capabilities `check` resolves the sibling taxonomy. No new code expected; if a test fails, the bug is in Task 1/2.

**Files:**
- Create: `tests/test_multiproject.py`

- [ ] **Step 1: Write the tests**

```python
import subprocess
from pathlib import Path

import yaml

from tcw.store.fs import (
    FsCapabilitiesStore, FsTaxonomyStore, find_node, init,
)


def _monorepo(tmp_path: Path) -> Path:
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    subprocess.run(["git", "-C", str(tmp_path), "config", "user.email", "t@t"], check=True)
    subprocess.run(["git", "-C", str(tmp_path), "config", "user.name", "t"], check=True)
    for name in ("project-a", "project-b"):
        root = tmp_path / name
        root.mkdir()
        init(["taxonomy", "capabilities"], root)     # writes sentinel + docs/
    return tmp_path


def _extend_b_onto_a(repo: Path) -> None:
    (repo / "project-b" / "docs" / "taxonomy" / "config.yaml").write_text(
        yaml.safe_dump({"extends": {"base": "../project-a"}}))


def test_extends_resolves_across_sibling_subfolders(tmp_path):
    repo = _monorepo(tmp_path)
    FsTaxonomyStore.open(repo / "project-a").add("Account")
    _extend_b_onto_a(repo)
    node = find_node("taxonomy", repo / "project-b")     # detection finds project-b
    assert node == (repo / "project-b").resolve()
    term = FsTaxonomyStore.open(node).get("base/account")
    assert term is not None and term.name == "Account"


def test_capabilities_check_resolves_sibling_taxonomy(tmp_path):
    repo = _monorepo(tmp_path)
    FsTaxonomyStore.open(repo / "project-a").add("Account")
    _extend_b_onto_a(repo)
    caps = FsCapabilitiesStore.open(repo / "project-b")
    caps.add("orders", "Place an order")
    caps.set("orders", {"Subject": "base/account"})
    node = find_node("capabilities", repo / "project-b")
    tax = FsTaxonomyStore.open(node)
    assert FsCapabilitiesStore.open(node).check(taxonomy=tax) == []
```

- [ ] **Step 2: Run — expect pass**

Run: `python -m pytest tests/test_multiproject.py -q`
Expected: PASS (2 passed). If `get("base/account")` is None, re-check `FsTaxonomyStore.__init__` resolving `extends` against `self.node_root` (Task 1 must not have altered `node_root`).

- [ ] **Step 3: Commit**

```bash
git add tests/test_multiproject.py
git commit -m "test: multi-project monorepo inheritance via extends across subfolders"
```

---

### Task 4: Improve the node-guard messages

**Files:**
- Modify: `tcw/taxonomy/cli.py` (`_store`, ~line 20-23)
- Modify: `tcw/capabilities/cli.py` (`_store`, ~line 20-23)
- Modify: `tcw/work/cli.py` (the repeated guard in `_store`/`_nodes`/`_reconcile`/etc.)
- Modify: `tests/test_smoke.py` (assert the new message)

- [ ] **Step 1: Write the failing test**

Add to `tests/test_smoke.py`:

```python
def test_command_outside_a_node_reports_helpfully(tmp_path, monkeypatch, capsys):
    _git_init(tmp_path)            # a git repo but NOT a tcw node (no sentinel)
    monkeypatch.chdir(tmp_path)
    assert main(["work", "list"]) == 1
    assert "tcw init" in capsys.readouterr().err
```

- [ ] **Step 2: Run — expect fail or pass-by-accident**

Run: `python -m pytest tests/test_smoke.py::test_command_outside_a_node_reports_helpfully -q`
Expected: the current message already contains `tcw work init`, so this may PASS; the point of this task is the *wording*. Proceed to Step 3 regardless.

- [ ] **Step 3: Update the wording**

`tcw/taxonomy/cli.py`:
```python
        print("tcw taxonomy: no tcw taxonomy node here — run `tcw init` in the project folder.",
              file=sys.stderr)
```
`tcw/capabilities/cli.py`:
```python
        print("tcw capabilities: no tcw capabilities node here — run `tcw init` in the project folder.",
              file=sys.stderr)
```
`tcw/work/cli.py` — replace **every** occurrence of
`"tcw work: no docs/work/ in this repo. Run \`tcw work init\`."`
with
`"tcw work: no tcw work node here — run \`tcw init\` in the project folder."`
(use a replace-all; the string repeats in `_store`, `_nodes`, `_reconcile`, and the delegate/escalate guards.)

- [ ] **Step 4: Run the test + full suite**

Run: `python -m pytest -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add tcw/taxonomy/cli.py tcw/capabilities/cli.py tcw/work/cli.py tests/test_smoke.py
git commit -m "feat(cli): clearer node-not-found guidance pointing at tcw init"
```

---

### Task 5: Documentation sync

No tests. Use verified line references from the spec (§8).

**Files:**
- Modify: `README.md`, `docs/release-notes/upcoming.md`, `docs/changelogs/upcoming.md`, `skills/tcw-work/SKILL.md`

- [ ] **Step 1: README**

- Line ~145: change "`tcw init` operates on the current git work-tree…" to describe operating on the **current directory** (writing a `tcw-config.yaml` marker), still refusing outside a git repo.
- Add a short "Multiple projects in one repo" subsection: the layout example from the spec, the sentinel, `cd project-b && tcw init`, and "taxonomy `extends` works across sibling subfolder projects."
- Lines ~309 & ~379 ("Any git repo with a `docs/work/` is a node"): apply **surgical** wording distinguishing *current node = sentinel* from *cross-node discovery = git repos (until a later sub-project)*. Do not blanket-rewrite.

- [ ] **Step 2: Release notes** — add to `docs/release-notes/upcoming.md` (plain language): a single git repo can now hold several TCW projects as subfolders; mark each with `tcw init`; sibling projects can share vocabulary via taxonomy extends.

- [ ] **Step 3: Changelog** — add to `docs/changelogs/upcoming.md` (with `git rev-parse --short HEAD` range), grouped:
  - **Added:** `find_node_root`, `write_sentinel`, `tcw-config.yaml` node marker; multi-project subfolder support.
  - **Changed:** `find_node` now sentinel-based; `tcw init` scaffolds cwd + writes the sentinel; node-guard messages.

- [ ] **Step 4: Skill** — `skills/tcw-work/SKILL.md`: note `tcw init` now marks the current folder a node (sentinel). Verify `skills/tcw-work/docs/cross-node-epic.md`'s "any git repo with docs/work is a node" wording stays valid for cross-node discovery (it does) — leave unless it conflicts.

- [ ] **Step 5: Commit**

```bash
git add README.md docs/release-notes/upcoming.md docs/changelogs/upcoming.md skills/tcw-work/SKILL.md
git commit -m "docs: sync README/notes/changelog/skill for sentinel node detection"
```

---

### Task 6: Capability ledger flip + completion

**Files:**
- Modify: `docs/capabilities/cli/host-multiple-projects-in-one-repo.md` (status)
- Modify: `docs/capabilities/cli/capabilities.md` (`Scaffold the doc trees` wording)

- [ ] **Step 1: Flip the new capability to Supported**

Run: `tcw capabilities set "cli/host-multiple-projects-in-one-repo#host-multiple-projects-in-one-repo" --status Supported`

- [ ] **Step 2: Refine the changed capability's wording**

Edit `Scaffold the doc trees` (`cli#scaffold-the-doc-trees`) body so it says `tcw init` scaffolds the **current directory** (writing a `tcw-config.yaml` marker) rather than "inside a git repo … under the repo root." Keep `**Status:** Supported`.

- [ ] **Step 3: Validate the ledger**

Run: `tcw capabilities check`
Expected: `capabilities OK`.

- [ ] **Step 4: Full suite + documentation-sync skill, then complete**

Run: `python -m pytest -q` → PASS.
Invoke the `skill-cefailures:documentation-sync` skill to confirm every triggered doc is updated.
Then:
```bash
git add docs/capabilities
git commit -m "capabilities: host-multiple-projects Supported; refine scaffold wording"
```
Run: `tcw work complete 2026-06-22-node-sentinel-tcw-config-yaml-and-sentinel-based-node-detection --resolution done --confirm`

(Version: this is a user-facing change — a **minor** `scripts/cut_version.py` bump is warranted at the next release, separate from this item.)

---

## Self-review

- **Spec coverage:** sentinel §3.1 → T1; detection §3.2 → T1; `init` cwd/backfill/report §3.3 → T1+T2; guard message §3.4 → T4; inheritance payoff §4 → T3; SP2 boundary §5 → untouched code (verified, no task); repo migration §6 → T1 Step 7; tests §7.1-7.8 → T1/T2/T3 (+ fixture migration T1 Step 5); docs §8 → T5; versioning §9 → T6 note; capability gate → T6.
- **Placeholder scan:** none — every code step shows code; every run step shows command + expected.
- **Type consistency:** `SENTINEL`, `write_sentinel`, `find_node_root`, `find_node` names/signatures consistent across T1→T2→T3; `init(components, root)` signature unchanged.
