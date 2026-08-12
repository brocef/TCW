# Implementation outcome

Three defects, all in the lookups around the claim protocol rather than in the
protocol itself. One of them broke the single-winner invariant.

## Delivered

1. **A claim takes an item out of `backlog` and nowhere else** (`91725c8`).
   `start()` resolved its claim source with `_find`, which searches every status
   folder, so between the status read at the top of `start()` and the claim
   lookup it could return the winner's item *after* publication to `active/`.
   `os.replace` then renamed that settled claim into the loser's private area —
   it succeeds, because nothing said a claim may only take an item from
   `backlog`. `_find` pointing anywhere outside `backlog` now means the race was
   lost, and routes into the existing `_lost_the_claim` recovery.

2. **`_find` re-walks before calling something a duplicate** (`91725c8`).
   `_item_dirs` walks the status folders in order, so an item moving from an
   earlier one to a later one — `backlog` → `active`, which is every claim — was
   counted in the folder it left and the folder it entered, and reported as
   `MultipleMatch`. Bounded re-walk: a genuine duplicate survives one, a
   transition does not.

3. **`_item_dirs` retries a walk that hits a vanished folder** (`91725c8`).
   `rglob` reaches each directory through `scandir`, which raises rather than
   skipping when it has gone, so one item leaving `backlog` mid-scan took down a
   read of the entire board.

Both re-walks are bounded at five attempts, after which the original error is
raised. A lock was rejected: the window is one rename wide, and a lock is a
filesystem-only mechanism with no analog in a remote adapter.

## Verification

- `python -m pytest -q`: **1225 passed**.
- **CI green on Python 3.11 and 3.14** — the point that matters, since two of
  these three defects have only ever appeared there.
- Three deterministic tests, each verified to fail without its fix:
  `test_a_loser_cannot_claim_the_winner_s_already_published_item`,
  `test_an_item_seen_in_two_status_folders_mid_move_is_not_a_duplicate`,
  `test_the_board_scan_survives_a_folder_vanishing_mid_walk`. A fourth,
  `test_a_genuine_duplicate_slug_still_raises`, passes either way by design — it
  guards against the re-walk swallowing the condition it was added to preserve.
- Stress: a standalone reproducer at 150 rounds × 4 contenders went from
  **7 violations to 0**, then 0 across 600 further rounds. The suite's stress
  test was raised from two contenders to four.
- `tcw taxonomy check`, `tcw capabilities check`, `tcw validate`,
  `git diff --check`: pass.

## What the previous item got wrong

This is worth recording precisely, because the same mistake produced two CI
rejections before this one.

- **The window enumeration was an enumeration of _reads_.** Its table classified
  `query()` → `_item_from_dir` as "same window, same fix" as `get()`. But the
  *scan* underneath both has two failure modes no per-item read guard can see,
  and they sit upstream of every guard that item added.
- **The claim lookup was never treated as a window at all.** It is not a read —
  it is a rename — so it fell outside the frame the enumeration was built in.
  That is where the severe defect lived.
- **The stress test's weakness was correctly identified and then
  under-corrected.** The previous outcome recorded that it passed with a bug
  present on a many-core machine and concluded it was evidence only on CI. The
  real problem was contender count: at two it passed 20 consecutive local runs
  with the steal present; at four it found it in roughly one round in twenty, on
  the same machine.

## Notes

`2026-06-22-…-atomic-owner-stamp` was accepted and completed before this was
found. `completed` is terminal in TCW, so it stays completed for what it
delivered — the read windows it closed are closed — and this item carries the
invariant its criterion 1 claimed. The correction is recorded in this item's
`initial-request.md` so the audit trail does not read as if that acceptance were
sound.
