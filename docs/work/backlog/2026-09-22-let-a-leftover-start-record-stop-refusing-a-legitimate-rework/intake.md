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

## Added 2026-09-30 — merged from inbox

Merged at triage by the maintainer's decision: a third leftover-start-record defect
in the same code, filed separately as
`2026-09-29-a-plain-binding-s-stuck-start-record-never-clears.md`. Kept verbatim:

#### Inbox manifest

- `2026-09-29-a-plain-binding-s-stuck-start-record-never-clears.md`

#### Inbox body

### A plain binding's recorded start never clears once its ticket has moved on

Found verifying `2026-09-29-refuse-a-catch-up-rework-whose-ticket-is-already-past-the-item`.

On a tracker binding **without** `catch-up`, a recorded start (from an outage
during `tcw work start`, say) whose ticket has since been moved on to In Review
ends in a conflict on every `tcw work tracker sync`. The workflow "offers no
transition named 'Start Progress'" from there. Under strict mode, that record
then refuses later moves with "run sync first".

That item fixed the same stuck record for legacy `catch-up` bindings: a `sync`
replaying a still-owed start, with the ticket held by this account above an
active item and not done, is held and the record dropped, as a live start is.
Plain bindings reach `assess_move` with no window instead. Decide whether the
same held rule belongs there (`tcw/tracker/sync.py`, `deliver`).
