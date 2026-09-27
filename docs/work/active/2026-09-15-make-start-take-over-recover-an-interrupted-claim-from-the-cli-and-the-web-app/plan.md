# Plan: make start --take-over recover an interrupted claim from the CLI and the web app

## Tasks

1. **Store.** Tests first in `tests/test_interrupted_claim.py`: an interrupted
   claim is listed with its own slug and status `backlog`; a settled item and a
   store with no `.claiming` list nothing. Add `interrupted_claims` to
   `tcw/store/base.py` (default `[]`) and `FsWorkStore`.
2. **CLI.** Tests first (same file): criteria 1-4 through `main(["work",
   "start", ...])`, including the refusing tagged `pre` hook. Rework `_start` in
   `tcw/work/cli.py`.
3. **Server.** Tests first in `tests/test_interrupted_claim.py` using the
   serve test helpers: criterion 5. Add the GET route and `recover` to the start
   action in `tcw/serve/__init__.py`; guard `_strict_refuses`.
4. **Client.** `web/client/src/ui/`: load `/api/work/interrupted-claims` with the
   board, render the notice and Recover button; a vitest test for the component
   (criterion 6). Rebuild `tcw/serve/dist`.
5. **End to end.** `pnpm test:e2e` (criterion 7).

## Documentation Sync

- Changelog and release notes: Fixed entries.
- `docs/guide/work.md` [Guide-Topic-Change]: where `--take-over` is described,
  say it recovers an interrupted claim and that the web app offers Recover.
- `skills/work` references [Skill-Driven-Component]: check the take-over wording.
- `docs/guide/jira.md` [Tracker-Change]: recovery under strict mode does not claim
  the ticket again — add if the guide describes strict start.

## Verification

Hands-on: in a scratch node, make an interrupted claim by hand, recover it with
the worktree's `tcw`; then with `tcw serve` in the Claude Chrome profile, see the
notice and press Recover.
