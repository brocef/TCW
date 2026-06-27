# Upcoming

User-facing release notes for the next version. Plain language — no jargon or
internal module names.

## Added

- Added `tcw work audit-work-backlog`, a read-only backlog audit that reports
  stale, duplicate, under-specified, blocked, broken-reference, and misplaced
  work items with evidence and suggested cleanup actions.
- Added `tcw work consolidate-plans`, a dry-run-first migration command that
  finds older planning documents outside TCW work items and can turn them into
  backlog items with lifecycle artifacts.
- `tcw work list` now shows compact lifecycle artifact letters so users can see
  which items have request, spec, plan, outcome, and refined-outcome documents.
- Older work items now have `initial-request.md` backfilled from `content.md`
  when they were missing a formal request artifact.
