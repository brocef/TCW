As a developer whose work items are bound to Jira tickets, I can move an item
through its lifecycle and have its ticket follow, without the tracker ever undoing
or blocking what I did locally — unless I turn on `work.tracker.strict`, where the
ticket authorizes local changes before they happen (`work/require-tracker-backed-work`).

`tcw work start` claims a bound item's ticket, by the same rules `tcw work tracker
import` uses. `submit`, `rework`, `complete` and discarding move the ticket to the
tracker status I map each local status to under `work.tracker.statuses` — `active`,
`review`, `completed`, and `discarded`, which may name a status per discard
resolution. A status I leave unmapped sends nothing.

A ticket is only ever moved when it is assigned to me and still sits where the
item's previous status put it. If someone else holds it, it is unassigned, it was
moved on in Jira, or its workflow does not offer exactly one transition to the
status I mapped, TCW leaves it alone and tells me why. It never follows Jira and
never pulls a ticket back.

When the ticket did not follow — Jira was down, my credentials are missing, or the
ticket was in the wrong place — the item still moves and is committed, the command
exits 1 saying so, and the binding records whether that is pending or conflicting.
`tcw work show` and `tcw work list` show that state, and `tcw work tracker sync
<slug>` or `--all` retries it, including a claim that did not succeed at start.
`sync` acts only on items I started, since it acts as whoever runs it, and a ticket
that followed first time leaves no record and no file change. A ticket already
where it should be is not written to.

Limits I accept: a ticket bound to several parts in this node moves only with the
last open part, but parts in other nodes or clones are not seen; transitions made
in `tcw serve`, or a command interrupted between its commit and the tracker call,
leave no record, so "current" means no undelivered change is recorded, and `sync
<slug>` checks such an item without moving its ticket; and a binding whose ticket
link is on a different Jira site from the configured one is never written through.

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
