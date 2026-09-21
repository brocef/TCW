# Refined outcome: children get their own status

## Decision

**Accepted** on 2026-09-21 in an autonomous run. The requester had authorized the
batch to be finished, self-reviewed, verified and released while they were away.

## Evidence

- Full suite as CI runs it (bare `pytest`, no git identity): **3963 passed**
  before the verify fixes; 550 targeted tests passed after them. `tcw:verifier`
  independently ran 990 tests across 12 files plus the web tree test (9 passed).
- `tcw:verifier`: 21 of 22 criteria met, and criterion 10 at the store level (see
  Deferred). `adversarial-code-reviewer`: DONE on re-review.
- `tcw validate` and `tcw capabilities check` OK in the worktree.

## Deferred

- Criterion 10's CLI form (`tcw work start <child> --take-over`) is blocked by an
  existing limitation, tracked by
  `2026-09-15-make-start-take-over-recover-an-interrupted-claim-from-the-cli-and-the-web-app`.
- A refused `tcw work complete` still prints the Definition of Done checklist
  first, so its output reads out of order. It's cosmetic and left as is.
- No GitHub issue is attached.

## Closeout

`tcw work complete` merges `work/<slug>` into `main` locally. The push happens with
the v2.5.1 release.
