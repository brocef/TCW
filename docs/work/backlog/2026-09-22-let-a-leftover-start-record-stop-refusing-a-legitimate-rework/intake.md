# Two older defects found while reviewing C4

Both were found in the fourth review round of
`2026-09-16-compose-the-lifecycle-moves-from-claim-and-sync` (C4) and confirmed to
be older than that change, so they were deliberately kept out of it. C4's
`refined-outcome.md` records the deferral. Neither was reproduced against the fake
tracker; both were traced by reading.

## 1. A leftover start record makes a `rework` refuse itself

A sync record naming a `start` gives an empty window of statuses the ticket may be
in. The forward-only guard (`tcw/tracker/sync.py`, the check that a lifecycle move
never drags a ticket backwards) then compares the ticket's rung with the item's.
With the item active, a leftover start record, and the ticket in In Review and held
by the running account, the guard reports the move as held and says "a rework does
not move a ticket back".

Moving a ticket from In Review back to In Progress is exactly what a rework is, and
C4's own acceptance criterion 18d requires it. So the guard refuses the very move
the criterion demands, whenever a start record is still present.

The empty-window rule came in with C4's first round, but the interaction is with
the forward-only guard, which predates it.

## 2. The catch-up walk's re-entry looks unreachable

`tcw/tracker/sync.py:864-868` re-enters the walk for a catch-up binding. Reaching
it needs a sync record to be present, but a record makes `check_only` false, and
every non-`check_only` catch-up binding has already returned the walk earlier
(around `:771-783`).

If it really is unreachable, deleting it is the honest answer. If it is reachable
by some route the reader missed, that route needs a test, because nothing covers
it today.

## Notes

- Verify claim 1 with a probe before designing a fix. Claim 2 is a reading of
  reachability, so the first task is deciding which of the two it is.
- Line numbers are as of commit `8e9937b4` and will move.
