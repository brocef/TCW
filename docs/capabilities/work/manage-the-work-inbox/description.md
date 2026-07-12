As a user, I inspect raw work requests with `tcw work inbox list` and
`tcw work inbox show <entry>`, then accept a request into the formal backlog
with `tcw work inbox accept <entry> [--title <title>]`.

Inbox entries remain permissive intake packages rather than work items. An
entry may be a standalone file or a folder containing an `INDEX.md` or
`INDEX.txt` request plus related resources. Accepting an entry creates a
backlog work item, preserves its resources as named attachments, generates the
durable `initial-request.md`, and consumes the original inbox entry.
