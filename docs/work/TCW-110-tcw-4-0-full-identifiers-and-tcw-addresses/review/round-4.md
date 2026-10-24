---
verdict: accepted
judges: 4
---

# Review round 4 — TCW-110

Reviewed by a separate read-only agent on 2026-10-23 at `ef061f8a` on the
branch `tcw110-fix`, over `3e6868fc..HEAD`, against the qa rejection that
implement round 4 answers. The branch was then brought into `v4` on top of
TCW-108's implement round (`f6243835..e5c7ebee`); the only conflict was the
built web client, which was rebuilt from the combined source.

## Checks run

- By the reviewer, at `ef061f8a`: the end-to-end suite in full with no flags,
  twice, `15 passed` each time with the screenshots compared; `pnpm test`
  `189 passed`; `tsc --noEmit`, `pnpm lint` and `pnpm check:build` clean; the
  three touched Python test files `56 passed`. The two new client tests were
  run against `3e6868fc`'s `app.tsx` and `work-views.tsx` and failed
  (`2 failed | 22 passed`), so they test the fix.
- By the dispatching session, on the combined `v4` at `e5c7ebee`: the full
  suite as CI runs it, `.venv/bin/pytest -q -p no:cacheprovider`, in two
  halves by folder, `1912 passed, 2 skipped` (`tests/work`, `tests/serve`)
  and `3987 passed, 111 skipped` (the rest), `5899 passed, 113 skipped` in
  all; `pnpm test` `190 passed`; `tsc --noEmit`, `pnpm lint` and
  `pnpm check:build` clean; the end-to-end suite `15 passed`.
- `documentation-sync`: the reviewer found that the changelog entry had no
  section for this round's fixes. The `## Fixed` section of
  `docs/changelogs/upcoming/TCW-110-…md` and the `## Web app fixes` paragraph
  of the release notes entry were added in `e5c7ebee` and checked against
  the reviewer's list (init in any letter case, `navigateTo`'s `saved`,
  `fileStage` and `openStage`, the end-to-end repairs).

## The qa rejection's items

- The end-to-end tests name objects by full identifier: met. No 3.x form is
  left under `web/e2e`; the remaining `slug:` keys are the name a new
  taxonomy entry is created under.
- The three failures older than this item: met. `jira.spec.ts` opens the
  Request tab; the tags go in `.tcw/tcw-config.yaml`; the three new
  screenshots were looked at and show the 4.0 page.
- The two client defects found on the way: correct and small. `saved` is
  passed only by the new item form, and every other caller still asks;
  `fileStage` applies only to the item it was set for and is read once.
- The timing fixes wait on real conditions, none on a fixed sleep.
- `tcw init` refuses `TCW://` and `Tcw://` as it refuses `tcw://`, exit 2,
  nothing written.

No finding belongs to this change.

## Needs a separate change

Kept on the 4.0 run's list of small follow-ups, decided by the dispatching
session because each is minor, older than this round or outside what qa
asked for:

- `store_location_problem` (`tcw/config.py`) recognises only a lower-case
  `tcw://` in a configuration file; `TCW://…` there is read as a folder.
- A browser back or forward move does not clear `fileStage`, so coming back
  to the same item can open on the tab of the file last edited.
- The link picker moves the caret one animation frame late (from TCW-77).
