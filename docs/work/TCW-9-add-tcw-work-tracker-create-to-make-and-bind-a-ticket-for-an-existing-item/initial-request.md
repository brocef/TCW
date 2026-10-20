# Add tcw work tracker create to make and bind a ticket for an existing item

## What is wanted

The tracker integration only goes from ticket to item: `import` creates an item from
a ticket, and `link` binds two things that already exist. Nothing creates a ticket
for an item that already exists — which is the first thing a team with an existing
TCW backlog needs.

In the reporter's first real use, 116 of 125 open items across six nodes had no
ticket, and getting them into Jira meant a custom script against the Jira REST API
that chose an issue type, set the parent from the item's parent or epic, set
components from the node, moved the ticket to the status matching the item, ran
`tracker link`, and kept a record so a re-run would not create duplicates. All of that
is information TCW already has, so every adopting team will write a version of that
script.

Wanted (GitHub #43): a command that creates a ticket for one existing item, or for
many, and binds it — configured under `work.tracker` and inherited like the rest of
that block — such that:

- summary and description come from the item's title and its request or intake,
  converted to the tracker's own format;
- the parent comes from the item's parent or epic when that item is bound, with
  epics created before their children;
- the ticket ends at the status matching the item, by the same rules as sync;
- it is safe to re-run: an already-bound item is never given a second ticket, and an
  interrupted run resumes by linking rather than creating a duplicate;
- a dry run shows what would be created before anything is written.

## Constraints

- Tickets created this way are consistent — same types, parent links and starting
  status for items decided the same way.

## Out of scope

- Writing the item reference or other properties into ticket fields — GitHub #37,
  tracked in `2026-09-15-write-work-item-properties-to-mapped-tracker-fields`, which
  this pairs with.

## Notes

- The reporter's proposed command shape and config block are kept verbatim in
  `intake.md`; they are a starting point for the spec, not a decision.
- The tracker bridge's first delivery listed "backfilling every historical work item"
  as a non-goal *for the first delivery*; that delivery has shipped, so this is the
  follow-up, not a reversal.
- Kept separate from #37 at triage because each is a large change.
- Reference material: asked; none provided.
- GitHub #43 stays open until the change ships.

## References

- `docs/work/completed/2026-08-04-supplement-filesystem-tcw-work-with-an-external-tracker-bridge/initial-request.md` —
  the non-goals for the first delivery.

## Added 2026-09-20 — creating an item should create its ticket

From a working session on 2026-09-20. An audit of this repository's own board
found 53 open work items and **zero** tracker bindings, against a TCW Jira
project holding one ticket. Getting them bound meant writing exactly the script
this item exists to delete — issues created through Jira's REST API, moved out
of the workflow's initial status, then bound one at a time with
`tcw work tracker link`.

Brian's request, having seen that: **filing a work item should create its ticket,
not leave one owed.** The command this item already describes is the mechanism;
what is added here is that ordinary item creation uses it, so a backlog can never
drift out of the tracker again in the way this one did.

This is folded in rather than tracked separately because the two are one design:
a command nobody remembers to run reproduces the same gap, and deciding the
command's shape without deciding whether creation calls it would settle the
interface twice.

### What is wanted, in addition to the command

- An item filed with `tcw work new` gets a ticket and a binding as part of being
  filed, under a `work.tracker` setting, inherited like the rest of that block.
- The setting is **off by default**. A project that has not asked for this must
  keep filing items exactly as it does today.

### Questions this raises that the command alone does not

1. **Filing must survive a tracker that does not answer.** `tcw work new` works
   with no network and no credentials today, and that is worth keeping — an idea
   filed on a plane is the point of the inbox. So a failed creation cannot lose
   the item. TCW already has the shape for this: the `sync` record that retries
   what a lifecycle command could not send. The likely answer is that the item is
   created, the ticket is owed, and `tcw work tracker sync` settles it — but that
   is the spec's to decide, not this request's.

2. **Which verbs count as creating an item.** `tcw work new` is the obvious one.
   `tcw work inbox accept` also creates items, `--parent` creates children, and
   epics are exempt from strict mode entirely today
   (`tcw/work/cli.py`, `_new`). The spec has to name the full set rather than
   assume `new`.

3. **How this sits beside `work.tracker.strict`.** Strict mode is the *opposite*
   arrangement and already exists: it makes `tcw work new` refuse outright and
   sends the user to `tcw work tracker import <ticket>`, so the ticket must be
   created by hand first. Three positions now exist — non-strict (file freely,
   no ticket, which is how this backlog drifted), strict (refuse, ticket first),
   and this (file freely, ticket follows). Whether the new setting is independent
   of `strict`, or whether strict becomes one value of a single mode, is a
   decision the spec must make and state. It affects whether strict mode's
   refusal path survives at all.

4. **The initial-status trap, restated as a requirement.** The intake already
   notes moving a ticket out of the workflow's initial status. The 2026-09-20
   audit showed why it is not cosmetic: new issues in this project land in
   `Triage`, which is exactly what `work.tracker.inbox-query` selects. A ticket
   created and left there returns through `tcw work inbox` as untriaged inbound
   work, offering to create a *second* item for the one that just created it.
   Automatic creation makes this worse than the manual command does, because it
   would happen on every filing without anyone watching.

### Evidence from the 2026-09-20 backfill

The workaround script is in this session's history rather than committed, but
what it had to do is worth recording, because each step is a requirement:

- create the issue (it lands in `Triage`);
- read the available transitions and move it to `To Do`, since the target status
  is not reachable in one hop from every initial status;
- bind with `tcw work tracker link <slug> <key>` — **without** `--sync-status`
  for backlog items, because that flag claims and assigns the ticket, which is
  wrong for work nobody has started;
- log the created key *before* linking, so an interrupted run can resume by
  linking rather than creating a duplicate;
- skip any item that already has a `tracker.yaml`, so a re-run is safe.

Only the one active item was linked with `--sync-status`, which correctly claimed
it, moved it to `In Progress` and assigned it. That asymmetry — backlog tickets
stay unassigned, the active one is claimed — is behaviour the command should
reproduce rather than leave to a flag the caller has to remember.
