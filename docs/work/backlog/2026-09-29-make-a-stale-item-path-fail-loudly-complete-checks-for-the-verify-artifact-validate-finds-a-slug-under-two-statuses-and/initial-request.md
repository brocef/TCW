# Make a stale item path fail loudly: complete checks for the verify artifact, validate finds a slug under two statuses, and the stage text says where to write

From GitHub issue [#58](https://github.com/brocef/TCW/issues/58) (filed
2026-09-19 by @brocef) — points 2–4 and the follow-up comment — preserved as
this item's `intake.md`. Point 1 (what `submit` and `rework` print) shipped in
2.7.0.

## The request

An agent holds an item's folder path across many turns. `submit` moves the
folder from `active/<slug>/` to `review/<slug>/`; if the agent then writes
`refined-outcome.md` to the path it was holding, the write recreates
`active/<slug>/` with one stray file in it. Nothing fails: the write, `git add`
and `complete` all succeed, and the item completes with its acceptance record
outside it.

Asked for, each independently:

2. **`complete` checks for `refined-outcome.md`.** An item completes as `done`
   with no `refined-outcome.md` anywhere in its folder, although that artifact
   is what distinguishes acceptance from rework. A warning, or a refusal that
   `--force` overrides.
3. **Detect one slug under two status folders.** With `review/<slug>/` holding
   the item and `active/<slug>/` holding a stray file, `validate`, `show` and
   `list` all report one healthy item. `validate` is the natural place.
4. **Say where to write in the stage text.** The `postmortem` prompt already
   says to write "in the item's folder wherever that folder currently lives";
   `verify` (right after the move) and `implement` say nothing. Point at
   `tcw work path <slug>`.

The follow-up comment suggests removing the cause: a folder that never moves,
with the status kept only in `state.yaml`, or a stable link.

## Notes

- Written autonomously (an `/autonomous-work` run); there was no requester to
  ask. Reference material: the issue and its comment.
- Triage recorded the stable-folder suggestion as a large store-layout change
  for the spec to weigh, not as the ask.
- Found since triage: with two folders holding one slug, `tcw validate` does
  not merely miss it — it **crashes** with an uncaught `MultipleMatch` from
  `FsWorkStore.check` → `_parent_problems` → `_find`. Filed as the inbox entry
  `2026-09-29-tcw-validate-crashes-on-a-duplicate-slug.md`; point 3 covers it.
- Also left for this item by an earlier review: for a qualified reference
  (`tcw work start kid/<slug>`, and `submit`, `rework`, `complete`), the folder
  printed after the transition is relative to the child project, not to where
  the command ran, so it names a path that does not exist from there.

## References

- `docs/work/inbox/2026-09-29-tcw-validate-crashes-on-a-duplicate-slug.md` — the
  crash point 3 has to fix.
