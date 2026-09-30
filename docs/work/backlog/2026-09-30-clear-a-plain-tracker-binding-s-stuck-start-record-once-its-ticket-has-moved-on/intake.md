## Inbox manifest

- `2026-09-29-a-plain-binding-s-stuck-start-record-never-clears.md`

## Inbox body

# A plain binding's recorded start never clears once its ticket has moved on

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
