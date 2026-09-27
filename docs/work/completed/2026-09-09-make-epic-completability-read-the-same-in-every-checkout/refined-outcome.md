# Refined outcome — Make epic completability read the same in every checkout

**Accepted** (unattended run, 2026-09-27).

- An epic whose children are all resolved now reads as ready to close in every
  checkout and closes there from `backlog`: each child's record names its epic,
  and the epic counts children known only from that record. `reconcile` lists
  them. A missing parent project no longer blocks closing or demoting an epic.
- Verified: the verifier found criteria 1–9 met, including in a real
  `git clone`; the full suite on the branch merged with main (4727 passed, 3
  skipped); the
  reproduction and the recovery for older records driven by hand through the
  CLI.
- Review: three findings fixed (`tombstone add` dropped the epic; demotion
  advice pointed at a refused edit; recovery docs asked for an unneeded
  `--force`), and the spec and plan brought in line with the code.

## Deferred

- No GitHub issue: the item came from an internal report.
- Children resolved before this release carry no epic in their record; the
  epic guide documents how to close such an epic (start it, then complete it).
- Follow-up filed:
  `2026-09-27-match-an-epic-s-children-by-the-epic-s-node-as-well-as-its-slug`.
