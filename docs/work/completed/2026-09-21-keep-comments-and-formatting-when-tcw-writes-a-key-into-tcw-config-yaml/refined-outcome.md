# Refined outcome: keep comments and formatting when TCW writes tcw-config.yaml

## Decision

**Accepted** on 2026-09-21 in an autonomous run. The requester had authorized the
batch to be finished, self-reviewed, verified and released while they were away.

## Evidence

- Full suite as CI runs it (bare `pytest`, no git identity): **4015 passed,
  3 skipped** at 7d279ca7. After the verify fixes, the item's test files plus the
  writers' test files gave 573 passed, 3 skipped. The verifier independently ran
  407 plus 1183 tests.
- The original proposit-app report was reproduced on a copy of its real config:
  `tags add` became a 1-line diff, and the two `extends` commands a 6-line append,
  where the report had 31 insertions and 22 deletions.
- `tcw:verifier`: accept. `adversarial-code-reviewer`: DONE.

## Deferred

- Windows line-ending handling is verified only by reading the code.
- Re-running `tcw work init` rewriting `work.path` predates this item and is filed
  separately.
- No GitHub issue is attached. Reported by the proposit-app agent.

## Closeout

`tcw work complete` merges `work/<slug>` into `main` locally. The push happens with
the v2.5.1 release.
