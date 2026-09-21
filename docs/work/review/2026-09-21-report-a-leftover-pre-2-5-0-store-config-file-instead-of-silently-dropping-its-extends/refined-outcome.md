# Refined outcome: report a leftover pre-2.5.0 store config file

## Decision

**Accepted** on 2026-09-21 in an autonomous run. The requester had authorized the
batch to be finished, self-reviewed, verified and released while they were away.

## Evidence

- Full suite as CI runs it (bare `pytest`, no git identity): **3923 passed** at the
  last code commit. After the documentation fix, the item's test files plus
  `test_documented_cli_surface` gave 632 passed. The verifier independently ran
  418 tests.
- `tcw:verifier`: accept (criterion 10 partly, see Deferred).
  `adversarial-code-reviewer`: DONE after the documentation fix.
- Hands-on check recorded in outcome.md.

## Deferred

- Criterion 10's check-command half: `tcw taxonomy check` and
  `tcw capabilities check` print "no … node here" instead of the open failure,
  because of `find_node`. Filed as
  `2026-09-21-let-a-broken-extends-reach-the-user-instead-of-find-node-answering-no-node-here`.
- `tcw validate` crashes on a missing `taxonomy.path` inside the capabilities
  check. This predates the item and is filed as
  `2026-09-21-report-a-missing-taxonomy-path-as-a-validate-problem-instead-of-crashing-inside-the-capabilities-check`.
- No GitHub issue is attached. Reported by the proposit-app agent.

## Closeout

`tcw work complete` merges `work/<slug>` into `main` locally. The push happens with
the v2.5.1 release.
