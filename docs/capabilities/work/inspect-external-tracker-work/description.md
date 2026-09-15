As a developer on a project whose work is assigned in Jira Cloud, I can point TCW
at the Jira site in `tcw-config.yaml` under `work.tracker` — the site address, the
query that selects the tickets I could pick up, the names of the environment
variables holding my credentials, and the name of the transition that claims a
ticket — and then read those tickets from the terminal without changing anything
in Jira. Settings a node leaves out can come from its parent nodes
(`work/inherit-tracker-settings-from-parent-nodes`).

`tcw work tracker list` prints one row per ticket the query selects, with its
status, assignee and summary. `tcw work tracker show <key>` prints one ticket and
answers two separate questions about it:

- **claimable** — does this ticket, right now, offer the claim transition?
- **exclusive** — would the workflow refuse a second person claiming the same
  ticket?

The second answer is honest about what one ticket can show. A ticket already in
the status the claim leads to reveals a workflow that lets a second claimant in
(`not exclusive`), but never proves the opposite; that case, and any ticket not
yet claimed, reports `not determined`.

Credentials are named, never stored: TCW reads the variables only when it makes a
request, and no command or error prints them. A malformed `work.tracker` block is
reported by `tcw validate` without breaking the board, `tcw validate` never
contacts the tracker, and a project with no tracker configured loads none of this
code.

TCW does not tell me my claim transition's name is wrong, because a ticket not
offering it may simply not have reached that point yet or may already be claimed.
Claiming a ticket and binding it to a work item is a separate capability,
`work/manage-external-tracker-intake`; keeping the ticket in step with a work item
is `work/synchronize-external-tracker-work`, and requiring tracked work is
`work/require-tracker-backed-work`.
