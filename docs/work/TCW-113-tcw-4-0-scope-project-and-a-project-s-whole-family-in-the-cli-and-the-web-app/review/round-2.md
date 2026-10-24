---
verdict: rejected
judges: 2
---

# Review round 2 — TCW-113

Reviewed by a separate read-only agent (the `tcw:reviewer` agent) on
2026-10-24 in a frozen worktree at `4faea341`, against review round 1's
items (a) to (c), over `975dfffd..4faea341`. Round 1's acceptance-criterion
results carry forward.

The reviewer recommended accepting, and placed its one finding under "needs
a separate change" because the code is older than this round. The code is
TCW-113's own, from implement round 1, and the finding breaks TCW-113's
Design 2.3 and 6.2, so the dispatching session counts it as belonging to
this change. The user's rule for the TCW-99 children is that an item is
accepted only with no open finding belonging to the change, so this round
is recorded as rejected.

## Checks run

- The full suite as CI runs it, run by the dispatching session at `e0010a77`
  in two halves by folder: `2172 passed, 2 skipped` and `4879 passed,
  111 skipped`, recorded in `implement/round-2.md`. `pnpm test`
  `229 passed`; `tsc --noEmit`, `pnpm lint`, `pnpm check:build` clean.
- By the reviewer: `tests/serve/test_scope.py` and
  `tests/serve/test_other_project.py`, `42 passed`;
  `tests/work/test_scope_work.py`, `24 passed`.
- By hand, through a guarded wrapper, on a family served from `shared`: for
  an item a wider scope covers, a sibling's item no scope covers, and the
  served project's own item, under all four scopes, `tcw work show <full id>
  --scope <s> --json` and `GET /api/work/<full id>?scope=<s>` give identical
  children and blocks with no duplicates, in all 12 cases. A project not on
  this machine is warned about and left out. In a headless browser, another
  project's item page names `tcw -C tcw://<owner>.path/ work advance <full
  id>`, which run from `shared` moves the item; the plain form is refused
  with TCW-114's message.

## Round 1's items

- (a) Met. Every case counts each project's items once; the two callers of
  `every_item` are the only ones. The fallback for a failed read was checked
  from the code; no test covers the Jira branch.
- (b) Met.
- (c) Met.

## Findings

1. `tcw/serve/work.py:380-396`, `detail()`: a full identifier of one project
   with `?project=` naming another answers 200. `GET
   /api/work/desktop.work%2F<item>?scope=down&project=server` shows
   `desktop`'s item, where `tcw work show desktop.work/<item> --scope down
   --project server` exits 2 naming both (Design 2.3), and Design 6.2 asks the
   routes to answer what `show --json` gives for the same input. A link
   followed while the page's project filter names another project shows a
   page the command line refuses.

## What implement must do

- (a) The detail routes refuse a full identifier whose project is not the
  `project` parameter, with the same message as Design 2.3's usage error and
  a 400 answer, with a test; check the taxonomy and capabilities detail
  routes for the same.
- (b) `implement/round-3.md`.
