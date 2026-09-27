# Outcome: show the server's message for a web save refused for a reason other than a stale revision

## What shipped

- **Tasks 1-2** — `92081d24`.
  - Server: `_map_store_error` (`tcw/serve/__init__.py`) adds
    `"code": "stale-revision"` to every stale-revision 409.
  - Client: `isStaleWrite(result)` in `web/client/src/model/api.ts`, used by both
    save branches of `web/client/src/ui/app.tsx`; any other failed save shows
    `result.error` and keeps the draft.
  - `tcw/serve/dist` rebuilt from the client.
  - Tests: `tests/test_serve_write.py` (marker present on stale PATCH and PUT,
    absent on the generated-sidecar refusal); `web/client/src/model/api.test.ts`.
- **Documentation** — `ded50a42`.
- **Review fixes** — `0f16dd8e`: the strict-refusal server test asserts no
  stale marker; the release note reworded (see Autonomous decisions).

## Tests

- Server tests went red on the old code (`KeyError: 'code'`); the client test
  went red, for the two non-stale 409 cases, against a version of `isStaleWrite`
  that treated every 409 as stale.
- `tests/test_serve_write.py` + `tests/test_tracker_strict.py`: 269 passed.
- vitest: 72 passed; `tsc --noEmit`, eslint and prettier clean on the changed files.
- Playwright (`web/e2e`, against `tcw serve` from the worktree): **14 passed**,
  including "edits lifecycle artifacts and preserves a draft across a stale
  write", which checks the banner on a real concurrent edit.
- Hands-on against `tcw serve` from the worktree in a scratch node: a PUT to
  `rollup.md` returned 409 with only its `error` text; a PATCH with a stale
  revision returned 409 with `"code": "stale-revision"`.
- Full Python suite: 4475 passed, 3 skipped (before the review fold-in, which changed one test assertion and a release note; that test file re-run green).

## What the plan or spec got wrong

- **No UI path reaches a non-stale 409 today.** The app shows no edit control for
  a generated sidecar, and the strict-tracker refusals are on routes whose
  handler already showed the message. The fix is a guard against the next such
  refusal, and the release note was reworded not to claim users hit it.
- **The plan's Verification paragraph is muddled** ("send the PUT from the page's
  console with the app's own code path unavailable"). What was done instead: the
  server half by hand with `curl`, the client half by the unit test, and the
  stale banner by the Playwright test.
- **`pnpm check:build` cannot be trusted in a worktree** whose `node_modules` is a
  link to the main checkout's: esbuild then embeds `../../node_modules/...` paths
  in `tcw/serve/dist/server.cjs`. The server bundle was restored from `HEAD` (its
  source did not change); the client bundle carries no such paths.
- **`app.tsx`'s switch itself is untested** beyond the helper and the end-to-end
  stale test; a revert of one branch to `status === 409` would not fail a test.
  Accepted for a two-line change.

## Documentation Sync

| Entry | Fired? | Done |
| --- | --- | --- |
| `README.md` [Public-API] | No | — |
| `docs/guide/jira.md` [Tracker-Change] | No | — |
| `docs/guide/<topic>.md` [Guide-Topic-Change] | No | No guide describes the banner. |
| `docs/release-notes/upcoming.md` [Public-API] | Yes | One line. |
| `docs/changelogs/upcoming.md` [Any-Code-Change] | Yes | Fixed entry, names the new `code` field. |
| `skills/<component>/SKILL.md` | No | — |
| `skills/configure/references/<document>.md` | No | — |

## Autonomous decisions

Run unattended on 2026-09-26 (`extras-autonomous-work`).

- **Spec: a body marker (A), a different status for other refusals (B), or
  parsing the message (C)?** Codex: A — B breaks tests pinning 409
  (`test_serve_write.py:737`, `test_tracker_strict.py:1021`), C couples to
  wording. Opus: A, for the same reasons, and noted the bug is narrower than
  the ticket says (only the generated-sidecar PUT reaches a save branch). Both
  confirmed every stale 409 goes through `_map_store_error`. Chose A.
- **Plan-stage delete (`app.tsx:744`).** Both advisors: correct today (its route
  only 409s through `StaleRevision`); left out of scope.
- **Code review** (adversarial-code-reviewer): DONE, merge with notes.
  Accepted: the release note overstated what users saw (reworded); the strict
  refusals lacked a no-marker assertion (added). Recorded rather than changed:
  the untested `app.tsx` switch (above); the "Validation errors" heading shown
  above a non-validation message (cosmetic, pre-existing).
- **Verify** (tcw:verifier): accept; criteria 1, 2, 4 met on its own runs,
  3 on the implementer's Playwright run. Noted, not changed: the strict-refusal
  test asserts the marker's text is absent rather than a `code` key; the
  `app.tsx` switch is covered only through the helper and the end-to-end stale
  test. Decision: accept.
