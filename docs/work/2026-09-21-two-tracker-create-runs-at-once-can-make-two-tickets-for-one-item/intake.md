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

## Folded in: 2026-09-21-a-create-response-that-never-arrives-leaves-a-ticket-nothing-can-find

_Merged here during the 2026-09-24 backlog cleanup; the source was closed as superseded._

## A create response that never arrives leaves a ticket nothing can find

`tcw work tracker create` records the new key the moment the tracker reports it,
which covers a crash after the response. It cannot cover a response that never
arrives: if the connection drops after Jira has created the issue but before the
key reaches TCW, the ticket exists and nothing anywhere names it. A later run
creates a second one.

The only recovery is to ask the tracker whether a ticket for this item already
exists — the description already ends with "Tracked in TCW as `<slug>`", so a
search on that text would find it. That is a new lookup rather than a change to
the existing path.

### Origin

Reported by Codex during the review of
`2026-09-15-add-tcw-work-tracker-create-to-make-and-bind-a-ticket-for-an-existing-item`
and deferred there. The interrupted-run record that item added closes every
window except this one.

### References

- `tcw/tracker/create.py` — `create_and_place`, `on_created`
- `tcw/tracker/create.py` — `description_document`, which writes the slug into the ticket

## Decision (2026-09-24 backlog cleanup)

The user wants duplicate tickets prevented, not just tolerated: "I'd prefer to prevent duplicate tickets from being created if possible." Searching the tracker for the "Tracked in TCW as `<slug>`" marker before creating covers both the lost-response case folded in above and two runs at once.
