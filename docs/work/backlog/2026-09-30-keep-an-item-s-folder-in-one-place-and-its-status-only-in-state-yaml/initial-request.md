# Keep an item's folder in one place and its status only in state.yaml

## What is wanted

A work item's folder should stay at one path for its whole life, so a path noted
at any point stays correct. Today an item's status *is* the folder it sits in
(`docs/work/backlog/<slug>/`, `active/<slug>/`, `review/<slug>/`, …) and every
transition moves the folder. Any path taken before a transition goes stale, and
a write through it creates a stray folder. #58 made that mistake loud (`complete`
requires `refined-outcome.md`, `validate` reports strays); this item removes its
cause. The maintainer confirmed the problem is real beyond this repository:
paths breaking after a transition have caused trouble in other projects too.

Decided with the maintainer at triage:

1. **Status is stored in the item's `state.yaml`**, as a field.
2. **The status-folder system is dropped.** Status is no longer read from, or
   expressed by, the folder an item sits in; the `state.yaml` field is the only
   source of it.
3. **The project config records a TCW version**, as groundwork for better
   migrations in general, not only this one. It records the version whose
   layout the project's files follow: a newer `tcw` that sees an older number
   knows a migration is owed. It changes only when a migration runs, not
   whenever some `tcw` happens to write the project.
4. **Existing projects move by an explicit migrate command.** `tcw` detects the
   old layout, refuses or warns, and names the command; the command converts
   the project and commits the result in one step. Not an automatic conversion
   on first run, and not reading both layouts forever.

## Constraints

- New code must still cope with a project on disk in the old layout, at least
  enough to detect it and point at the migration. Old `tcw` reading the new
  layout is not a constraint.
- The abstraction litmus test applies: status as a field is something a
  non-filesystem store can implement directly, so this should make the store
  interface simpler, not tie it tighter to folders.

## Open for spec

- **Resolved items.** Today discarded items stay on disk but out of git through
  `.gitignore` on `docs/work/discarded/*`, and `work.retain` (`completed: false`
  here) deletes a completed item's folder, leaving it in git history. With one
  place for every item, both need a mechanism. The maintainer left this to
  spec: whether resolved items may still move once (nobody holds a path to a
  finished item), or nothing moves at all and untracking and retention work
  another way.
- Where items live once folders no longer mean status (for example
  `docs/work/items/<slug>/`, or directly under `docs/work/`).
- Children made by older versions nested inside their parent's folder: the
  migration has to handle that layout too.

## Notes

- Readers that infer status from the folder: `_status_of` in `tcw/store/fs.py`
  (status = first folder under the work root), plus status-folder names in
  `tcw/store/base.py` (`WORK_STATUSES`), `tcw/work/cli.py`,
  `tcw/work/recursion.py`, `tcw/validate.py`, `tcw/tracker/{sync,create,intake}.py`,
  and possibly the built web app bundle under `tcw/serve/dist/`. Found by a
  quick search at triage, not a complete list.
- `docs/work/blocked/` also exists in this repository although `blocked` is not
  one of `WORK_STATUSES`; spec should find out what it is.
- The item is much larger than a typical one and may be split at spec, for
  example the config version field and migrate command first, the layout change
  on top of them.
- Reference material beyond the originating issue: not yet asked for; to be confirmed with the maintainer.

## References

- GitHub issue #58 (`brocef/TCW`, still open pending publication) and its
  follow-up comment: where the stale-path problem was reported and where
  removing the cause was first suggested.
- `intake.md`: the inbox entry as filed.
