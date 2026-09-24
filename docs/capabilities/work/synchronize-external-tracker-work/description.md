As a developer whose work items are bound to Jira tickets, I can move an item
through its lifecycle and have its ticket follow, without the tracker ever undoing
or blocking what I did locally — unless I turn on `work.tracker.strict`, where the
ticket authorizes local changes before they happen (`work/require-tracker-backed-work`).

`tcw work start` claims a bound item's ticket — an assignment, read back, applying
no transition unless `work.tracker.exclusive-claim-transition` names one — and then
moves it to the status mapped for `active`. `submit`, `rework`, `complete` and
discarding move the ticket to the
tracker status I map each local status to under `work.tracker.statuses` — `active`,
`review`, `completed`, and `discarded`, which may name a status per discard
resolution. A status I leave unmapped sends nothing.

A claim gates work, not resolution. `submit` and `rework` of an item with a ticket
are refused before the item moves unless the ticket is assigned to me — the refusal
names whoever holds it, or `tcw work tracker claim` when nobody does — in every
mode; when Jira cannot be reached they go ahead and report that the ticket did not
follow. Completing and discarding need no claim and move the ticket whoever holds it,
and so does a `tcw work tracker sync` of a completed or discarded item whose ticket
somebody reopened: it is closed again without anyone having to take it.
Otherwise a ticket is only ever moved when it is assigned to me, and when TCW can
tell which transition to use. Where two transitions lead to the
status I mapped, I name the one each move should use under `work.tracker.transitions`
(`submit`, `rework`, `complete`, `discard`, the last taking one name or one per
resolution); with nothing named, the old rule stands and exactly one transition must
lead there. If someone else holds the ticket, if it has been moved on past where its
item is, or if the named transition is not offered or leads elsewhere, TCW leaves it
alone and tells me why. It never follows Jira, and a lifecycle move never pulls a
ticket back: a `start` whose ticket is already past `active` leaves it there and
says so.

Linking a ticket to work already under way changes nothing in Jira.
`tcw work tracker link` warns me when the ticket does not match the item, and while it
stays out of step later moves of that item say the ticket was linked without its
status synced instead of blaming a hand move nobody made. To bring it along I run
`tcw work tracker claim` and then `tcw work tracker sync`, which moves it in one
transition. `link --sync-status` is retired and refuses, naming those commands. A
binding an older `--sync-status` wrote (`catch-up: true`) still has its ticket brought
up through the statuses I mapped, one at a time: forward only, never on a ticket
already resolved, and stopping at the first step it cannot make, for `sync` to carry
on from. A ticket TCW did claim and someone then moved backwards stays drift, and is
not walked forward again.

A ticket waiting in a status before the backlog — Jira's `Triage` is the usual
one — is left there unless I name that status, and the transition out of it, under
`work.tracker.pre-backlog` (for example `Triage: Accept`). With it named, whatever
takes the ticket for work — `start`, or a `sync` that still owes a claim — first
takes it through that transition to `statuses.backlog`, reads it
back, and claims it from there; I am told the ticket left triage even when the
claim afterwards fails. Nothing else takes a ticket out of triage: not `submit`,
`rework`, completing or discarding, and not `tcw work tracker claim`. Without the setting
the refusal names it.

A hand move that takes the ticket part of the way TCW was trying to take it is
accepted rather than reported as drift: anywhere on the path between where the ticket
was left and where the move was going counts as in step.

When the ticket did not follow — Jira was down, my credentials are missing, or the
ticket was in the wrong place — the item still moves and is committed, the command
exits 1 saying so, and the binding records whether that is pending or conflicting.
That is for a lifecycle move only: a `tcw work tracker sync` of an item with nothing
recorded reports what it found and writes nothing at all, whatever Jira answers.
`tcw work show` and `tcw work list` show that state, and `tcw work tracker sync
<slug>` or `--all` retries it, including a claim that did not succeed at start, while
the record still names that `start` as what it owes: it claims, delivers the start,
then the move that came after it. A claim Jira did not answer is pending; one it
refused is conflicting. Two things clear that note — a second failure recording its
own move over it, and another part's item holding the ticket, which drops this item's
record because a held item owes the tracker nothing — and after either, no command
claims the ticket for me any more: `tcw work tracker claim <slug>` takes it and `sync`
then delivers the move.
`sync` acts only on items I started, since it acts as whoever runs it; naming one
somebody else started fails and tells me how to run it as them or take the item over,
while a `--all` sweep walks past their work and still succeeds. A ticket that followed
first time leaves no record and no file change. A ticket already
where it should be is not written to.

Limits I accept: a ticket bound to several parts in this node moves only with the
last open part, parts in other nodes or clones are not seen, and `sync` therefore
leaves a `--part` binding's ticket alone rather than guess; a `--all` sweep visits
only the items that have a record or an owed comment, so reconciling a ticket nothing
is recorded for is something I ask for by naming the item; a binding whose ticket link
is on a different Jira site from the configured one is never written through; and
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
