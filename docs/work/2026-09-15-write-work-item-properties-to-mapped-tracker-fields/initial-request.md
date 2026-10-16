# Write work item properties to mapped tracker fields

## What is wanted

Once a ticket is bound, the item and the ticket describe the same work, but the only
thing TCW keeps in step is status. Someone reading the ticket in Jira cannot see which
work item it belongs to, and every other property a team tracks there has to be copied
by hand and drifts the first time someone edits the item.

Wanted (GitHub #37 and its widening comment):

1. **The item reference on the ticket.** A node names a tracker field that TCW fills
   with the item's stable reference (`<project-id>/<slug>`, as `tcw://` links name
   it) whenever it makes a binding, and clears on unlink only when the field still
   holds this binding's value. The reporter's team already uses a "TCW Item" field
   for JQL, boards and automation, and had to fill it in by hand after every link.
2. **Other properties, kept in step.** A mapping from item properties — priority,
   effort, complexity, tags, title, owning epic — to tracker fields, written on
   `import` and `link` and again whenever `tcw work edit` changes a mapped property,
   with values converted where the field needs it (for example effort to a select
   list). Concrete case: a numeric Jira priority field holding the same integer as the
   item, so boards sort as `tcw work list` does.

## Constraints

- **One direction only**: item to ticket. TCW never reads a field back into the item.
- **Only named fields are written.** With no mapping, nothing changes.
- **Inherits** like the rest of `work.tracker`: set once at the workspace root.
- **Failure keeps the binding.** A refused field write is reported, the command exits
  non-zero, and running it again fills the field without a second binding.
- `tcw validate` keeps checking the setting's shape only.

## Open questions the reporter listed

Field length limits, several items bound to one ticket (`--part`), field name versus
id, priority direction and scale, overwriting a hand edit, and backfilling items bound
before a mapping is added. All are recorded in `intake.md` for the spec.

## Notes

- Accepted with the maintainer's widening comment at triage; kept separate from GitHub
  #43 (`tracker create`), which it pairs with, because each is a large change.
- The tracker bridge's first delivery excluded "mirroring technical lifecycle artifacts
  into tracker fields"; properties and a reference are not lifecycle artifacts.
- Reference material: asked; none provided.
- GitHub #37 stays open until the change ships.

## References

- `2026-09-15-add-tcw-work-tracker-create-to-make-and-bind-a-ticket-for-an-existing-item` —
  the paired item; a created ticket would want these fields filled too.
- `2026-09-15-check-the-tracker-s-workflow-against-the-statuses-mapping-in-tcw-validate` —
  if that check contacts the tracker, whether a mapped field exists could be checked there.
