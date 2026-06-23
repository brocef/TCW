# Spec — Node sentinel (`tcw-config.yaml`) + sentinel-based node detection

**Status:** design approved (brainstorming), pending implementation plan
**Work item:** `2026-06-22-node-sentinel-tcw-config-yaml-and-sentinel-based-node-detection`
**Sub-project:** 1 of 3 (foundation). SP2 = cross-node recursion across subfolder
nodes; SP3 = new inheritance machinery. Both depend on this and are out of scope.

## 1. Problem

TCW should support a **shared documentation repo holding multiple projects as
subfolders**, each with its own `docs/{taxonomy,capabilities,work}/`, with
inheritance between them (e.g. `project-b` inherits `project-a`'s taxonomy):

```
/                       # one git repo (documentation root)
  /.git
  /project-a/docs/{taxonomy,capabilities,work}/
  /project-b/docs/{taxonomy,capabilities,work}/   # extends project-a's taxonomy
```

Today a **node is defined as a git work-tree root that contains
`docs/<component>/`**. `git_root()` shells out to `git rev-parse
--show-toplevel`; `find_node()` checks for `docs/<component>/` directly under
that root. In the layout above, running `tcw` inside `project-b/` resolves
`git_root()` to the *monorepo root*, looks for `docs/work/` there, finds nothing,
and fails. Node identity is wrongly welded to git-repo identity.

The fix decouples the two: a **`tcw-config.yaml` sentinel** declares a folder a
TCW node. This is the smallest change that unblocks the layout — and it makes the
already-existing taxonomy `extends` inheritance work between siblings for free.

## 2. Abstraction litmus (AGENTS.md prime directive)

Node detection is **filesystem-adapter-local** — it realizes the abstract notion
"locate the store root / node identity." `git_root`/`find_node` are already
marked FS-adapter details, not store-interface operations. A remote backend would
resolve a node by a project key instead of a sentinel file. So the sentinel is a
pure FS realization; **no abstract store-interface method changes.** ✓

## 3. Design

### 3.1 The sentinel: `tcw-config.yaml`

- Lives at the **node root** (the folder that contains `docs/`).
- v1 content is a comment-only stub; its **existence** is what marks the node:

  ```yaml
  # tcw node marker — declares this folder a TCW project (node).
  # Future config (inheritance, etc.) goes here.
  ```

- Loaded with the existing `load_yaml` (absent/empty → `{}`), so future keys
  (SP2/SP3) cost nothing to add.
- **Node-scoped**, and kept distinct from the existing **component-scoped**
  configs (`docs/taxonomy/config.yaml`, `docs/capabilities/.config.yaml`). No
  merging of the three — different scopes.
- **Detection never parses the sentinel** — it tests existence only
  (§3.2). Content is loaded lazily by features that read keys (none in v1), so a
  malformed sentinel cannot break detection. YAML is deliberate (the user wants
  it to carry future config); a plain marker file was considered and rejected.
- **Reserved filename at any depth.** Because detection is nearest-wins by
  filename (§3.2), a `tcw-config.yaml` placed anywhere under a node (a fixture, a
  docs example, a work-item attachment) would shadow the real node for any cwd
  beneath it. `tcw-config.yaml` is therefore reserved as a node marker at every
  depth — never commit one except at a node root.

### 3.2 Detection (all in `tcw/store/fs.py`)

- New `find_node_root(start: Path | None = None) -> Path | None`: from
  `(start or Path.cwd()).resolve()` (mirroring `git_root`'s resolve so symlinked
  cwds chain identically), walk up parents to the **nearest** directory holding a
  **file** `tcw-config.yaml` (match `is_file()`, not a dir of that name); return
  it, or `None`. The walk terminates at the filesystem-root fixpoint
  (`p == p.parent`). **Nearest-wins** → nested nodes resolve to the innermost
  node (this also sets up SP2 with no extra work).
- `find_node(component: str, start: Path | None = None) -> Path | None` is
  rewired to:
  ```python
  nr = find_node_root(start)
  return nr if nr is not None and (nr / "docs" / component).is_dir() else None
  ```
  **Signature and call contract unchanged** — callers keep calling
  `find_node(component)` and still get the node iff it has that component (a node
  missing a component reports `None`, as today). The only caller-side edit is the
  improved failure-message string (§3.4); runtime behavior otherwise shifts only
  in that a sentinel is now required (which is why all test fixtures need one,
  §7.7).
- `find_node` **no longer calls `git_root`**. `git_root` remains for git plumbing
  (`git -C node_root …`) and for SP2's `child_nodes`/`parent_node`, which are
  **untouched** here.

### 3.3 `tcw init`: scaffold at cwd, write sentinel, idempotent backfill

`run_init()` in `tcw/cli.py` changes its target from `git_root()` to **cwd**
(`Path.cwd()`). Note the guard uses `git_root(cwd) is not None`, which is true
for *any* directory inside a repo (it returns the repo **root**, not cwd) — the
node may be a subfolder, so do **not** check `cwd == git_root()`.

1. Require cwd be inside a git repo (`git_root(cwd) is not None`); keep the
   existing "not inside a git repository — run `git init` first" guard, because
   write transitions need git.
2. Scaffold `docs/<component>/` skeletons as today (idempotent) — same component
   selection as today (all three by default, or the named subset).
3. Write `tcw-config.yaml` at cwd if absent (the **backfill**). **Do not stage
   it** — `init` today creates the `docs/` skeleton (with `.gitkeep`s) *without*
   staging; the sentinel follows the same create-don't-stage rule, so `init`
   never touches the git index. (Scaffold-then-sentinel ordering: a sentinel only
   appears once the skeleton exists.)
4. Report. **The report must be deterministic across runs** — print the sentinel
   path identically whether it was just created or already present (e.g. always a
   `tcw-config.yaml` line), so the existing byte-equal-stdout idempotency tests
   (§7) keep passing. Do **not** vary the output on "written vs. already there".

Re-running is idempotent and backfills a missing sentinel — the migration path
for existing single-node repos; a half-finished `init` is simply re-run.

**Behavior change (called out):** `tcw init` now acts on **cwd**, not the git
root. At a repo root cwd == git root, so single-repo workflows are unaffected; in
a subfolder it creates a subfolder node — the intended new capability.
`ponytail:` cwd-driven placement; add an explicit `--path` argument only if this
proves a footgun in practice.

### 3.4 Detection-failure message (single message — simplified)

Both reviews flagged the original two-message design (distinguish "no sentinel"
vs. "sentinel present but component missing") as over-engineered: `find_node`
returns a bare `None` for both, so distinguishing them would need a richer return
type plus branching at ~8 guard call sites — for marginal UX gain. **Dropped.**

Instead, keep `find_node → Path | None` and improve the existing per-component
guard wording to one line that covers both cases, e.g.
`tcw <group>: no tcw <component> node here — run \`tcw init\` (in the project
folder) to create one.` This stays the smallest change (§1) and touches only the
guard strings, not detection.

## 4. What this unlocks (no new code)

With `node_root` correctly resolving to `project-b/`, the existing taxonomy
federation resolves relative paths against it: `project-b/docs/taxonomy/
config.yaml` with `extends: {base: ../project-a}` resolves to
`project-a/docs/taxonomy` and inherits its terms. The inheritance payoff is a
**consequence of fixing detection**, not separate machinery.

**Why it works mechanically:** `FsTaxonomyStore.__init__` resolves each `extends`
path against `self.node_root` (`= root.parent.parent`, i.e. the subfolder once
detection is fixed) — see `fs.py` `ext = (self.node_root / repo_path / "docs" /
"taxonomy")`. The same holds for capabilities `check`, whose `Subject` refs
resolve through the taxonomy store opened at the same node root
(`capabilities/cli.py` `_taxonomy_for`). So fixing detection lights up both
taxonomy `list`/`get` **and** capabilities cross-component `check` in the
monorepo layout (covered by tests §7).

## 5. Scope boundary (explicit)

- **In:** the sentinel, `find_node_root`/`find_node`, `run_init` at cwd +
  backfill, this repo's own migration, tests, docs sync.
- **Out (SP2):** `child_nodes`/`parent_node` keep their current git-repo-based
  discovery, so sibling **subfolder** nodes will *not* appear in `tcw work nodes`
  yet. SP1 must **not regress** the existing nested-git-repo recursion behavior.
- **Out (SP3):** any inheritance beyond per-project taxonomy `extends`
  (capabilities inheritance, implicit/repo-level inheritance).

**Known SP2 debt — divergent node definitions (name it, don't fix it here).**
After SP1 two definitions of "node" coexist:
- *current node* (`find_node`/`find_node_root`) = nearest folder with a sentinel;
- *cross-node discovery* (`child_nodes`/`parent_node`, used by `tcw work nodes`/
  `reconcile`/`delegate`/`escalate` via `recursion.py`) = git-work-tree-root with
  `docs/work/`.

For the **existing nested-git-repo** layout these still agree (each repo is a git
root), so there is **no regression**. For the **new subfolder** layout they
diverge: from `project-b`, `parent_node` walks to the monorepo git root (no
`docs/work/` → `None`) and `child_nodes` sees no descendants, so `tcw work nodes`
shows no parent/children. This is accepted, expected, and resolved by SP2. The
implementation plan must state this invariant so it isn't mistaken for a bug.

**Unaffected:** the worktree machinery (`add_worktree`/`ensure_worktree_ignored`/
`merge_worktree`) takes an explicit `node_root` from the store, never from
`find_node`, so it is orthogonal to this change.

## 6. Migration of this repo

Implementation adds `tcw-config.yaml` at this repo's root so its own `tcw work`
keeps resolving after the change. No chicken-and-egg: during implementation the
new code runs locally, so the file is generated by the new `tcw init` (or written
directly) and **committed in the same change** as the code — landing together,
serving as dogfooding.

## 7. Tests (pytest over `tmp_path` git repos)

1. `find_node_root`: nearest sentinel; nested → innermost; `None` when none up to
   root; matches a *file* (a dir named `tcw-config.yaml` does **not** match);
   resolves a symlinked `start`.
2. `find_node(component)` returns the node iff sentinel present **and**
   `docs/<component>/` exists; `None` otherwise.
3. CLI prints the improved single "no tcw <component> node here — run `tcw init`"
   message on a sentinel-less directory.
4. `tcw init` writes the sentinel at cwd, is idempotent, backfills a missing
   sentinel in a repo that already has `docs/` but no sentinel, and **does not
   stage** it (index stays clean). The **byte-equal-stdout** idempotency
   assertions in `test_taxonomy.py`, `test_work.py`, and `test_smoke.py` must
   still hold (report determinism, §3.3).
5. **Integration (taxonomy):** a two-project monorepo (`project-a`, `project-b`,
   each with a sentinel + `docs/`), run from inside `project-b`, with
   `extends: {base: ../project-a}` — assert project-a's terms resolve through
   project-b's taxonomy store.
6. **Integration (capabilities):** in the same monorepo, a `project-b` capability
   with a `Subject:` pointing at a `project-a` term passes `capabilities check`
   (proves cross-component resolution against the subfolder node root).
7. **Test-fixture migration (BLOCKER from review):** the rewrite makes every
   `chdir + main()` test route through the new `find_node`, so **all five**
   CLI-driven fixtures must create a sentinel or every such test fails at the
   guard. Affected: `tests/test_work.py`, `tests/test_recursion.py`,
   `tests/test_taxonomy.py`, `tests/test_skill_flow.py`,
   `tests/test_capabilities.py`. Prefer a single shared helper
   (`make_node(tmp_path, components=...)` that writes the sentinel + scaffolds, or
   route every fixture through `run_init`) over hand-editing each fixture.
8. Regression: the `test_recursion.py` nested-git-repo cross-node behavior still
   passes once its fixtures carry sentinels.

## 8. Documentation sync (CLAUDE.md triggers)

Verified line references:

- **README.md:145** — "`tcw init` operates on the current git work-tree…" → now
  "operates on the **current directory** (writing a `tcw-config.yaml` marker),
  still refusing outside a git repo." **Must update.**
- **README.md** — add a short multi-project subsection: the layout example, the
  sentinel concept, `tcw init` per subfolder, and "taxonomy `extends` works
  across sibling subfolder projects." **Add.**
- **README.md:309 & :379** ("Any git repo with a `docs/work/` is a node") —
  these describe **cross-node discovery**, which stays git-based until SP2, so
  they remain accurate. Apply only **surgical** wording so they don't contradict
  the new sentinel-based *current-node* definition (distinguish "current node =
  sentinel" from "cross-node discovery = git repos, until SP2"). Do **not**
  blanket-rewrite them to "sentinel".
- **docs/release-notes/upcoming.md** — plain-language: shared docs repo with
  subfolder projects; `tcw init` makes the current folder a node.
- **docs/changelogs/upcoming.md** — Added/Changed entries with the commit range.
- **skills/tcw-work/** — SKILL.md doesn't define node=git-repo (only references
  "sub-project nodes"); verify `skills/tcw-work/docs/cross-node-epic.md` — its
  cross-node node=git-repo definition stays valid for SP1. Add only that
  `tcw init` now marks the current folder a node.
- **AGENTS.md** — verified: no literal "node = git repo" line (only abstract
  node-relation vocabulary). **Likely no change**; confirm during sync.
- Detection-failure guard message text (§3.4).

## 9. Versioning

This is a **user-facing CLI behavior change** (`tcw init` targets cwd; a sentinel
is now required to detect a node). Per AGENTS.md it warrants a **minor** bump
across the 5 version-bearing files via `scripts/cut_version.py`. Write the
`upcoming.md` entries (§8) as part of this work; the actual cut is the usual
separate release step, not part of this item.

## 10. Dual review

Reviewed by an independent subagent and the local LLM (`bllm-review-plan`).
Folded in: the 5-fixture test-regression scope (§7.7), report determinism vs.
byte-equal-stdout tests (§3.3, §7.4), simplifying §3.4 to one message,
create-don't-stage the sentinel (§3.3), `find_node_root` robustness — resolve /
`is_file()` / FS-root fixpoint (§3.2), the SP2 divergent-node-definition invariant
(§5), reserving the sentinel filename at any depth (§3.1), detection-never-parses
(§3.1), and verified doc/version obligations (§8–9). Rejected: replacing YAML with
a plain `.tcw-node` marker (the user chose YAML to carry future config), and
mount-boundary/symlink-loop/permission hardening of the upward walk (a `.parent`
walk to the FS-root fixpoint cannot loop — over-cautious for this scope).
