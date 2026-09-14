As a developer on a project whose work is assigned in Jira Cloud, I can take a
ticket from the terminal and get a TCW work item bound to it.

`tcw work tracker import <key>` claims the ticket and then creates a backlog item
for it. The claim moves the ticket through the configured claim transition, assigns
it to me if nobody had it, and reads the ticket back: only when it is now in the
status the claim leads to and assigned to me is an item created. A ticket assigned
to someone else, or already closed, is refused, and I am told who has it and where
it is. The item's intake holds the ticket's description with a link to the ticket,
its request is still mine to write, and it has no owner until I start it.

Running the same import again gives me the item I already have. If a run took the
ticket but stopped before the item existed, the next run finishes it without moving
the ticket again. `--part` lets one ticket become several items on purpose.
`tcw work tracker link <slug> <key>` claims a ticket for an item I already have, and
`tcw work tracker unlink <slug> --reason <text>` removes a wrong binding, keeps a
record of it with my reason, and leaves the ticket in Jira as it is.

The binding is written by these commands, not by hand, and the web app offers no
edit for it. It is never treated as proof of a claim: importing re-reads the ticket
and refuses when Jira disagrees.

Two limits are accepted rather than prevented. On a workflow that offers the claim
from every status, two people can both claim one ticket. And two runs by the same
Jira account at the same moment can both create an item. Keeping the ticket in step
with the item's lifecycle, and requiring tracked work, are separate capabilities
that are not yet built.
