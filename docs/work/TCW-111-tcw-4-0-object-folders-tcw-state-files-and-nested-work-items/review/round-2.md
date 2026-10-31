---
verdict: accepted
judges: 2
---

# Review round 2 — TCW-111

Reviewed by a separate read-only agent (the `tcw:reviewer` agent) on
2026-10-24 in a frozen worktree at `85d9c2bb`, against review round 1's
items (a) to (c) and the change in `4f0eddd6..85d9c2bb`. Round 1 checked
every acceptance criterion and every capability record; its results are
carried forward.

## Checks run

- The full suite as CI runs it, `.venv/bin/pytest -q -p no:cacheprovider`,
  run by the dispatching session at `ec858dd6` in two halves by folder:
  `1982 passed, 2 skipped` and `4126 passed, 111 skipped`, recorded in
  `implement/round-2.md`. `pnpm test` `191 passed`; `tsc --noEmit`,
  `pnpm lint`, `pnpm check:build` clean.
- By the reviewer: `tests/test_removal_blockers.py`, `6 passed`; both tests
  compare the whole of standard error.
- By hand in a scratch project: `tcw taxonomy rm invoice` exits 3 with
  `cannot remove 'invoice': invoice/old holds a TCW 3.x meta.yaml; run 'tcw
  migrate' in this project first`, and `tcw capabilities rm cli/x` the same
  for its `item.yaml`; the prefix is not doubled and both 3.x files remain.

## Round 1's items

- (a) Met. "exit 1." is on one line; no line in either `upcoming/` entry
  starts a numbered list.
- (b) Met. `_blocked_removal` (`tcw/store/fs.py:1097`) writes the text spec
  2.5 gives, and is the one route for both removals. The `validate` finding
  for the same case keeps spec row f's form, without the prefix.
- (c) Met.

No finding belongs to this change, and none needs a separate change.
