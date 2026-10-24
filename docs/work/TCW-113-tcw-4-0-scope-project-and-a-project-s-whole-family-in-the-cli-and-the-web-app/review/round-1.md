---
verdict: rejected
judges: 1
---

# Review round 1 — TCW-113

Reviewed by a separate read-only agent (the `tcw:reviewer` agent) on
2026-10-24 in a frozen worktree at `2c59c59a`, branch `v4` with TCW-113
landed after its rebase onto `93b17acb` (TCW-114 completed), over
`93b17acb..2c59c59a`. The dispatching session checked each finding against
the code before writing this round.

## Checks run

- The full suite as CI runs it, `.venv/bin/pytest -q -p no:cacheprovider`,
  run by the dispatching session on the rebased branch at `8dedb0ca` in two
  halves by folder: `2169 passed, 2 skipped` and `4879 passed, 111 skipped`.
  `pnpm test` `227 passed`; `tsc --noEmit`, `pnpm lint`, `pnpm check:build`
  clean. The implementing agent ran the end-to-end suite before the rebase,
  `18 passed`.
- By the reviewer: TCW-113's new test files, `401 passed` and `83 passed`;
  the shipped-text and help tests, `785 passed, 2 skipped`.
- By hand, through a guarded wrapper with every `TCW_*` variable unset and
  scratch home folders, on a family of projects with one not on this
  machine: `work list` under each scope lists the right projects in scope
  order, with one warning line for the missing one; `--project` outside the
  family and `--scope own --project <child>` exit 2 naming the way;
  another project's missing object exits 5; `capabilities show --scope down`
  prints the status-by-project block; a single project's `show` is the same
  under every scope. Under `tcw serve` with a headless browser: every write
  route answers 403 `read-only` for another project's object and its files
  are unchanged; another project's item page has no editing controls.

## Acceptance criteria

AC 1 to 41 are met by their named tests, several also by hand (AC 30, 33,
34, 35 by hand). The capability records match what was observed. The
mutation results and per-step comparisons in implement round 1 were not
repeated.

## Findings

1. `tcw/serve/work.py:383-405` with `tcw/work/scoped.py:124-138`: the web
   detail of another project's item, under a scope, passes the owner's
   backend to `every_item`, which takes its second argument as the served
   project's. The owner's items are read twice and the served project's not
   at all. In a family where the served project `shared` and its child
   `desktop` each have a child of `desktop.work/<item>`, `GET
   /api/work/desktop.work%2F<item>?scope=down` answers `desktop`'s child
   twice and never `shared`'s, where `tcw work show <item> --scope down`
   gives both once each (Design 3.3, 6.2). Blocks are affected the same way,
   and so is an item of a project the scope does not cover.
2. `web/client/src/ui/work-views.tsx:390`: another project's read-only item
   page says "Move it with tcw work advance <full id>", a command that is
   refused in the served project with TCW-114's "run the command there"
   message. Folded in by the dispatching session as a small follow-up.

## Needs a separate change

- The advice for a project whose work store is declared and not on this
  machine says `run tcw provision`, which from the active project would fetch
  the active project's own stores. TCW-115 renames that command and is
  correcting this advice in its round joining TCW-113 on `v4`.
- `tests/test_tree_parent_missing.py:58-59, 98, 193` and
  `tests/test_overrides_by_path.py:417`: docstrings still describe
  `list --local` (TCW-117's pass).

## What implement must do

- (a) The web detail of another project's item counts children and blocks
  from every covered project once each, the served project's included, and
  an uncovered owner's own items once, matching `tcw work show --scope`;
  with a server test where each of two projects holds a child.
- (b) Another project's item page names the `tcw -C` form of the move
  command, or no command.
- (c) `implement/round-2.md`.
