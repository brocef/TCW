## Changed

- The next-step hints after a transition come from one table,
  `TRANSITION_NEXT_STEPS` in `tcw/store/base.py`, beside `STAGE_NEXT_STEPS`, and
  are guarded by the same kind of tests: every command named must exist, no
  placeholder may survive substitution, and every stage named must be legal in
  the status the item lands in (`TRANSITION_LANDS_IN`).
- `tcw work new` (epics included) and `tcw work inbox accept` of a raw entry
  point at `tcw work stage gate request <ref>`. Epics printed no hint before.
- `tcw work start` points at the first stage the item still needs, chosen by
  `start_next_stage` from its artifacts: `spec`, `plan`, `implement`, or — for an
  unheld active item that already has `outcome.md` and no `rework.md` —
  `verify`. The artifacts are read once, shared with the unplanned-item warning
  (`_present_artifacts`).
- `tcw work submit` and `tcw work rework` print the item's location from
  `locate`, falling back to the status name, and point at the `verify` and
  `implement` stage gates.
- `tcw work complete --resolution done --confirm` prints the Definition of Done
  only after the item has closed, as `[x]` lines headed
  `Definition of Done — acknowledged with --confirm:`. A refusal on the way
  prints no checklist. Without `--confirm` the output is unchanged.

## Fixed

- `tcw work start` told the reader to run `tcw work complete`, skipping
  implement, submit and verify (GitHub #68).
- `tcw work submit` told the reader to delete a `refined-outcome.md` that the
  verify stage had not written yet (GitHub #68).
- `tcw work complete --confirm` printed the checklist unticked, including above
  unrelated refusals such as `--already-integrated` on an item with no worktree
  (GitHub #67).
- `tcw work submit` and `tcw work rework` reported a status rather than the
  item's new location (GitHub #58, point 1).

## Removed

- `_complete_hint` in `tcw/work/cli.py`.
