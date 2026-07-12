# Implementation plan

1. Add abstract inbox entry/resource dataclasses and list/show/accept operations
   to `WorkStore`; reduce the formal status graph to backlog, active, completed.
2. Implement filesystem inbox discovery, safe resource inspection, deterministic
   request generation, attachment copying, staged atomic acceptance, and source
   cleanup in `FsWorkStore`.
3. Add `tcw work inbox list|show|accept` parsing and presentation; update existing
   work-command messages for backlog-only start/drop behavior.
4. Update the web viewer status vocabulary and any API assumptions.
5. Add focused store and CLI tests for files, folders, manifests, binary content,
   ambiguity, ignored entries, symlinks, title overrides, cleanup, and status
   retirement; update existing status fixtures.
6. Update `README.md`, `docs/release-notes/upcoming.md`,
   `docs/changelogs/upcoming.md`, `skills/tcw-work/SKILL.md`, its lifecycle inbox
   guidance, and the affected capability descriptions.
7. Run focused tests, the full pytest suite, `tcw capabilities check`, and
   `tcw validate`; record results in `outcome.md` for user verification.

Steps 4 and 6 can proceed after the model contract settles; tests are developed
alongside steps 1-3 and then run together in step 7.
