# A create response that never arrives leaves a ticket nothing can find

`tcw work tracker create` records the new key the moment the tracker reports it,
which covers a crash after the response. It cannot cover a response that never
arrives: if the connection drops after Jira has created the issue but before the
key reaches TCW, the ticket exists and nothing anywhere names it. A later run
creates a second one.

The only recovery is to ask the tracker whether a ticket for this item already
exists — the description already ends with "Tracked in TCW as `<slug>`", so a
search on that text would find it. That is a new lookup rather than a change to
the existing path.

## Origin

Reported by Codex during the review of
`2026-09-15-add-tcw-work-tracker-create-to-make-and-bind-a-ticket-for-an-existing-item`
and deferred there. The interrupted-run record that item added closes every
window except this one.

## References

- `tcw/tracker/create.py` — `create_and_place`, `on_created`
- `tcw/tracker/create.py` — `description_document`, which writes the slug into the ticket
