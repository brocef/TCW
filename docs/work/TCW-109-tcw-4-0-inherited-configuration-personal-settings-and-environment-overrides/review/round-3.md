---
verdict: accepted
judges: 3
---

# Review round 3 — TCW-109

Reviewed by a separate read-only agent (the `tcw:reviewer` agent) on
2026-10-24 in a frozen worktree at `66ddacf7`, branch `impl-109` rebased onto
`v4` at `9de3de73` (TCW-107, 110, 108 and 111 landed), against review round
2's items (a) to (d), the point folded in after implement round 3, and the
combined change with TCW-111. Rounds 1 and 2 checked every acceptance
criterion; their results are carried forward.

## Checks run

- The full suite as CI runs it, `.venv/bin/pytest -q -p no:cacheprovider`,
  run by the dispatching session at `66ddacf7` in two halves by folder:
  `1985 passed, 2 skipped` and `4358 passed, 111 skipped`. `pnpm test`
  `191 passed`; `tsc --noEmit`, `pnpm lint`, `pnpm check:build` clean.
- By the reviewer: the item's eight test files, `483 passed, 3 skipped`;
  `tests/work/test_validate_work.py` and `tests/work/test_nested_items.py`,
  `35 passed`.
- By hand, scratch projects with every `TCW_*` variable unset.

## Round 2's items

- (a) Met. A parent after the missing one passing `work.jira: {bogus: 1,
  priorities: {bogus: x}}` gets two warnings at its file, as with no gap;
  before the gap, none.
- (b) Met. `bogus: {}` is reported behind a gap as without one, an error in
  the project and a warning in a later parent; `credentials: {}` does not
  decide both credential names.
- (c) Met. A variable naming project `b` holding `null`, `{a: 1}` or
  `[{inherit: 5}]` stops commands in `a` and `b`; `[1]` or a `file:` binding
  leaving `b`'s folder stops only `b`. Each message starts with the
  variable's name, as the release notes now say.
- (d) Met.
- The point folded in: the project's own `[{inherit: true}, 5]` is one error
  at `.tcw/tcw-config.yaml: work.tags[1]` behind a missing parent, with none,
  and with a parent passing tags; in a parent it is a warning after the gap
  and nothing before. Positions name the entry in the writer's own file,
  which also corrects stage `prompt` lists.
- The writing layer's rank matters only for a list entry under `work.tags`;
  no value written by the project or a later parent is still dropped, and no
  undecided value newly gets a warning.

## The combined change with TCW-111

The rebase conflict in `work_store_problems` (`tcw/work/fs_backend.py`) keeps
TCW-111's walk at any depth and TCW-109's withheld tags. With the tags
undecided, a nested item's tag is not checked, and the unresolved line says
the inherited configuration could not be checked (Design 3.6); with the tags
known, a bad tag on a nested item is a warning at its state file. No test
line added writes `item.yaml` or `meta.yaml`.

No finding belongs to this change.

## Needs a separate change

Kept on the 4.0 run's list of small follow-ups, decided by the dispatching
session because it has no visible effect today:

- `_merge` (`tcw/config.py:735`) keeps the recorded positions of `work.tags`
  entries when a later layer writes `work.tags` as something other than a
  list; the parser then reports without an index, so they are never read.
