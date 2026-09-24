# Refined outcome: leave an accepted or imported ticket in the backlog status, matching its item

## Decision

**Accepted** by the user on 2026-09-24. They approved completing the item before
the final full-suite run finished ("we can always undo them if it does not
pass"). The release tag is pushed only once that run is green.

## Evidence

- An independent read-only check against the spec (the `tcw:verifier` agent) found
  AC1–AC8 met, each covered by a test that fails when the behaviour breaks. It
  raised four problems, all accepted and fixed before this decision (commits
  `84288f0c` and `2153d25d`; details in `outcome.md`):
  - the `transitioned` guard the spec asked for had been dropped;
  - after a tracker error, the warning could name the wrong status;
  - the README understated the claim;
  - no test started an imported item.
- `pytest -q tests/test_tracker_import_returns.py`: 10 passed after the fixes.
  The tracker and inbox files passed 1118 before the fixes.
- `tcw validate`: OK. `tcw capabilities check`: OK.
- AC9, a full bare-`pytest` run on the final code, was still running when this was
  written. The one earlier full run failed only the test that was then corrected.
  If this run is not green, the release is not tagged, and this completion is
  reopened.

## Capability ledger

`work/manage-external-tracker-intake` is **changed**, as declared in
`capabilities.yaml`. Its description gains the put-back sentence and a fifth
accepted limit (the race in spec R1). No status flip is needed: it was
`Supported` and stays so.

## Closeout choices

- **Merge route:** committed straight to `main`. No worktree or PR.
- **Documentation:** Jira guide, README, `skills/work/references/commands.md`,
  the capability description, and changelog and release notes `upcoming.md`.
- **Release:** a patch, v2.6.1, cut with `scripts/cut_version.py patch` and
  published by pushing the tag, once the full suite is green.
- **No originating GitHub issue.** The item came from TCW-1's acceptance during
  the 2026-09-24 backlog cleanup.

## Follow-ups

- `2026-09-24-make-the-test-suite-run-in-minutes-not-half-an-hour` (filed at the
  user's request).
- The real-Jira check from `outcome.md`: the next real `inbox accept` of a Triage
  ticket after v2.6.1 should leave the ticket in To Do.
