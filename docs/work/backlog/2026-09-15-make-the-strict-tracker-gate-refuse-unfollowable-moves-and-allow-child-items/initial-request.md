# Make the strict tracker gate refuse unfollowable moves and allow child items

## What is wanted

Strict tracker mode (`work.tracker.strict: true`) exists so that no local work
happens without a claimed ticket behind it. Four gaps make it either let through
something it should refuse, or refuse something a team needs:

1. **It lets through a move the ticket cannot follow.** The gate checks the
   ticket's assignee and status but not whether the workflow offers a transition to
   the target. A review reproduced `submit` passing the gate, the item moving to
   review, delivery then recording a conflict, and the next `rework` being refused
   because of that record.
2. **A held item whose claim is still owed stays locked.** When several items share
   one ticket, `submit` is refused ("run sync") while `sync` reports `held`, exits 0
   and keeps the record, so the item is stuck until the other part resolves. Rare,
   but a dead end.
3. **It cannot create child items.** `tcw work new` is refused for everything but an
   epic, and `tcw work tracker import` takes neither `--parent` nor `--initiative`, so
   nesting an item under a parent is impossible and grouping under an epic takes a
   workaround.
4. **An epic worktree from before strict mode can still merge.** Strict mode only
   refuses starting an epic with a worktree; one started before `strict: true` was
   set merges its branch on completion because epics are exempt from the gates.

## Constraints

- A refusal still means nothing happened: the gate runs before the store is touched.
- Whatever lets child items through must still leave strict mode's promise intact —
  a child cannot start without a bound, claimed ticket.

## Out of scope

- `tcw work tracker sync` exiting 0 when it skips a named slug (§2 of the same
  review entry) — tracked in
  `2026-09-15-let-tracker-sync-name-its-transitions-bring-a-late-linked-ticket-forward-and-stop-reading-ordinary-moves-as-drift`.
- Durable evidence of a hold — tracked in
  `2026-09-15-record-lasting-evidence-of-a-tracker-hold-on-a-shared-ticket`.

## Notes

- Merged at triage from two inbox entries and a note from a third, because each
  changes what strict mode refuses; all kept verbatim in `intake.md`.
- Checked at triage on `main`: all four gaps are present (`authorize` in
  `tcw/tracker/sync.py` never reads the offered transitions; `_new` refuses any
  non-epic under strict; the import parser has only `ticket`, `--part`, `--title`;
  `_strict_refusal` returns early for epics).
- Reference material: asked; none provided beyond what `intake.md` cites.

## References

- `docs/work/completed/2026-09-12-refuse-local-work-that-no-claimed-tracker-ticket-authorizes/` —
  the item that built strict mode; its Risk 6 recorded the nesting gap.
- `2026-09-15-check-the-tracker-s-workflow-against-the-statuses-mapping-in-tcw-validate` —
  asks the same "does the workflow offer this transition" question ahead of time.
