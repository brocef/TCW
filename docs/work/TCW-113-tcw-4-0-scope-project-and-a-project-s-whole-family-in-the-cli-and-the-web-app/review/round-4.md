---
verdict: rejected
judges: 4
---

# Review round 4 — TCW-113

Reviewed by a separate read-only agent (the `tcw:reviewer` agent) on
2026-10-24 in a frozen worktree at `465442aa`, against the qa rejection that
implement round 4 answers, over the TCW-113 commits after `82cdb4f9`.
Earlier rounds' results carry forward. The dispatching session checked each
finding against the code before writing this round.

## Checks run

- The full suite as CI runs it, run by the dispatching session at `065b52ce`
  in two halves by folder: `2185 passed, 2 skipped` and `5111 passed,
  111 skipped`, recorded in `implement/round-4.md`. `pnpm test`
  `239 passed`; `tsc --noEmit`, `pnpm lint`, `pnpm check:build` clean.
- By the reviewer: `tests/test_scope_reader.py` `25 passed`,
  `tests/work/test_scope_work.py` `26 passed`, `tests/serve/test_scope.py`
  `32 passed`; `pnpm test` `239 passed`.
- By hand, in a headless browser against `tcw serve` on a family: under
  `down` and `all`, each project linked in a capability's "Status by
  project" opens that project's own object with one request; typed addresses
  in both forms open it, also under `own`; a missing object or an unknown
  project says so beside the list; the served project's own entry under a
  filter that leaves it out still clears the pane. Under a project filter the
  command line's text and `--json`, `/api/work` and the board agree on what
  is left out and why. `--project nosuch` gives the new ending, exit 2, and
  the web answers 400 with the same words; a known project outside the
  family keeps the old ending.

## Round 4's items

- (a) Met, except finding 1, which this round's change opened.
- (b) Met.
- (c) Met. Design 2.2's message template in the spec still lists two endings.

## Findings

1. `web/client/src/ui/app.tsx:484-487` and `:1540`: the term and capability
   effect clears `detail` but not `detailError` when the axis is work, and the
   pane now shows `detailError` on every axis. Open
   `/capabilities/desktop.capabilities/nosuch`, then click Work: the board's
   pane says "no such capability" until an item is picked.
2. `web/client/src/ui/content-views.tsx:327-336`: "Status by project" links
   only the page's own object and those that override it. On another
   project's override page, `Missing: shared | Supported: desktop | Omitted:
   server` links only `desktop`, to itself, where Design 6.9 links each
   project that has its own object at the path.

## Needs a separate change

Folded into the next round by the dispatching session, since finding 2's fix
adds more links to the page already shown: following a link to the page
already shown clears it (`navigateTo`, `app.tsx:584-600`, sets the detail to
nothing while the selection stays the same, so nothing loads it again).

Kept on the 4.0 run's list of small follow-ups: the served project's own
entry is fetched twice on first load (older than this round).

## What implement must do

- (a) Clear the error with the detail when leaving an axis, with a test of
  the path above.
- (b) Link every project in "Status by project" that has its own object at
  the path, from `statuses`, on every page that shows it.
- (c) Following a link to the page already shown keeps it shown.
- (d) Bring Design 2.2's message template in line with the three endings,
  as a note in the round (the spec is not edited at implement).
- (e) `implement/round-5.md`.
