Work completed successfully and is ready for user verification.

## What changed

- Added abstract inbox entry/detail/resource types and list, show, and atomic
  accept operations to `WorkStore`.
- Implemented permissive standalone-file and indexed-folder intake in
  `FsWorkStore`, including safe text detection, resource manifests, bounded
  attachments, hidden-file/symlink exclusion, deterministic generated requests,
  and source preservation on pre-acceptance failures.
- Added `tcw work inbox list|show|accept` and retired `inbox` from formal work
  statuses, transitions, status-path resolution, board filters, and drop/start
  behavior.
- Updated README, web presentation, the `tcw-work` skill and lifecycle guidance,
  capability descriptions, release notes, changelog, and an optional intake
  template.

## Verification

- Focused work/store suite: 177 passed.
- Full suite: 548 passed.
- `tcw capabilities check`: OK.
- `tcw validate`: OK.
- `git diff --check`: clean.

## Deviations and follow-ups

No scope deviations or deferred implementation issues. A version decision and
explicit user verification remain before capability reconciliation and work-item
completion.
