As a developer on a project whose work is assigned in Jira Cloud, I can take a
ticket from the terminal and get a TCW work item bound to it.

`tcw work tracker import <key>` claims the ticket and then creates a backlog item
for it. The claim moves the ticket through the configured claim transition, assigns
it to me if nobody had it, and reads the ticket back: only when it is now in the
status the claim leads to and assigned to me is an item created. A ticket assigned
to someone else, or already closed, is refused, and I am told who has it and where
it is. The item's intake holds the ticket's description with a link to the ticket,
its request is still mine to write, and it has no owner until I start it.

A ticket waiting in a status before the backlog, such as `Triage`, is claimable
once I name that status and the transition out of it under
`work.tracker.pre-backlog`: the import first takes it through that transition to
`statuses.backlog`, and tells me so, even when the claim afterwards fails. Without
the setting the refusal names it, and a Triage ticket already assigned to me is
imported as before with a warning that it stays in Triage.

`tcw work inbox accept <key>` is a second way into the same claim, not a second
claim: where `work.tracker.inbox-query` is declared, it runs this import, with the
same checks, binding and messages, for a ticket I am triaging from the inbox.

Running the same import again in the same node gives me the item I already have.
If a run took the ticket but stopped before the item existed, the next run finishes
it without moving the ticket again. `--part` lets one ticket become several items on purpose.
`tcw work tracker link <slug> <key>` records that an item I already have and a
ticket are the same work, and changes nothing else: the ticket keeps its status and
whoever holds it, so I can link one assigned to somebody else, and my item keeps its
status, owner and documents. `tcw work tracker unlink <slug> --reason <text>` removes
a wrong binding and keeps a record of it with my reason. Both work at any status, so
I can tie finished work to the ticket that tracked it and repair a wrong binding on
it; where finished items are kept out of git, as they are by default, that binding
stays on my machine. Neither ever changes the ticket in Jira, and importing a ticket
I have only linked tells me it is not claimed rather than claiming it.

The binding is written by these commands, not by hand, and the web app offers no
edit for it. I can read it wherever I read the item: `tcw work show` names the
ticket, provider, part and link, the board row ends with the ticket, `show --json`
carries it as `tracker`, and the web app's item detail links to the ticket. It records what is bound to what and when, never who took the ticket.
It is never treated as proof of a claim: importing re-reads the ticket and refuses
when Jira disagrees.

Four limits are accepted rather than prevented. On a workflow that offers the claim
from every status, two people can both claim one ticket (under `work.tracker.strict:
true`, `import` refuses to create an item for such a claim). Two runs by the same Jira
account at the same moment can both create an item. Each node keeps its own
bindings, so importing one ticket in two nodes gives an item in each. And a ticket
held by a finished item can be bound to a second item, open or finished, without a
refusal.
A binding for a ticket id that points at a different Jira site from the configured
one makes `import` and `link` refuse and name the item, rather than mistaking an
unrelated ticket on the new site for one already bound.
Keeping the ticket in step with the item's lifecycle, including claiming a linked
ticket when I start the item, is `work/synchronize-external-tracker-work`; requiring
tracked work is `work/require-tracker-backed-work`.
