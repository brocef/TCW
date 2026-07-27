# Refined outcome

## Verification decision

**Accepted.** Approved as part of the standing decision to drive the epic to
completion, use the resulting lifecycle, and refine it from experience under a
fresh work item.

## Evidence

- 809 Python tests pass (from 785). `tcw validate` OK.
- A real repository driven through all five transitions with a second item's
  `spec.md` left deliberately uncommitted: five commits, each containing exactly
  the moved item's two files as clean renames, and the unrelated file still
  untracked at the end.
- `--worktree` end to end: the branch carries its own status move, two non-empty
  commits, nothing left in the tree.
- **The feature closed its own submit.** Commit `e0033f4` was produced by the
  code under review, moving the item that built it.

## Capability reconciliation

- **Changed:** `work/start-a-work-item`, `work/submit-a-work-item-for-review`,
  `work/rework-a-reviewed-work-item`, `work/discard-a-work-item` — each now
  records that TCW commits the move, and names the two config keys.
- **Changed:** `work/complete-a-work-item` — the same, plus
  `--already-integrated` and the dropped Definition-of-Done storage.
- No new capabilities. Auto-commit changes how existing capabilities behave
  rather than adding one, and `--already-integrated` is a flag on completion, not
  a distinct thing a user can do.

## Open items accepted, not resolved

Both were raised in the outcome and are deliberately carried forward:

- **`tcw serve` reports a refused commit only to its own stderr.** Treating it as
  success is right for the UI — the item moved — but a browser user is not
  watching that terminal. The fix is the mutation response's `warnings` field,
  which those endpoints do not currently use. Assigned to child 2b, which already
  owes the web complete-modal a note that hooks did not run; the two are the same
  edit to the same surface.
- **`pr` was not consumed.** Child 1 added it predicting this child's
  `--already-integrated` would read it; the flag needs only `worktree` and
  `branch`. That was the stated condition for calling the field premature, so it
  is now on record. Not reverted: child 2b's policy work and child 4's stage
  documents may still use it, and removing a persisted field to re-add it later
  is worse churn than leaving one unread key. **If it is still unconsumed at epic
  close, it should be deleted then** — the same `phase`/`dod` pattern this child
  applied twice.

## Notes

Four spec claims were disproved by implementation and corrected in place. That
is now the pattern across both completed children — child 1 produced two, this
one produced four — and it is the strongest available argument for the epic's own
ship-then-refine sequencing: none of the six was findable by more careful
reading.

The one worth remembering is that `git commit` fails outright if **any** pathspec
matches nothing. It broke 67 tests the instant auto-commit was switched on, and
it would have broken every user's first transition on an item created but not yet
committed. Task 1 landing the plumbing with the flag off is what made that a
contained, obvious failure rather than a confusing one.

**A house pattern has now formed and should be written down once rather than
rediscovered:** dropping a persisted field means it stops being read, existing
items keep it inertly, and no migration pass is added. `phase` and `dod` both
took that shape. Child 4 owns stating it.
