As a developer whose work items are bound to Jira tickets, I can move an item
through its lifecycle and have its ticket follow, without the tracker ever undoing
or blocking what I did locally — unless I turn on `work.tracker.strict`, where the
ticket authorizes local changes before they happen (`work/require-tracker-backed-work`).

`tcw work start` claims a bound item's ticket, by the same rules `tcw work tracker
import` uses. `submit`, `rework`, `complete` and discarding move the ticket to the
tracker status I map each local status to under `work.tracker.statuses` — `active`,
`review`, `completed`, and `discarded`, which may name a status per discard
resolution. A status I leave unmapped sends nothing.

A ticket is only ever moved when it is assigned to me — or unassigned and being
discarded, since abandoning work is the one thing a ticket nobody holds authorizes —
and when TCW can tell which transition to use. Where two transitions lead to the
status I mapped, I name the one each move should use under `work.tracker.transitions`
(`submit`, `rework`, `complete`, `discard`, the last taking one name or one per
resolution); with nothing named, the old rule stands and exactly one transition must
lead there. If someone else holds the ticket, if it has been moved on past where its
item is, or if the named transition is not offered or leads elsewhere, TCW leaves it
alone and tells me why. It never follows Jira and never pulls a ticket back.

Linking a ticket to work already under way changes nothing in Jira unless I ask.
`tcw work tracker link` warns me when the ticket's status does not match the item, and
later moves of that item say the ticket was linked without its status synced instead
of blaming a hand move nobody made. With `--sync-status`, TCW claims the ticket and
brings it to where the item is — in one transition when the workflow offers one,
otherwise up through the statuses I mapped, one at a time. Forward only, never on a
ticket already resolved, only through statuses I named, and it stops at the first
step it cannot make, leaving the ticket where it reached for `sync` to carry on from.
A ticket TCW did claim and someone then moved backwards stays drift, and is not
walked forward again.

A hand move that takes the ticket part of the way TCW was trying to take it is
accepted rather than reported as drift: anywhere on the path between where the ticket
was left and where the move was going counts as in step.

When the ticket did not follow — Jira was down, my credentials are missing, or the
ticket was in the wrong place — the item still moves and is committed, the command
exits 1 saying so, and the binding records whether that is pending or conflicting.
`tcw work show` and `tcw work list` show that state, and `tcw work tracker sync
<slug>` or `--all` retries it, including a claim that did not succeed at start.
`sync` acts only on items I started, since it acts as whoever runs it; naming one
somebody else started fails and tells me how to run it as them or take the item over,
while a `--all` sweep walks past their work and still succeeds. A ticket that followed
first time leaves no record and no file change. A ticket already
where it should be is not written to.

Limits I accept: a ticket bound to several parts in this node moves only with the
last open part, but parts in other nodes or clones are not seen; transitions made
in `tcw serve`, or a command interrupted between its commit and the tracker call,
leave no record, so "current" means no undelivered change is recorded, and `sync
<slug>` checks such an item without moving its ticket; a binding whose ticket
link is on a different Jira site from the configured one is never written through; and
catching a ticket up stops at any status I have not mapped, so a workflow that forces
a ticket through one needs that status mapped or that ticket moved by hand.

With `comments: true` under `work.tracker`, each move also posts a short comment on
the ticket saying what happened to which item — and, with a `link` template, where
to follow it — but only when the ticket is assigned to me; no lifecycle document
is ever copied. A comment that did not post is recorded and sent by `tcw work
tracker sync`, which first looks for it on the ticket so a post that landed
without an answer is not repeated. Limits I accept: a later move's comment
replaces one still owed, and one whose ticket is no longer mine is dropped; two
runs at once, an edited or deleted comment, or more than 100 newer comments can
still produce a repeat; comments are not posted for moves made in `tcw serve`; and
on a Jira Service Management project a comment may be visible to customers, so I
leave comments off there unless item titles may be seen.
