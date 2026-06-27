# Plan — Normalize initial requests from content bodies

## Steps

- Start the work item before the migration.
- Copy every `docs/work/**/content.md` to its sibling `initial-request.md`.
- Trim trailing blank lines in generated request files so `git diff --check`
  stays clean.
- Verify all pairs match.
- Record outcome and complete the work item.
