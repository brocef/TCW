# Outcome — Backfill initial-request from content bodies

Work completed successfully.

## What changed

- Created `initial-request.md` for 25 existing work items that had nonempty
  `content.md` and no formal request artifact.
- Preserved all existing `initial-request.md` files.
- Left `content.md` in place as the work item body/overview surface.
- Updated README, `tcw-work` lifecycle guidance, release notes, changelog, and
  the work capability ledger to clarify the body/request distinction.

## Verification

- Backfill coverage check: `missing initial-request for nonempty content: 0`.
- `tcw work list --status backlog` — older backlog items now show `R`.
- `tcw work list --status completed` — older completed items now show `R`.
- `tcw capabilities check` — capabilities OK.

## Deviations from plan

- No code changes were required; this was a work-artifact migration and
  documentation update.
