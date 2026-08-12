# Upcoming

Developer changelog for the next version. Technical and precise; grouped by
category.

## Fixed

- `FsWorkStore._item_from_dir` returns `None` when the item folder goes away
  mid-read, instead of raising out of whichever guarded read lost the race.
  Every read it performs (`load_yaml`, `read_text`, `stat`) tests for the file
  and then opens it, so each was its own window onto a competing claim's
  `os.replace`; CI hit the `state.yaml` one as `FileNotFoundError` from
  `get()` → `_item_from_dir` → `_safe_yaml`. Two conditions are checked, because
  `load_yaml` answers `{}` for an absent file and `_safe_yaml` tolerates a
  malformed one — without an explicit re-check for `state.yaml` after the read, a
  folder already gone reads back as a *valid* item full of defaults, reporting
  its old status. `query()` drops such items from the board; `get()` returns
  `None`, which its signature already promised.
- `FsWorkStore.start()` no longer reports `no such work item` to a claim loser.
  An empty read now looks for the claim before denying the item exists: an
  in-flight claim in `.claiming/` routes to the shared loser path, and a
  re-read of `get()` catches a winner that published to `active/` in the
  meantime. Both land on the same typed `AlreadyClaimed` carrying the winner's
  owner and start time.
- `FsWorkStore._claiming_dirs()` matches the 32-character uuid suffix instead of
  `-*`, which spans `-` and let a claim on a longer slug answer for a shorter
  one. Slugs are prefixes of each other by construction — `_unique_slug` mints
  `{base}-2` for a duplicate title — so `tcw work start <absent-slug>` could
  stall 500 ms and then report an interrupted claim belonging to a different
  item, for as long as a stale claim folder sat in `.claiming/`. The `--take-over`
  lookup, which refuses when it sees more than one candidate, is fixed by the
  same change.
- `FsWorkStore.artifacts()` returns `[]` rather than raising when the folder is
  claimed away between its `is_file()` test and the `read_text()` that test
  guards. This is the board's own window — `tcw work list` renders its
  `R`/`S`/`P`/`O` letters through this call, so a concurrent claim could take
  down the board with a traceback.

## Internal

- Added `FsWorkStore._lost_the_claim()` (`NoReturn`), the extracted
  wait-for-the-winner recovery loop, and `_claiming_dirs()`. Every way of losing
  a claim — `os.replace` raising, `_find` coming back empty, the item vanishing
  under a read — now ends in one place instead of three near-copies.
- `_item_from_dir`'s reading body moved unchanged into `_read_item`; the outer
  function is now the vanish guard.
- Eight new tests in `tests/test_external_work_store.py`, each failing against
  the code it pins. `test_repeated_claim_races_have_exactly_one_winner`
  runs the two-thread race 25 times to satisfy the acceptance criterion asking
  for repeated races; note that it passes with the defect present on a
  many-core machine, so it is evidence only on constrained CI schedulers.
