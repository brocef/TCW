# Stop a claim loser from stealing the winner's published item

## Capability changes

None. `work/start-a-work-item` and `work/view-the-board` already describe the
behavior this restores; they were describing something the implementation did
not actually guarantee.

## Problem

See `initial-request.md`. Three defects, one severe: `start()` resolves its claim
source with `_find`, which searches every status folder, so a loser can rename
the winner's already-published item out of `active/` and claim it.

## Goals

- A claim moves an item out of `backlog` and nowhere else, so exactly one caller
  can ever win regardless of contender count.
- A board read does not raise while an item is being claimed — neither
  `MultipleMatch` for a transition in flight, nor `FileNotFoundError` from the
  walk.
- Each defect gets a deterministic test, not only a probabilistic one.

## Non-goals

- Changing the claim protocol's shape (private rename, stamp, publish). All
  three fixes are guards on lookups, not a redesign.
- The deferred reader findings in
  `2026-08-12-teach-the-remaining-readers-to-tell-a-vanished-item-from-an-absent-one`.

## Design

1. **`start()`** — reject a claim source outside `backlog`, routing it into the
   existing `_lost_the_claim` recovery so the loser is told who won.
2. **`_find`** — re-walk, bounded, before raising `MultipleMatch`. A genuine
   duplicate persists across walks; a transition does not.
3. **`_item_dirs`** — retry the walk, bounded, on `FileNotFoundError`.

A re-walk rather than a lock: the window is one rename wide, the store is
already single-winner by rename, and a lock would be a filesystem-only mechanism
with no analog in a remote adapter.

## Acceptance criteria

- Four contenders racing on the same item produce exactly one success, in a
  stress run long enough to have caught the defect (it appeared 7 times in 150
  rounds before the fix).
- A loser whose `_find` returns the winner's published item raises
  `AlreadyClaimed` naming the winner, leaves the item in `active` with the
  winner's owner intact, and leaves no residue in `.claiming/`.
- An item visible in two status folders during one walk resolves to one item; a
  genuine duplicate slug still raises `MultipleMatch`.
- A walk that hits a vanished directory still returns the rest of the board.
- The full suite passes on **CI**, on every supported Python, not only locally.

## Risks

- The bounded re-walks convert a crash into a delay under pathological
  contention. Bounded at five attempts, after which the original error is
  raised.
- CI is the only place two of these defects have ever appeared. A green local
  suite is not evidence; the criteria are only met once CI is green.
