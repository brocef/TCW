# Refined outcome: Say so when tracker import --parent meets a ticket already bound here

## Decision

Accepted by the user on 2026-09-27, after the verify assessment.

## Evidence

- Verifier (tcw:verifier): all six acceptance criteria met by passing tests;
  three of the new tests run against main's code fail, so they test the new
  behavior; documentation sync done; `outcome.md` matches the commits. Its one
  gap, the untested branch for a bound item that disappears before it is read,
  was covered at verify (`9cf8da79`) and mutation-checked.
- Full suite in the worktree at `9816bba1`: 4733 passed, 3 skipped.
- Combined check: after merging main (`111b6e70`), which now also holds the
  tags fix `2026-09-26-read-item-tags-normalized-and-keep-non-tag-work-tags-entries-visible`,
  the full suite on the merged tree: 4750 passed, 3 skipped. The two items share only the
  changelog and release notes, which merged without conflict.
- No live Jira check: the tests drive the suite's simulated tracker; no real
  Jira project was used.

## Capability ledger

`work/manage-external-tracker-intake` and `work/require-tracker-backed-work`
changed as the spec said: `--parent` and `--initiative` place only the item an
import creates, and a re-import naming a placement the bound item lacks changes
nothing and fails. Status of both stays Supported.

## Deferred

- The other two strict-mode gaps stay in
  `2026-09-27-close-two-strict-mode-gaps-left-by-the-unfollowable-move-gate`.
- From the spec review, not taken here: a re-run with `--parent P` after `P` was
  discarded is refused by the existing pre-check before the binding lookup. It
  predates this change and needs `P` resolved while its child stays open;
  `complete` refuses that, and whether discarding can reach it was not checked.
  Not filed.

## Closeout

Complete, then merge the branch into main locally. No push and no version cut:
the entries wait in `upcoming.md` for the next bugfix release. No GitHub issue
is attached to this item.
