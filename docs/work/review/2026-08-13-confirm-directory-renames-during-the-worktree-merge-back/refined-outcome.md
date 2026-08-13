# Refined outcome — Confirm directory renames during the worktree merge-back

**Decision: accepted.** Approved by the user on 2026-08-13 after review of the
per-criterion assessment.

## Evidence at acceptance

All eleven acceptance criteria in `spec.md` were met.

The two that were at risk of being met falsely, and how each was actually proved:

- **Criterion 5 — genuine conflicts still fail closed.** The risk was fixing the
  test rather than the code. `git diff 6e22a56..HEAD -- tests/test_recursion.py`
  returned **zero lines**: the fix commit changed no test whatsoever, so
  `test_complete_aborts_on_merge_conflict` passed unmodified.
- **Criterion 7 — branch-absent no-op.** The plan claimed existing coverage; there
  was none. The only candidate test passes `--already-integrated`, which skips
  `merge_worktree` entirely. Caught during assessment and closed with
  `test_merge_worktree_is_a_quiet_no_op_without_the_branch` (`724b036`) rather
  than waved through.

Verified on merged `main`:

| Check | Result |
| --- | --- |
| `python -m pytest -q` | 1250 passed |
| `tcw taxonomy check` | `taxonomy OK` |
| `tcw capabilities check` | `capabilities OK` |
| `tcw capabilities drift` | `no capability drift` |
| `tcw validate` | `validate OK` |
| `git status --short` | clean |

The behavior this fix widens — branch-added files following *any* directory
renamed on the primary checkout, code included — is not provable by this item's
tests, which only exercise the lifecycle folder. It was confirmed directly on a
scratch repository (`src/old/b.py` added on a branch landed at `src/new/b.py`
after the primary renamed the directory), so the release-note wording describes
observed behavior rather than inference.

## The fix proved itself at its own closeout

The merge that integrated this branch was exactly the operation the fix repairs:
`outcome.md`, committed on the branch under `docs/work/active/<slug>/`, landed at
`docs/work/review/<slug>/outcome.md` when merged with
`-c merge.directoryRenames=true`. Performed by hand only because the `tcw` on PATH
still resolved to the pre-merge checkout; from the next invocation onward
`tcw work complete` does this itself.

## Capability reconciliation

`capabilities.yaml` declares `changed: work/complete-a-work-item` — no `new:`
entry, so no status flip. The description was extended in `580f52f` to state that
an item whose folder moved mid-lifecycle is not a conflict, and that the
relocation extends to code directories. `tcw capabilities check` and
`tcw capabilities drift` both pass.

## Closeout

- **Route: merge**, into `main`, on the shared branch with
  `2026-08-12-honor-the-configured-work-path-at-every-work-store-call-site`. The
  two items were implemented on one branch at the user's direction, which is also
  why this item's blocker was removed before `start`.
- Documentation current at acceptance: `README.md`, both `upcoming.md` files,
  `skills/tcw-work/references/transitions.md`, and the capability description.
  Nothing was added to `skills/tcw-work/SKILL.md`, whose body sits at the 60-line
  router budget.

## Follow-ups

- **Unfiled:** the `reconcile --commit` / `_ERRORS` traceback, carried over from
  the sibling item and still not tracked.
- **Not pursued, and worth naming:** this item fixed the merge-back, not the
  lifecycle ordering that lets a transition on the primary checkout straddle
  artifacts committed on a branch. The spec scoped that out explicitly. If the
  ordering is ever revisited, this item's tests are the regression net.

## Notes

Three plan defects surfaced during implementation and are recorded in
`outcome.md`: a blocker whose rationale the shared-branch decision voided, a
verification command that was pytest node-id syntax rather than valid git, and the
false coverage claim for criterion 7. The third is the one that would have shipped
an unverified criterion.
