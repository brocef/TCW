# Refined outcome: Let tcw work edit change an item's type to or from epic

## Decision

Accepted, unattended (`autonomous-work`); reasoning in `outcome.md`, "Autonomous
decisions".

## Evidence

- `tcw-verifier`: criteria 1-8 met, from targeted tests (75 passed) and its own
  scratch-project runs of promotion, refusals (open child, resolved child,
  descendant-project child, partial graph), the no-partial-write case and the grouped
  board.
- Full suite at `640fa466` (after review fixes): 3617 passed (criterion 9).
- `tcw capabilities check`: OK; both `capabilities.yaml` paths resolve.

## Closeout choices

- **Route:** committed directly on `main`; nothing to merge. Not pushed.
- **Documentation:** README, `docs/guide/work.md`, `docs/guide/jira.md`,
  `skills/work/references/commands.md`, release notes and changelog.
- **Capabilities:** `work/coordinate-a-cross-node-epic` and
  `work/require-tracker-backed-work` updated; both stay `Supported`.
- **Version:** none cut; accumulates in `upcoming.md`.
- **GitHub issue:** none.

## Deferred follow-ups

- `docs/work/inbox/2026-09-17-a-missing-parent-project-blocks-epic-gates-that-only-look-down.md`
- `docs/work/inbox/2026-09-17-tcw-work-edit-writes-blockers-before-refusing-a-bad-tag.md`
