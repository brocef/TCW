# Say where a dated amendment to an item's request belongs

From GitHub issue [#74](https://github.com/brocef/TCW/issues/74) (filed
2026-09-29 by @brocef), preserved as this item's `intake.md`.

## The request

When something that changes an item's request arrives *after* the item was
written up — a decision made later, a clarification, a new constraint — there
is no documented place to record it. `intake.md` is raw arrival and is never
edited. An older item has `initial-request.md` and no `intake.md`, and an agent
that needed to record a later decision against one had to guess; it appended a
dated section to `initial-request.md`.

Asked for:

- A documented place for amendments that arrive after an item is written up.
  The requester offers options without choosing: an `amendments.md` or
  `notes.md` convention that `tcw work show` recognises, or a command such as
  `tcw work note <slug>` that appends a dated entry.
- A sentence in the `work` skill saying which file an agent should use.

Seen on tcw 2.6.4.

## Notes

- Written autonomously (an `/autonomous-work` run); there was no requester to
  ask. Reference material: the issue itself; nothing else was offered.
- Found while writing this: the `create-work` procedure
  (`tcw/work/procedures/create-work.md`, "Append only what is new") already
  says to append new information under a dated `## Added <YYYY-MM-DD>` heading
  — to `initial-request.md` if it exists, **otherwise to `intake.md`**. That
  last clause contradicts the body-surface rule in the `work` skill and the
  guide ("Edit `intake.md` only as a named artifact — raw input that quietly
  changes is not raw input"). The answer partly exists, disagrees with itself,
  and is not where an agent recording a later decision would look.

## References

- `tcw/work/procedures/create-work.md` — the existing dated-append rule, and
  the `intake.md` clause that conflicts with it.
- `skills/work/references/commands.md` § "The body surface" and
  `docs/guide/work.md` § "Editing a body, and how it promotes an intake" — the
  rule that `intake.md` is never quietly edited, and that a body write promotes
  an intake-only item to a request.
