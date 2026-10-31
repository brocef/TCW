---
verdict: accepted
judges: 2
---

# Review round 2 — TCW-116

Reviewed by a separate read-only agent (the `tcw:reviewer` agent) on
2026-10-24 in a frozen worktree at `a1a2245e`, against review round 1's
three findings, over `741d7e4b..a1a2245e`. Round 1's results carry forward.

## Checks run

- The full suite as CI runs it, run by the dispatching session at `6a18c5a8`
  in two halves by folder, every `TCW_*` variable unset: `2246 passed,
  2 skipped` and `5482 passed, 111 skipped`, recorded in
  `implement/round-2.md`. `pnpm test` `247 passed`; `tsc --noEmit`,
  `pnpm lint`, `pnpm check:build` clean.
- By the reviewer: `tests/migrate` `321 passed`.
- By hand, through a guarded wrapper, on a copy of round 1's reproduction:
  the dry run prints one A14 line and changes no file; the run prints one;
  a second run has nothing to migrate; 4.0 `tcw validate` finds nothing.

## Round 1's items

- (a) Met. Nothing parses the report codes, and A14 predicts no finding, so
  a code beyond the spec's A1 to A13 is acceptable. Not keeping the 3.x path
  in `.tcw/tcw-migration.yaml` is sound: the record holds only values with no
  4.0 home, and this one has the personal manifest.
- (b) Met. Offering a ticket the run never touched does no harm: the way
  back edits a ticket only while it holds exactly the 4.0 value this
  migration planned, so any other value is skipped or left as pending.
- (c) Met.

Two observations sent from TCW-117's guide writers, checked: the
`write .tcw/.gitignore` line printed twice is what Design 2.4's phase A
requires (the ignore line is written before the progress record, the whole
file later), not a defect; and a work store still in the 2.x layout passing
with exit 0 is out of this item's scope (Non-goals and decision 13), where
A12 reports it.

Departures from the spec to record, decided by the dispatching session as
spec defects, accepted here: criterion 7 lists A1 to A13 and the code adds
A14; Design 2.11 promised that a second person's per-machine paths (M4) are
recovered, where only M5 can be.

No finding belongs to this change.

## Needs a separate change

Kept on the 4.0 run's list of small follow-ups, decided by the dispatching
session: no test covers A14's other source name (`tcw/migrate/config.py:
664-665`); the two `.tcw/.gitignore` lines could be shown as one; A12 for a
2.x work store could name the 2.8-to-3.0 migration guide, as 3.x did. For
TCW-118: the way-back snippet in implement round 1 reads `error.pending`,
which an error raised before the loop does not carry.
