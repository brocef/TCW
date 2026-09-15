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
