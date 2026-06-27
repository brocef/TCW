# Plan — Backfill initial-request from content bodies

## Steps

- Start the work item before the migration.
- Run a bounded script over `docs/work/**/state.yaml` item folders.
- For each item with `content.md` and no `initial-request.md`, copy nonempty
  `content.md` into `initial-request.md`.
- Update lifecycle guidance in README and `skills/tcw-work`.
- Update the work capability ledger for the body/request distinction.
- Verify with `tcw work list`, `tcw capabilities check`, and tests if code is
  changed.

## Documentation sync tasks

- Update `README.md` for public lifecycle guidance.
- Update `docs/release-notes/upcoming.md` and `docs/changelogs/upcoming.md`
  because repository work artifacts and docs change.
- Update `skills/tcw-work/SKILL.md` because lifecycle guidance changes.
