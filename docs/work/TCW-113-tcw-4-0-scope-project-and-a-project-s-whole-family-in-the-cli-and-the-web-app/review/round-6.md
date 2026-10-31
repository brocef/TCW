---
verdict: accepted
judges: 6
---

# Review round 6 — TCW-113

Reviewed by a separate read-only agent (the `tcw:reviewer` agent) on
2026-10-24 in a frozen worktree at `1ec9eb10`, against review round 5's
finding, over `50305f8e..1ec9eb10`. The round was bounded to that finding and
to whether round 6's change opened a new defect, as the user chose. Earlier
rounds' results carry forward.

## Checks run

- The full suite as CI runs it, run by the dispatching session at `385b8d05`
  in two halves by folder: `2186 passed, 2 skipped` and `5112 passed,
  111 skipped`, recorded in `implement/round-6.md`. `pnpm test`
  `247 passed`; `tsc --noEmit`, `pnpm lint`, `pnpm check:build` clean.
- By the reviewer: `tests/test_scope_trees.py` and `tests/test_scope_rows.py`
  `62 passed`; `tests/serve/test_scope.py` `33 passed`; `pnpm test`
  `247 passed`. Three mutations, made in a scratch copy, each turn tests red.
- By hand, through a guarded wrapper and the command line: each `statuses`
  entry's `full-id` names the project's own object whether or not it sets a
  Status, else the object it inherits, from a parent or under `all` from a
  grandparent; an unavailable project has no entry; the text output is
  unchanged. In a headless browser against `tcw serve`: on desktop's override
  page under `down`, `server`, whose own object sets no Status, is linked and
  opens its own object; on the served page a grandchild's own object is
  linked; projects that only inherit stay plain text.

## Round 5's finding

Met. A project owns at most one object at a path, so the client's link can
never point at the wrong object, and an inheriting entry links only for the
project it inherits from.

The implementing agent also listed the new field in the spec's Design 4.6,
marked as added in implement round 6, and in the capability record; both are
accurate. Decided by the dispatching session: the spec edit is kept, since it
records the record's shape as shipped and is marked as made at implement.

No finding belongs to this change, and none needs a separate change.
