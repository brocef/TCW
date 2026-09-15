# Outcome — Confirm directory renames during the worktree merge-back

Implemented on the **existing** branch
`work/2026-08-12-honor-the-configured-work-path-at-every-work-store-call-site`,
at the user's direction: the bug was discovered from that item's own closeout, and
putting both on one branch removes the cross-branch `tcw/store/fs.py` question
entirely. This item's own lifecycle artifacts stay on `main`.

## What shipped

### Task 1 — reproduce the stop as a failing test (`6e22a56`, committed red)

`tests/test_recursion.py` gains `_submit_then_complete_a_worktree_item` plus two
tests built on it:

- `test_complete_merges_across_a_transition_rename` — start `--worktree`, **add**
  `outcome.md` under `docs/work/active/<slug>/` and `feature.py` at the repository
  root, commit on the branch, `submit`, `complete`.
- `test_complete_merges_across_a_rename_despite_local_git_config` — the same flow
  in a repository whose own config sets `merge.directoryRenames=conflict`.

Both reproduced the reported failure exactly, which was the plan's stop condition:

```
tcw work complete: merge of work/2026-08-13-ship into the primary checkout failed;
branch left intact — resolve and re-run:
CONFLICT (file location): docs/work/active/2026-08-13-ship/outcome.md added in
work/2026-08-13-ship inside a directory that was renamed in HEAD, suggesting it
should perhaps be moved to docs/work/review/2026-08-13-ship/outcome.md.
```

Committed red deliberately, per the plan: the reproduction is the evidence, and
the fix is a three-line diff that would be unreviewable on its own.

### Task 2 — decide the rename behavior at the invocation (`b3fa418`)

`merge_worktree` (`tcw/store/fs.py`) now passes
`-c merge.directoryRenames=true` on its `git merge`. The branch-existence guard,
the `--abort` on failure, the error text, and the `None`-on-success contract are
untouched. The docstring's stale premise — that ordering the merge before
`complete`'s own rename means "no rename/modify overlap" — was corrected: it
avoids *that* rename, not one an earlier transition left behind.

Criteria evidence:

- **5 (fail closed).** `git diff 6e22a56..HEAD -- tests/test_recursion.py` returns
  **0 lines**: the fix commit changed no test at all, so
  `test_complete_aborts_on_merge_conflict` passed on its own rather than being
  edited to accommodate the change.
- **8 (single override).** `rg -n '"-c",' tcw --glob '*.py'` → exactly one hit,
  in `merge_worktree`, across 21 `git -C` call sites.
- **7 (branch-absent no-op).** Covered by a new test — see correction 4 below.

### Tasks 3-6 — documentation (`580f52f`)

`README.md`, `docs/release-notes/upcoming.md`, `docs/changelogs/upcoming.md`,
`skills/tcw-work/references/transitions.md`, and
`docs/capabilities/work/complete-a-work-item/description.md`. Nothing was added to
`skills/tcw-work/SKILL.md` — its body is at the 60-line budget
`test_the_router_stays_within_its_line_budget` enforces, and this detail is
conditional, so it belongs in the reference. That constraint was carried into the
plan from the previous item's experience and held.

## What the plan got wrong

1. **The blocker the plan insisted on had to be removed.** `plan.md`'s Notes
   argued the dependency on
   `2026-08-12-honor-the-configured-work-path-at-every-work-store-call-site`
   belonged in `--blocked-by` rather than prose, "so `start` enforces it". Its
   entire rationale was avoiding a conflict between two branches touching
   `tcw/store/fs.py`. Once both items share one branch that hazard does not exist,
   so the blocker was gating nothing and refusing `start` for no reason. Removed
   with `tcw work edit --unblocked-by` and committed separately before `start`.
   The reasoning was sound for the world the plan assumed; the assumption changed.

2. **Plan Task 2 Step 3 named a command that is not valid git.**
   `git diff tests/test_recursion.py::` was written as the check that the conflict
   guard stayed untouched. `::` is pytest node-id syntax, not a git pathspec, and
   the command would have silently diffed nothing useful. Replaced with a real
   proof: `git diff <red-commit>..HEAD -- tests/test_recursion.py`, which is empty
   precisely when the fix touched no test.

3. **Criterion 7 had no coverage, and the plan said it did.** Plan Task 2 Step 3
   asserted the branch-absent no-op was "already covered by the existing recovery
   test". Checking rather than trusting that: the only candidate,
   `test_already_integrated_tolerates_a_worktree_removed_externally`, passes
   `--already-integrated`, which skips `merge_worktree` altogether. Nothing
   exercised the guard. Added
   `test_merge_worktree_is_a_quiet_no_op_without_the_branch` (`724b036`).

4. **Task 7 Step 2's `pnpm install` note was already satisfied.** The plan assumed
   a fresh linked worktree; this one was already installed during the previous
   item, so the step was a no-op rather than a prerequisite.

Nothing in `spec.md` was contradicted. Every acceptance criterion was checkable as
written.

## Verification

Run with cwd = the worktree so `import tcw` resolves to worktree source rather
than the editable install pinned at the primary checkout.

| Check | Result |
| --- | --- |
| `python -m pytest -q` | **1250 passed** in 247s (was 1247; +3 new tests) |
| `pnpm exec tsc --noEmit` | clean |
| `pnpm run lint` | clean |
| `pnpm run test` | 50 passed, 11 files |
| `pnpm run build` / `check:build` | both built, no diff to committed assets |
| `tcw taxonomy check` | `taxonomy OK` |
| `tcw capabilities check` | `capabilities OK` |
| `tcw capabilities drift` | `no capability drift` |
| `tcw validate` | `validate OK` |
| `git diff --check` / `git status --short` | clean |

### Verification beyond the suite

The plan flagged that this item's tests only exercise the lifecycle folder, so the
widened behavior claimed in the release notes could not be proven by them. Checked
directly on a scratch repository rather than inferred:

```
main:    src/old/  →  src/new/          (directory renamed)
feature: src/old/b.py added             (under the old path)
merge:   create mode 100644 src/new/b.py
```

A branch-added file follows a renamed **code** directory into its new location.
The release-note wording describes that, not only the item folder.

The merge-back still produces an ordinary merge commit — not a squash or
fast-forward — so the merge remains inspectable and revertible, which is the
ground on which the spec accepted losing git's confirmation prompt.

## Notes

- This item's fix is not yet exercised by `tcw work complete` itself: the `tcw`
  on PATH is an editable install pinned to the primary checkout, which is still on
  `main`. It becomes live for real closeouts once this branch merges.
- The sibling item that surfaced this bug is in `review` on `main` and shares this
  branch. Merging the branch closes out both; that merge itself is the fix's first
  real use, and can be performed with the same
  `-c merge.directoryRenames=true` the fix now applies internally.
- Still untracked from this session: `reconcile --commit` raises an uncaught
  `subprocess.CalledProcessError` because `git_commit` is not in
  `tcw/work/cli.py`'s `_ERRORS`. Deliberately out of scope here; it needs its own
  item.
