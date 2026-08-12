As a user, I inspect raw work requests with `tcw work inbox list` and
`tcw work inbox show <entry>`, then accept a request into the formal backlog
with `tcw work inbox accept <entry> [--title <title>]`.
I run `tcw work inbox path` to print the absolute, resolved inbox folder inside
the active, configuration-aware work store.

Inbox entries remain permissive intake packages rather than work items. An
entry may be a standalone file or a folder containing an `INDEX.md` or
`INDEX.txt` request plus related resources. Accepting an entry creates a
backlog work item, preserves its resources as named attachments, records what
arrived as the item's durable `intake.md` — the entry body, a manifest naming
every preserved resource and the entry it was accepted from, and a note in place
of a primary resource that is not text — and consumes the original inbox entry.
Accepting no longer writes the item's request: what the entry said is preserved
as raw intake, and the `request` stage is still to run.
