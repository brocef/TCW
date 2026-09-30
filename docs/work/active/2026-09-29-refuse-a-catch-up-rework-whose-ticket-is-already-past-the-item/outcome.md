# Outcome — Refuse a catch-up rework whose ticket is already past the item

## What changed

- `tcw/tracker/sync.py`: `catch_up_declines(statuses, ticket_status, local,
  expected, syncing)` decides when `deliver`'s catch-up branch declines a ticket
  above its item — only for a `sync` with no window of its own. Every other
  case whose ticket is above the item skips the catch-up walk and is carried as
  on a binding without `catch-up`: a rework applies its own configured
  transition (not the start transition the walk would have used), a start is
  held. `_above_item` is the shared "ticket's rung above the item's" test.
- Review fix: a `sync` replaying a start that is still owed — its ticket held
  by this account above an active item, and not done — ends held and drops the
  record, as the live start does. Before, it re-recorded the conflict on every
  `sync`, and under strict mode every later move was refused with "run sync
  first".

## Commits

- eb5a7cb5 tests (failing cases `xfail(strict=True)`)
- d09d2efe the fix and the table test
- 689d437a documentation
- 7dcd9a8e review fixes: the replayed start, `_above_item`, the replay table
  test, a corrected comment, changelog and plan notes

## Evidence

- `tests/test_tracker_catch_up_moves.py`: 21 tests — rework in strict and
  non-strict mode (applies transition "42", leaves no record, clears
  `catch-up`); a start held; a recorded rework conflict and a recorded start
  conflict each clear on `sync` (both modes for the start, then `submit`
  succeeds); a Done ticket still refused (rework, and a replayed start); a
  completion still works; a table pinning that no gated move is declined
  inside the strict gate's allowed statuses; a table pinning that every
  replayed move except a start carries a window.
- Mutation checks: restoring the old behavior, dropping `not expected`, and
  `return False` each turned tests red (8, 1 and 5 failures); after review,
  disabling the held branch (2 failures) and dropping its `done` guard (1).
- All 1205 tracker tests pass (`-k tracker`) at 7dcd9a8e. Full suite: see
  below.
- Hands-on: the CLI was exercised only through these tests, which run the
  real commands against an in-process fake tracker. Not run against a real
  Jira: that would move real tickets on a shared board.

## What the plan or spec got wrong

- The plan put the tests into `test_tracker_strict_gate.py` and
  `test_tracker_sync.py`; they went into a new file importing their helpers.
- Goal 4 ("a conflict recorded by the old behavior clears on the next sync")
  held only for a rework record until review; a replayed start has no window
  and was declined again. Fixed in this item rather than narrowed.

## Autonomous decisions

- **Spec — where to fix, and how widely.** Opus and Sonnet (in place of Codex,
  at its usage limit until 2026-10-03) both chose fixing `deliver` over adding
  a gate refusal. They split on scope: Sonnet limited it to backward moves
  inside the window; Opus generalised it to any lifecycle move and found the
  matching start defect. Took Opus's rule after checking it against the order
  of branches in `deliver` — the catch-up branch returns before the held
  branch, so the start was affected too.
- **Review, Significant 1 (a replayed start never clears).** Accepted and fixed
  here rather than splitting it out: it is the start half of the same defect,
  and narrowing goal 4 would ship a known permanent conflict under strict mode.
  Held only when the item is active, the ticket is not done and this account
  holds it; everything else still declines.
- **Review, duplicated "above the item" test.** Partly accepted: the two new
  copies now share `_above_item`; the three older copies elsewhere in
  `deliver` are left, as rewriting unrelated branches is not this item's.
- **Review, the table test is near trivially true.** Accepted: added the
  replay table the reviewer proposed, which would have exposed Significant 1.
- **Review, comment overstating the window check.** Accepted and reworded.
- **Review, a rework `sync` replay on a ticket held by someone else says "not
  claimed or moved back" instead of naming the holder.** Rejected as a change
  here: it is still a refusal, never moves the ticket, is unreachable from the
  CLI (the rework itself refuses first) and is wording in an unchanged branch.
