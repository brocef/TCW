# Make the strict tracker gate refuse unfollowable moves, and allow child items

Under `work.tracker.strict: true`:

1. The gate (`authorize`) checks the ticket's assignee and status but not whether
   the workflow can carry the ticket to where the item is going. `submit` passes,
   the item moves, delivery records a conflict, and the next move is refused over
   that record.
2. A child item cannot be nested: `new --parent`/`--initiative` are refused, and
   `tracker import` takes neither.
3. A held item whose claim is still owed seemed to stay locked.
4. An epic started with `--worktree` before strict mode was turned on still
   merges its branch on complete.

## Notes

- From the intake (Jira TCW-19), triaged 2026-09-15. Written during an
  unattended run (2026-09-26); no requester to ask. References: asked; none
  beyond the intake.
- Part 3 was fixed after the intake was written (commits `b41cc5b2`,
  `42f28ce2`: `deliver` clears an open held item's record); this item adds the
  regression test only.
- The intake's cross-reference about `claim_refusal` points at an item since
  discarded, whose part moved to
  `2026-09-16-separate-claim-from-status-movement-in-the-tracker-verbs`
  (completed); nothing of it is done here.
