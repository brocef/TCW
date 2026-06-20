# Cross-node recursion (work Spec 2) — spec

**Status:** spec ✓ · build ☐
**Delivers:** the cross-node **recursion layer** on top of the single-node `tcw work` core — node topology, epics + `initiative:` back-pointers, `reconcile`, the escalate/delegate inbox channel, and `tcw work start --worktree` (+ the checkout-ownership rule).
**Depends on:** Phase 5 Spec 1 (the single-node `WorkStore` + `FsWorkStore` + CLI — already shipped).
**Source of truth:** this doc, derived from [`phase-5-work`](../../../plan/phase-5-work.md) A.2/A.6/A.8/A.11, Part C #2, and [`phase-6-beyond`](../../../plan/phase-6-beyond.md). Framework rules: [`../../../../AGENTS.md`](../../../../AGENTS.md).

> Scope is **mechanism only**. The *judgment* that drives these mechanisms — when to decompose, when to escalate, canonical-wording coordination, the lifecycle handshake, recursive process-inbox/resume — is the Spec 3 skill layer (A.10 mechanism-vs-judgment). The product-layer capability *ledger flip* is also Spec 3; Spec 2 only **surfaces** capability deltas read-only.

---

## 1. Scope

**In (this spec):**

- Node topology — discover a node's parent and child nodes.
- Epics — `initiative:` back-pointer on tasks; optional `type: epic` board sugar.
- `reconcile` — scan children for an initiative, write a consolidated read-only rollup into the epic.
- Inbox channel — `delegate` (write down) / `escalate` (write up), bounded to `inbox/`.
- Worktrees — `start --worktree`, the split checkout-ownership rule, and `complete`'s merge-guard + teardown.
- CLI: `nodes`, `reconcile`, `delegate`, `escalate`; flags `new/edit --initiative`, `new --epic`, `start --worktree`.

**Out (Spec 3 skill layer):** the `tcw work` driving skill; when-to-decompose / when-to-escalate / when-to-resume judgment; the product-layer capability ledger flip on epic completion; canonical-wording coordination over the inbox channel; recursive process-inbox.

**Out (other specs):** remote `WorkStore` adapters (additive, the interface already allows them); the hard DoD gate (deferred hook).

---

## 2. Architecture stance (the litmus test)

The single-node `WorkStore` ABC stays **single-node and untouched**. Cross-node is a **layer above it**, never new interface methods. The litmus test — *"could a non-filesystem store implement this?"* — drives the placement of every piece:

| Mechanism | Realization | Where it lives | Remote analog |
|---|---|---|---|
| node topology (parent/children) | directory walk | FS-local, `fs.py` (beside `find_node`) | tracker hierarchy / project links |
| `reconcile` *(read)* | node-walk + per-node `WorkStore.query` | recursion layer (`recursion.py`) | one epic-link query |
| `reconcile` *(write rollup)* | direct file I/O into the epic body | recursion layer (FS-flavored) | additive body-update primitive |
| `delegate` / `escalate` | write a request doc into a node's `inbox/` | recursion layer | assign / notify |
| worktrees | `git worktree` | FS-local | n/a (FS bonus) |

The recursion layer talks to each node through the **abstract `WorkStore`** for per-node reads; only node *discovery* and worktrees are FS-flavored (A.2 lists both as "beside the interface"). Because we ship only `FsWorkStore`, the recursion layer's realization is FS-flavored today; a future remote recursion layer is purely additive. **No method is added to `WorkStore` that only the FS adapter could honor.**

`reconcile`'s *read* (per-node `query` filtered by `initiative`) is interface-clean. Its *write* (the rollup into the epic's `content.md`) is direct file I/O in the recursion layer — `WorkStore` exposes no body-update primitive (only `create` writes `content.md`, fs.py), so the rollup-write stays an **FS-adapter capability**, not a smuggled interface method; a remote recursion layer would add a body-update op (additive). Likewise the worktree guard/teardown (§3.4) is a **CLI/recursion-layer wrapper around the unchanged concrete `WorkStore.complete()`** — never a new param on, or override of, the core method.

The four-status state machine is **unchanged**. An `initiative` is a *reference*, not a status; an epic is an ordinary work item that tasks point at.

---

## 3. Components

### 3.1 Node topology (FS-adapter-local, `tcw/store/fs.py`)

Two helpers alongside the existing `git_root` / `find_node`:

- `child_nodes(root: Path) -> list[Path]` — the **nearest descendant** directories that are a git work-tree (`git -C <dir> rev-parse --show-toplevel` equals the dir) **and** contain `docs/work/`. Descent **stops at each found node** (a child's own children are *its* children, not this node's — A.2). Excludes *this* node's own linked worktrees: a candidate is the same logical node (not a child) when its `git -C <dir> rev-parse --path-format=absolute --git-common-dir` equals `root`'s. **Both paths are `--path-format=absolute` then `.resolve()`d before comparison** — `--git-common-dir` is cwd-relative by default, and a naive compare would fail to exclude (yielding a false child). A genuine nested independent repo resolves to its *own* `.git`, so it is correctly kept.
- `parent_node(root: Path) -> Path | None` — the **nearest ancestor** directory (above `root`) that is a node, or `None` at the root.

These are FS-local functions, not `WorkStore` methods (A.2: "node-detection by directory walk" is beside the interface).

### 3.2 Recursion layer (`tcw/work/recursion.py`)

A new module of orchestration functions, testable without the CLI. Each takes node roots / opens `FsWorkStore` per node — depending only on the abstract store for per-node reads.

**`reconcile(node_root, epic_slug) -> Rollup`**

1. Resolve the epic item in the current (orchestrator) node; **error** if the slug doesn't resolve (no silent empty rollup).
2. Gather the **task set**: for `self` + each `child_nodes(node_root)`, open `FsWorkStore` and `query()` items whose `state.yaml` `initiative == epic_slug`.
3. Build the rollup:
   - **slice table** — one row per task, **keyed by (node-relative-path, slug)** since slugs are minted per-node and can collide across children (fs.py `_unique_slug` is node-bounded). Columns: `node · slug · status · phase · unresolved-blockers`. Row order is **deterministic**: group by node path, then `topo_order` within node (stable) — required for the byte-identical claim below.
   - **capability deltas** — surface each task's `capabilities.yaml`. The tool still treats it as a **not-acted-on blob** (no ledger write), but for display it expects an *optional top-level list of `{file, heading, from, to}` mappings*; it lists those and **tolerantly skips/echoes** anything non-conforming (the `_safe_yaml` degrade-don't-crash idiom, fs.py:578). **Read-only**: reconcile never writes any capabilities ledger.
   - **next-action hint** — the ready (unblocked, non-completed) tasks, in `topo_order`.
4. Write the rollup into the epic's `content.md` inside a managed block:

   ```
   <!-- tcw:rollup -->
   …generated table + deltas + next-action…
   <!-- /tcw:rollup -->
   ```

   Replace the block matched by an **anchored regex** on the two markers; if absent, append it (the append path must not duplicate on the second run). **Idempotent** — re-running with an unchanged task set yields a byte-identical block (relies on the deterministic ordering above + fixed formatting + trailing-newline-safe replacement). Hand-written prose outside the markers is preserved. Stage-only (a `--commit` flag may ride with related changes; default stage-only, matching B.7).

**Child folders are ground truth; the rollup is a consolidated interpretation** (A.6) — regenerated, never the source.

**`delegate(node_root, child_ref, title, body) -> Path`** — `child_ref` is the child's **path relative to `node_root`** (matching the `from:` convention); error listing valid children on a miss, error on ambiguity. Write a dated request doc into `<child>/docs/work/inbox/<YYYY-MM-DD-slug>.md` with front-matter `from: <origin rel-path>`, `initiative:` (if given). Create `inbox/` if missing; on filename collision suffix `-2`, `-3`, … (the slug idiom). Body comes from the arg or, if empty, stdin (reuse `_stdin_body`). Returns the written path.

**`escalate(node_root, title, body) -> Path`** — same, into `parent_node(node_root)/docs/work/inbox/`; errors if there is no parent. Prints the reminder to start an orchestrator session (A.6: a repo-spawned agent flags the human rather than driving the parent directly).

**Boundary invariant (enforced):** `delegate`/`escalate` write **only** into a node's `inbox/`. They never create/transition items in another node's `backlog`/`active`/`completed`. A raw request doc in `inbox/` is *not* a work item folder, so the receiving node's `query()`/`board()` ignore it until its triage (a Spec 3 skill) turns it into an item — no conflict with the single-node tool.

### 3.3 Epic / initiative fields (`state.yaml`)

- **`initiative: <epic-slug>`** — a task's back-pointer to its epic, a cross-node reference by stable id (A.6). Set at `new --initiative <slug>` or `edit --initiative <slug>` (clear with `--initiative ""`). It is an **unresolved free-text back-pointer at set-time** — a task lives in a *child* node whose store (`_find`, node-bounded, fs.py:559) cannot resolve a slug that lives in the *parent*, so it is not validated where it's set (like an `external` blocker). Validation happens **only at `reconcile`**, when the orchestrator scans its children and matches `initiative == epic_slug`. Never a path.
- **`type: epic`** — *optional* board-annotation sugar set by `new --epic`. `reconcile` operates on **any** slug by scanning for `initiative == slug`, so epic-ness is **not load-bearing**. This is the only meaningful value of `type`; ordinary items omit it.

Reconciles the apparent A.6 (`type: epic`) vs. B.4 ("no type field") conflict: there is **no mandatory `type` field** and the product/technical/meta axes still classify; `type` is optional recursion sugar that only ever holds `epic`.

### 3.4 Worktrees + the checkout-ownership rule (A.8)

The rule, resolved (the "split" model): **status transitions are owned by the node's primary checkout (trunk); in-flight item edits are owned by the worktree branch, with a single owner per phase so the merge-back can't conflict.**

- **`start <slug> --worktree`:**
  1. On the **primary checkout**, do the `backlog|inbox → active` `git mv` **and** record `worktree: .worktrees/<slug>` + `branch: work/<slug>` in `state.yaml`, then **commit** both. This is a **deliberate exception to the stage-only default** (B.7): `git worktree add` branches from a *commit*, so a staged-but-uncommitted rename would leave the new worktree checked out at the *pre-mv* tree (item still at `backlog/<slug>`) — the worktree must branch from a commit that already has the item at `active/<slug>` with its fields set. `--worktree` therefore implies `--commit` for this transition.
  2. `git worktree add .worktrees/<slug> -b work/<slug>` from that commit (trunk `HEAD`). `.worktrees/` lives at the node root and is **added to the node's `.gitignore`** (a linked worktree dir is untracked otherwise and would clutter/be staged).
  3. Print the worktree path (the agent works there). The board stays coherent — `ls active/` on trunk is authoritative.
- **During active work — single-owner invariant:** all item `state.yaml`/document edits (`tcw work edit`: phase, blockers) happen on the **worktree branch**. Trunk performs **no `set_field` on this item** between worktree creation and merge-back. Because the branch's base commit already carries `worktree`/`branch` (step 1) and trunk doesn't touch the file, the merge-back of `active/<slug>/state.yaml` is **clean by construction** (`set_field` rewrites the whole map, so two concurrent writers *would* conflict — the invariant is what prevents it).
- **`complete <slug>`** (a CLI/recursion-layer wrapper around the unchanged concrete `WorkStore.complete()`):
  1. Integrate first: the operator merges/PRs `work/<slug>` into trunk (bringing code + the branch's `state.yaml` edits). `complete` does **not** auto-merge and does **not** assert ancestry — `git merge-base --is-ancestor` gives **false refusals on squash- and rebase-merges** (the common PR flows create commits with no parent link to the branch), which would just train operators to `--force`. "No further code changes" stays a **DoD acknowledgment** (the `reviewed` / integrated checklist item), not a brittle git assertion.
  2. Normal DoD gate + `active → completed` `git mv` on trunk (post-merge, so trunk holds the merged `state.yaml`).
  3. **Best-effort teardown:** `git worktree remove .worktrees/<slug>` (which itself refuses on a dirty worktree — the real safety net against losing uncommitted work) and delete the `work/<slug>` branch. Teardown failure warns, doesn't abort the completion.

Concurrency safety is still dispatch-discipline + worktrees, not a lock (A.8): one writer per node for the primary `docs/work/` tree; each active item isolated in its own worktree for code. If `git worktree add` (step 2) fails, the item is left `active` on trunk with its fields set — re-runnable; no rollback machinery (A.8 does not guarantee transition atomicity).

### 3.5 CLI surface (additions only)

```
tcw work nodes                                  list this node's parent + child nodes
tcw work reconcile <epic-slug> [--commit]       scan children → write rollup into the epic
tcw work delegate <child> "<title>"             write a request into a child node's inbox/   (body via stdin)
tcw work escalate "<title>"                      write a request into the parent node's inbox/ (body via stdin)
tcw work new "<title>" [--epic] [--initiative <slug>] [--blocked-by <refs>]
tcw work edit <slug> [--initiative <slug>|""] [--blocked-by …] [--blocks …] [--unblocked-by …]
tcw work start <slug> [--worktree] [--force]
```

Existing subcommands and behavior are unchanged.

---

## 4. File-format additions

- **`state.yaml`** gains optional `initiative` (string), `type` (`epic`), `worktree` (path), `branch` (string). All absent on ordinary single-node items — back-compatible with Spec 1 items.
- **`content.md`** (epics) gains the managed `<!-- tcw:rollup --> … <!-- /tcw:rollup -->` block, owned by `reconcile`.
- **Inbox request doc** (`inbox/<dated-slug>.md`): front-matter `from:` / `initiative:` + the title and body. A plain file, not a work-item folder.

---

## 5. Testing (`tests/test_work.py` or a new `tests/test_recursion.py`)

pytest over **nested `tmp_path` git repos** — a parent node with two child nodes, each created with **`git init --initial-branch=main`** (a default branch must exist before `git worktree add`), `user.name`/`user.email` set, and `docs/work/` initialized:

- **topology** — `child_nodes` finds both children, stops at node boundaries; **excludes the parent's own linked worktree** *and* **keeps a genuine nested independent repo** (both placed under the node, to prove the `--git-common-dir` compare has no false positive or false negative); `parent_node` resolves up and returns `None` at the root.
- **reconcile** — gathers tasks across children + self by `initiative`; rows keyed by (node, slug) so **two children with the same slug both appear**; rows carry correct status / blockers; capability deltas surfaced from a conforming `capabilities.yaml` **and a malformed blob degrades gracefully** (no crash); managed-block rewrite is **byte-identical idempotent** (assert before/after content) and preserves surrounding prose; never mutates a capabilities ledger; unknown epic slug **errors**.
- **inbox channel** — `delegate` lands in the named child's `inbox/` (creating it if absent), `escalate` in the parent's, with correct `from:` front-matter; filename collision suffixes; **boundary** — neither ever writes another node's `backlog`/`active`/`completed`; `escalate` at the root errors.
- **worktrees** — `start --worktree` commits the trunk mv + fields and the **new worktree actually contains the item at `active/<slug>/`** (the blocker-1 regression); records `worktree`/`branch` in `state.yaml`; an `edit` on the work branch **merges back to trunk without conflict**; `complete` post-merge moves to `completed/` and tears down the worktree + branch; teardown failure warns but completion still succeeds; `.worktrees/` is git-ignored.
- **fields** — `new --epic` sets `type: epic`; `new/edit --initiative` sets and clears the back-pointer; reconcile works on a slug with no `type: epic`.

---

## 6. Documentation sync (per CLAUDE.md)

Implementation must include these doc tasks (triggers expected to fire):

- **`README.md`** [Public-API] — document `nodes`, `reconcile`, `delegate`, `escalate`, and the new `new/edit/start` flags; a short "cross-node / epics" section.
- **`docs/release-notes/upcoming.md`** [Public-API] — plain-language note: epics across repos, rollups, delegate/escalate, worktree-isolated work.
- **`docs/changelogs/upcoming.md`** [Any-Code-Change] — Added/Changed, with the commit-hash range.
- **`docs/plan/phase-6-beyond.md`** — mark the "Cross-node / recursion (work Spec 2)" item as built.
- **`docs/plan/phase-5-work.md`** — reconcile B.4 ("no type field") with A.6 (`type: epic`): note `type` is optional recursion sugar, only-value `epic` (§3.3 above).

---

## 7. Build checklist

1. `child_nodes` / `parent_node` in `fs.py` (+ absolute `--git-common-dir` worktree-exclusion).
2. `state.yaml` fields (`initiative`, `type`, `worktree`, `branch`) via `set_field`; `new`/`edit` flags.
3. `recursion.py`: `reconcile` — (node, slug)-keyed deterministic rollup + idempotent managed-block writer + tolerant capability-delta surfacing.
4. `recursion.py`: `delegate` / `escalate` (+ boundary invariant, inbox-create, collision suffix, stdin body).
5. `start --worktree` (commit-before-`worktree add`, `.gitignore` the worktree dir, single-owner invariant); `complete` wrapper (DoD-ack integration, best-effort teardown — no ancestry guard).
6. CLI wiring: `nodes`, `reconcile`, `delegate`, `escalate`, new flags.
7. Tests (§5).
8. Documentation sync (§6).
