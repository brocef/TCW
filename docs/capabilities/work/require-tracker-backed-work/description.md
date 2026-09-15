As a developer on a project where every piece of work must come from a ticket, I set
`work.tracker.strict: true` and TCW refuses local work that no ticket I have claimed
authorizes. Nothing offers a way around it: there is no bypass flag, and `--force`
and `--take-over` still gate only what they gated before.

Under strict mode, `tcw work new` and `tcw work inbox accept` refuse and point me at
`tcw work tracker import <ticket>`, which claims a ticket and creates its item.
`tcw work start` of an item with no ticket refuses; of a bound item, it claims the
ticket first and starts the item only when the claim succeeded. `submit`, `rework`
and completing an item as `done` first read the ticket and refuse unless it is
assigned to me and sits where the item's lifecycle left it — for a `worktree` item,
before anything is merged. A refusal says what did not happen and what to fix, and
changes no file; a `start` refused after its claim leaves the ticket claimed.
Discarding an item is always allowed, so no item is trapped; `drop` refuses an item
that has ever been bound, since dropping would erase that record, and tells me to
discard it instead. Epics are not gated, since they only group work, except that an
epic cannot be started in a worktree.

A claim only authorizes work when the workflow could have refused a second person:
if, once claimed, the ticket still offers the claim transition, `start` and
`tcw work tracker import` refuse and leave the ticket claimed for me to release. A
claim retried later — by the next lifecycle command or `tcw work tracker sync` — is
checked the same way, and stays owed while the check fails.

The web app cannot check a ticket, so under strict mode its create, start, complete
as `done` and drop actions, and edits to `tracker.yaml`, answer with a refusal naming
the `tcw work` command to use. Editing an item's fields and documents stays allowed
everywhere.

Strict mode needs the tracker. When Jira cannot be reached, gated changes are refused
until it answers. `tcw validate` reports a strict block missing `statuses.active`,
`statuses.completed`, or a `statuses.discarded` that covers every discard resolution,
and while the tracker configuration has problems the gates refuse rather than
switching themselves off. Turning strict mode off is `strict: false`, or removing
the key; a child node that inherits a strict parent's tracker block can set
`strict: false` in its own.

Limits I accept: one claimed ticket can authorize several items, through `tracker
link` and `import --part`; `new --parent` and `new --initiative` are refused, so a
child is imported and linked rather than nested; and whether a workflow can refuse a
second claimant is learned from the ticket after the claim, as the account I use sees
it, not from the project's workflow definition — a workflow that hides the claim from
my account but offers it to another is not caught. A ticket held back for another
part whose item is not in this checkout is refused as out of place until I move it.
