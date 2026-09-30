# Plan — Let a started item still pass its planning gates, or stop start from letting it past them

Worked in a worktree (`start --worktree`), with a scratch venv pinned to it.

## Task 1 — Failing tests

**Creates** `tests/test_planning_gates_after_start.py`, with one test per
acceptance criterion 1-6. Each uses a scratch node, driving the CLI in-process
as `tests/test_transition_hints.py` does. Criteria 1, 2, 4, 5 and 6 are
committed `xfail(strict=True)`. Criterion 3 passes today and must keep
passing.

## Task 2 — Legality and the start warning

**Modifies** `tcw/store/base.py`:

- `STAGE_STATUSES["request"]` gains `active`, and its comment is extended;
- `start_next_stage` returns `request` first when `initial-request` is absent.

**Modifies** `tcw/work/cli.py`: `_unwritten_plan` becomes
`_unwritten_planning`, covering `initial-request`, and both callers (`start`
and the implement gate) are updated.

**Re-baselines** `tests/fixtures/lifecycle_baseline/self.json` for `request`'s
legality, following that fixture's capture notes. Only the `request` legality
may move, and that is asserted before the new bytes are written.

**Updates** the existing tests that pinned `request`'s legality or `start`'s
next-step hint for an item without a request (`tests/test_transition_hints.py`
and any others that grep finds). **Proves** criteria 1-3 and 6.

## Task 3 — The refusal's hint

**Modifies** `tcw/work/cli.py` `_stage`: one line after the existing refusal,
following goal 4 (`review` → `rework`; `backlog` → `start`; resolved →
nothing runs; open → `stage prompt`, without checks). **Proves** criteria 4-5.

## Task 4 — Documentation Sync

- `skills/work/references/transitions.md` and `skills/work/SKILL.md`, wherever
  stage legality or the start warning is described (grep for "legal in",
  "can still be written"). [Skill-Driven-Component]
- `docs/guide/work.md`, wherever stage legality is described.
  [Guide-Topic-Change]
- The capability descriptions `work/run-a-lifecycle-stage` and
  `work/start-a-work-item`, and the item's `capabilities.yaml`.
- The changelog and release notes.

## Task 5 — Full suite

Bare `pytest`, with the venv first on PATH. **Proves** criterion 7.

## Verification

By hand in a scratch node: start an item that has only a title, read the
warning and the next step, then run `stage gate request`. Submit it, then try
`stage gate spec` and read the refusal.
