As a developer on a project where every piece of work must come from a ticket, I set
`work.tracker.strict: true` and TCW refuses local work that no ticket I have claimed
authorizes. Nothing offers a way around it: there is no bypass flag, and `--force`
and `--take-over` still gate only what they gated before.

Under strict mode, `tcw work new`, and `tcw work inbox accept` of a raw inbox entry,
refuse and point me at `tcw work tracker import <ticket>`, which claims a ticket and
creates its item. `tcw work inbox accept` of a ticket key is not refused for being
strict: it is that same import, and refuses exactly where the import would.
`tcw work start` of an item with no ticket refuses; of a bound item, it claims the
ticket first and starts the item only when the claim succeeded. `submit` and `rework`
first read the ticket and refuse unless it is assigned to me and sits where the
item's lifecycle left it. Completing an item as `done` refuses only when the ticket
is not where the lifecycle left it — for a `worktree` item, before anything is
merged — and not for who holds it: a claim gates work, not finishing it. A refusal says what did not happen and what to fix, and
changes no file; a `start` refused after its claim leaves the ticket claimed.
Discarding an item is always allowed, so no item is trapped; `drop` refuses an item
that has ever been bound, since dropping would erase that record, and tells me to
discard it instead. Epics are not gated, since they only group work — which is why
`tcw work edit --type` refuses to turn an item into an epic or an epic into an
item — except that an epic cannot be started in a worktree.

A claim only authorizes work when the workflow could have refused a second person,
and the key that carries that promise is `work.tracker.exclusive-claim-transition`.
The claim `start` and `tcw work tracker claim` make applies that transition before
assigning the ticket, so on a workflow that will not apply it to a ticket somebody
already took, a second person is refused there and their item does not move. Every
strict claim — `start`, `tracker claim`, `import` and `inbox accept` — then checks
that the ticket does not offer the transition again from the status it led to, and
refuses when it does, leaving the ticket claimed for me to release; `import` and
`inbox accept` check `transitions.start` the same way, since they take the ticket
through it. On a ticket I
already hold no transition is applied, since the claim must be safe to repeat; what
is checked there is that the workflow would still refuse a second person. A released
item whose ticket sits unassigned where the transition cannot be applied is refused,
and the refusal tells me to assign the ticket to myself in the tracker or move it
back to a status that offers the transition.

The web app cannot check a ticket, so under strict mode its create, start, complete
as `done` and drop actions answer with a refusal naming the `tcw work` command to use;
an edit to `tracker.yaml` is refused in every mode (see
[Edit TCW content in a local web app](tcw://C/web/editing)). Editing an item's fields and documents stays allowed
everywhere.

Strict mode needs the tracker. When Jira cannot be reached, gated changes are refused
until it answers. `tcw validate` reports a strict block missing `statuses.active`,
`statuses.completed`, a `statuses.discarded` that covers every discard resolution,
`work.tracker.exclusive-claim-transition`, or `work.tracker.transitions.start` —
required because strict mode creates work only from a ticket, and `tcw work tracker
import` and `tcw work inbox accept` claim through it —
and while the tracker configuration has problems the gates refuse rather than
switching themselves off. Turning strict mode off is `strict: false`, or removing
the key; a child node that inherits a strict parent's tracker block can set
`strict: false` in its own.

Limits I accept: one claimed ticket can authorize several items, through `tracker
link` and `import --part`; `new --parent` and `new --initiative` are refused, so a
child is imported and linked rather than nested; and a workflow that offers
`exclusive-claim-transition` again from where it leads excludes nobody, and TCW can
tell only from a ticket in that status — so a strict `start` of a ticket I already
hold in the backlog status is accepted without that check. A ticket held back for another
part whose item is not in this checkout is refused as out of place until I move it.
