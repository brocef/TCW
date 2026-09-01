# Plan: Re-anchor a relative work.path at the node's counterpart inside the main worktree

Four tasks, ordered so `pytest` is green at every commit boundary. The
behaviour change is one function; the ordering risk is that the tests proving
"nothing else moved" must exist *before* the change, not after.

## Task 1 — Fixture and regression tests for the behaviour that must not change

**Modifies:** `tests/test_environment_hardness.py`

Add a fixture beside the existing `worktree_node` / `monorepo_worktree` helpers:

- `nested_node_worktree(tmp_path, work_path=None)` → `(repo, node_sub, wt)`.
  One git repo with a tcw work node at `apps/server`, a linked worktree of the
  whole repo at `<repo>/.worktrees/f` (following `monorepo_worktree`'s shape and
  using `WORKTREES_DIR`), and `work.path` written into the node's
  `tcw-config.yaml` when given. It must also create the target store directory
  tree (`inbox` + every entry of `WORKTREES`-adjacent `WORK_STATUSES`) so
  `FsWorkStore.open` can succeed, not merely `_local_root`.

Then a test class asserting the cases the change must leave alone, each
comparing `FsWorkStore._local_root` resolved from the primary checkout and from
the worktree:

- absolute `work.path`, node at `apps/server` — identical, both checkouts;
- absent `work.path` (the default), node at `apps/server` and at the repo root —
  each checkout gets its own `docs/work`, as today;
- relative escaping `work.path` (`../external/work`) on a node **at the repo
  root** — identical, both checkouts.

**Proves:** these three assertions pass on the unmodified tree. Run
`pytest tests/test_environment_hardness.py -k worktree` and confirm green
*before* Task 2 touches `fs.py`. Covers spec acceptance criteria 4 and 5.

## Task 2 — Gate the re-anchoring on escape and anchor at the node's counterpart

**Modifies:** `tcw/store/fs.py` (`FsWorkStore._local_root`, lines 2778-2795),
`tests/test_environment_hardness.py`

Replace the body per the spec's Design block: return early for an absolute
value; compute `resolved = (node_root / value).resolve()`; re-anchor to
`main / node_root.relative_to(top)` only when `node_root.is_relative_to(top)`
and `not resolved.is_relative_to(top)`.

Rewrite the docstring. The current one asserts the behaviour being removed —
"resolves against the main worktree root" — and must instead state the rule it
now shares with `FsProjectRegistry._target_path`, and say that only an escaping
path re-anchors and that a nested node anchors at its own counterpart. Cite
`tcw/store/project.py:322-334` as the sibling rule so the two stay tied.

In the same commit, add the three tests for changed behaviour:

- node at `apps/server`, `work.path: ../../../external/work` — worktree
  resolution equals primary resolution (spec criterion 1);
- node at `apps/server`, `work.path: docs/work` — from the worktree, resolves to
  `<wt>/apps/server/docs/work`, and equals what the same node resolves with no
  `work.path` at all (spec criterion 2);
- node at repo root, `work.path: docs/work` — from the worktree, resolves to
  `<wt>/docs/work`, equal to the default for that node (spec criterion 3).

Same commit as the code so the boundary is green; separating them would land a
red commit.

**Proves:** `pytest tests/test_environment_hardness.py` green, including
`monorepo_worktree` (spec criterion 6), and the three new assertions fail if
the `fs.py` change is reverted. Then `pytest` in full (spec criterion 7).

## Task 3 — Amend the two capability entries

**Modifies:** `docs/capabilities/` via `tcw capabilities` commands — never by
hand-editing the store.

- `cli/run-from-a-git-worktree` (cap-b47597): extend the body so the
  re-anchoring rule is stated of relative **locators and `work.path` alike**,
  and so "the node I operate on is the worktree — its `docs/work/` … are the
  checked-out ones" is true of a node with an explicit inside-staying
  `work.path`, not only of the default.
- `work/configure-the-work-store-location` (cap-46e036): qualify "a path
  relative to the owning project's primary checkout" — that holds for a path
  that leaves the checkout; one that stays inside belongs to the worktree, like
  the default. Link to `tcw://C/cli/run-from-a-git-worktree`.

Both stay **Supported**; no status flips and no new capability. Set each
entry's Planning doc to this item's slug where the field is empty or names an
older item, per the ledger convention.

**Proves:** `tcw capabilities validate` and `tcw validate` both exit 0, and
`tcw capabilities show` for each entry reads true against the Task 2 behaviour.

## Task 4 — Documentation Sync

**Modifies:** `README.md`, `docs/changelogs/upcoming.md`,
`docs/release-notes/upcoming.md`

Run the `documentation-sync` skill over the finished diff and evaluate every
declared entry. Predicted per entry:

- **`README.md`** — [Public-API] **fires.** Two passages:
  - line 203-204, "Relative paths are anchored to the owning project's primary
    checkout" — now true only of a path that leaves the checkout; qualify it.
  - lines 301-309, the linked-worktree paragraph — it states the escape rule for
    `connected-projects` locators only; say it covers `work.path` too, so the
    README stops implying the two differ.
- **`docs/changelogs/upcoming.md`** — [Any-Code-Change] **fires.** A `Fixed`
  entry naming `FsWorkStore._local_root`, both defects (the dropped node
  sub-path, the unconditional re-anchoring), and the alignment with
  `_target_path`.
- **`docs/release-notes/upcoming.md`** — [Public-API] **fires.** Plain language,
  no module names: a project whose work store is configured with a relative
  path now resolves the same store from a linked worktree, and a relative path
  that stays inside the checkout now stays with the worktree like the default.
  Credit GitHub issue #26.
- **`skills/<component>/SKILL.md`** — [Skill-Driven-Component] **predicted not
  to fire.** No CLI surface, model, lifecycle, or guardrail changes. The
  nearest text, `skills/tcw-work/references/commands.md:104-106` ("a configured
  `work.path` changes only the filesystem adapter location"), stays true.
  Confirm during the pass and record the no-change decision rather than
  skipping the entry silently.

**Proves:** every entry above evaluated with a decision recorded; `tcw work docs`
lists nothing unaddressed.

## Verification

Beyond the suite:

- **Manual worktree check** — the suite exercises `_local_root` directly; run
  `tcw work path` end-to-end from inside a real linked worktree of a nested
  node, both `work.path` shapes, to confirm the whole `open` ladder (not just
  the path computation) reaches the store. This is what the reporter actually
  ran, and `_open_at`'s directory validation sits downstream of the change.
- **The reporter's own reproduction** — his case is a node at `apps/server`
  with the store *outside* the repository. Reproduce that exact shape rather
  than only the in-tmpdir fixture, since the fixture's store is inside the repo.
- **Regression on the reporter's claim** — confirm no second `_local_root`
  exists (`grep -n "_local_root" tcw/`), so the fix is not silently half-applied
  to a copy nobody edited.
- Nothing here needs the store's own state, so no `tcw work` transition is part
  of verification.

## Notes

**Blockers:** none. Nothing else in the backlog touches `_local_root` or
`worktree_anchors`; checked against `tcw work list --all`.

**Litmus test.** Every task stays inside the filesystem adapter or its
documentation. No abstract store operation is added, renamed, or changed, so
the model a non-filesystem store implements is untouched — which is the correct
outcome for a defect about resolving a path on disk.

**Deliberately not planned:** extracting the counterpart expression now shared
by four sites. The spec's Non-goals explain why; if a fifth appears, that is
the moment.

**That moment arrived during implementation.** Rebasing onto main brought the
generalized `resolve_store` ladder and with it a second, character-identical
copy of the anchoring rule on `FsTreeStore._local_root` — the copy the reporter
described and this plan's spec had denied. Fixing one and not the other would
have left taxonomy and capabilities broken in exactly the way the work store
had just been repaired, so Task 2 grew a sibling: extract
`anchor_configured_path` and route both hooks through it, with the escape and
inside-staying assertions repeated for `FsTaxonomyStore` and
`FsCapabilitiesStore`. The Non-goal is withdrawn, not worked around.
