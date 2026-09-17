# Let tcw work edit change an item's type to or from epic

## What is wanted

An item filed as an ordinary backlog item that later turns out to be an initiative
should be promotable to an epic through the CLI, and an epic that should not have been
one should be demotable.

Today `tcw work new --epic` is the only way to set `type: epic`. `tcw work edit` has no
option for it and `update_work` takes no `type`. While planning the tracker bridge, whose
request had been written as a whole initiative, the session had three bad choices:
recreate the item under a new slug and lose its history; leave it a plain item and lose
what only an epic gets (`ready-to-close` on the board, completing straight from backlog,
`reconcile --complete-when-ready`); or set the field by hand — which it did, and which
the skill tells agents never to do.

## Constraints

- **Demoting an epic must not orphan its children** — items that point at it with
  `initiative:`.
- Storage-neutral: `type` is already a field every store carries, so setting it is an
  ordinary field write.

## Notes

- Most epic behaviour does not depend on the type (`reconcile` scans for
  `initiative == <slug>`; the "child cannot start before its epic is active" gate reads
  the parent's status). Only `epic_completable` and the board's `ready-to-close` segment
  require it.
- The entry's suggested shape (`--type epic` / `--type ""`, a `type` keyword on
  `update_work`, refusing demotion while children exist) is kept in `intake.md` for the
  spec.
- Checked at triage on `main`: still no `--type`/`--epic` on `edit`, no `type` on
  `update_work`.
- Reference material: asked; none provided.
