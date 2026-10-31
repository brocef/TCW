---
verdict: rejected
judges: 5
---

# Review round 5 — TCW-113

Reviewed by a separate read-only agent (the `tcw:reviewer` agent) on
2026-10-24 in a frozen worktree at `80980199`, against review round 4's
items, over `2bfa8b82..80980199`. Earlier rounds' results carry forward.

This round's one finding is a hole in round 5's own fix. Under the user's
review rule, the dispatching session brought the split to the user rather
than start another round; the user chose to run implement round 6 for this
finding, with a review bounded to it.

## Checks run

- The full suite as CI runs it, run by the dispatching session at `a3cc6ce2`
  in two halves by folder: `2185 passed, 2 skipped` and `5111 passed,
  111 skipped`, recorded in `implement/round-5.md`. `pnpm test`
  `245 passed`; `tsc --noEmit`, `pnpm lint`, `pnpm check:build` clean.
- By the reviewer: `pnpm test` `245 passed`; each of round 5's fixes undone
  in a scratch copy sends its own tests red.
- By hand, in a headless browser against `tcw serve` on a family: a "no such
  capability" page followed by Work, or by the back button, leaves the
  board's pane empty, and a missing work item still shows its error; a link
  to the page already shown makes no request and keeps it; a row clicked
  twice, another row, another axis and the back button behave as before.

## Round 4's items

- (a) Met. (c) Met. (d) Met (noted in implement round 5).
- (b) Met where a project's own object sets its status or the record names
  it; not met otherwise (finding 1).

## Findings

1. `web/client/src/ui/content-views.tsx:327-346` with
   `tcw/store/base.py:580-584`: a project whose own object at the path sets
   no Status is reported `inherited: true`, and unless the record names it
   (`overridden-by` lists only direct overrides) the status line shows it as
   plain text. With `server`'s own `abc` holding only a name, desktop's
   override page under `down` shows "Missing: shared, server (inherited)"
   with `server` unlinked, though `server.capabilities/abc` exists; a
   grandchild's override that sets no Status is unlinked on the served
   page too. Design 6.9 links each project that has its own object at the
   path. A hole in round 5's fix of round 4's finding 2.

No finding needs a separate change.

## What implement must do

- (a) Give each `statuses` entry the full identifier of the object its
  project's view comes from, and link an entry whenever that identifier's
  owner is the entry's project; tests on the server answer and the client,
  including a project whose own object sets no Status and a grandchild's
  override.
- (b) `implement/round-6.md`.
