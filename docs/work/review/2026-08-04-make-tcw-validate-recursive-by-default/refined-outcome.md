# Verified outcome

## Decision

Accepted by the requester on 2026-08-04.

## Evidence

- Bare `tcw validate` recursively validates the active project and all
  registered descendants, including nested and component-only descendants.
- Recursive diagnostics identify the canonical project that produced each
  problem.
- `tcw validate --no-recurse` validates only the active project, while an
  explicit path remains a bounded active-project scan.
- The full test suite passed: 1170 tests.
- `tcw capabilities check`, `tcw taxonomy check`, `tcw validate`, and
  `git diff --check` passed.
- README, release notes, changelog, and the standing validation capability are
  synchronized with the implemented behavior.

## Deferred follow-ups

None.

## Closeout choices

- Integration route: changes are already committed on the primary checkout.
- Capability reconciliation: `cli/validate-a-node` is an existing Supported
  capability and its description now reflects the changed behavior.
- Documentation Sync: complete.
- Version choice: deferred until after the work item completes.
