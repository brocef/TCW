# Refined outcome: point a refused drop to the discard route

## Decision

**Accepted** on 2026-09-21 in an autonomous run. The requester had authorized the
batch to be finished, self-reviewed, verified and released while they were away.

## Evidence

- `tests/test_work.py` 215 passed. The new tests failed before the fix, and a
  mutation check confirms the resolved-status branch is covered.
- adversarial-code-reviewer: DONE, and all of its findings are folded in.
- Hands-on check in a scratch node, recorded in outcome.md.

## Deferred

- No GitHub issue is attached. Reported by the proposit-app agent.

## Closeout

`tcw work complete` merges `work/<slug>` into `main` locally. The push happens with
the v2.5.1 release.
