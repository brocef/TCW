# Two tracker create runs at once can make two tickets for one item

`tcw work tracker create` checks for an existing binding, then creates, then
records the key. Two runs overlapping on the same item — two people, or a sweep
and a named run — can both pass the check before either records anything, and
both create a ticket. The second `created` record then overwrites the first, so
one of the two tickets is left in the tracker with nothing naming it.

Nothing reserves the item before the create request goes out. A fix needs either
a reservation written and read under the sidecar's revision before the tracker
is called, or a search of the tracker for a ticket already matching the item
before creating one.

TCW never deletes a ticket, so the cost is a duplicate somebody closes by hand.

## Origin

Reported by Codex during the review of
`2026-09-15-add-tcw-work-tracker-create-to-make-and-bind-a-ticket-for-an-existing-item`
and deferred there as needing its own change: every fix for it is a new
mechanism rather than a correction to what that item built.

## References

- `tcw/work/cli.py` — `_create_one`, the check-then-create-then-record sequence
