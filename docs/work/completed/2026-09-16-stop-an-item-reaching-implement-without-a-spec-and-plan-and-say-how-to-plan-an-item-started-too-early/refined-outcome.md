# Refined outcome — Stop an item reaching implement without a spec and plan

**Accepted** (unattended run, 2026-09-27).

- An item started before it was specified or planned can now be: `spec` and
  `plan` run in `active` as well as `backlog`. `tcw work start` and the
  `implement` gate warn, naming the missing document and the command to write
  it; neither refuses. This repository binds a refusal to `implement`.
- Verified: the verifier found criteria 1–5 met, criterion 4's repository
  refusal exercised in a scratch copy; the full suite on the branch merged with
  main passed (4692 passed, 3 skipped); the report reproduced by hand.
- Review: two findings fixed (an unreadable document failing a completed start;
  a qualified reference advised by bare slug), each with a test that fails on
  the earlier helper.

## Deferred

- No GitHub issue: the item came from an internal report.
- The work skill's front page is unchanged (its line budget); `transitions.md`
  carries the recovery. The store-wide unreadable-artifact problem is the
  existing item
  `2026-09-26-keep-one-unreadable-state-yaml-or-artifact-from-breaking-the-board-or-an-item-s-detail`.
