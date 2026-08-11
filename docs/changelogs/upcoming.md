# Upcoming

Developer changelog for the next version. Technical and precise; grouped by
category.

## Fixed

- `FsWorkStore._effect_transition` no longer reaches `git_mv` with `None` when a
  competing process moves the item between its two lookups. It raises
  `ValueError` naming the item's re-read current status, which the work CLI
  already handles (`_ERRORS`), so `submit`/`rework`/`complete` exit 1 with a
  message instead of a traceback. Previously this surfaced as `FileNotFoundError`
  from `shutil.move("None", …)` when the destination is gitignored — the default
  for `completed/` and `discarded/` — or `CalledProcessError` from
  `git add -- None` when it is tracked.
- Four other `_find` results that were dereferenced unguarded now degrade
  cleanly: `start()`'s take-over commit lookup and `_plan_stage_path` raise
  `ValueError` (were `AttributeError` and `TypeError`), and `get_detail` returns
  `None`, which its signature already promised (was `TypeError`).
- `check()` (behind `tcw work validate`) raises no `TypeError` when an item
  vanishes mid-scan; the `ValueError` is absorbed by the enclosing handler.
  **Output change:** a validation sweep that races a *healthy* transition now
  reports `<slug>: no such work item: <slug>` against an item with nothing wrong
  with it. A spurious line beats a traceback, but anyone parsing that output
  should know it can appear.

## Internal

- Added `FsWorkStore._require_dir`, collapsing eight identical
  `_find` + `raise ValueError(f"no such work item: {slug}")` guards. Behavior
  preserving — same type, same message, and `MultipleMatch` still propagates from
  `_find` above the guard. The parent lookups keep their own
  `no such parent work item` message and are untouched.
- `tests/test_external_work_store.py` pins a known-unfixed residual: a `complete`
  that loses the race has already written its `resolution` before the move, so
  the write survives the refused transition. Tracked as
  `2026-08-11-roll-back-or-reorder-the-pre-move-set-field-writes-on-a-lost-transition`.
