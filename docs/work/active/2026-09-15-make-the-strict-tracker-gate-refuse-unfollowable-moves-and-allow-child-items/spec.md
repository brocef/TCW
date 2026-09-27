# Spec: strict gate refuses unfollowable moves; import nests children

## Capability changes

`work/require-tracker-backed-work`: the gate also refuses a move the ticket's
workflow cannot follow; `import` can nest a child. Its "Limits I accept"
paragraph changes: the nesting limit goes, and a sentence says an epic worktree
started before strict mode was enabled still merges.

## Problem

- `authorize` (`tcw/tracker/sync.py`) checks binding, assignee and status.
  `deliver` then picks a transition with `assess_move` (`sync.py` ~245), which
  refuses when the workflow offers no transition to the target, or several and
  no configured name picks one. The gate never asks, so a gated move can pass
  and then leave a conflicting record that refuses the next move.
- Strict mode refuses `new` except for epics; `tracker import` has no
  `--parent`/`--initiative`, so a child cannot be nested at all.

## Goals

1. `authorize` gains `move` and `resolution`; after its existing checks it asks
   `assess_move` with the configured transition name
   (`transition_name(config.move_transitions, move, resolution)`), exactly as
   `deliver` does, and refuses when that says there is no single transition to
   follow. Skipped when the target is unmapped, and when another open part of
   the ticket holds it (`deliver` returns HELD there without moving anything).
   Already at the target is `assess_move`'s own "current" answer.
2. `_strict_refusal` passes the move and the item's resolution (used for the
   configured transition name; `statuses.completed` is never per-resolution).
   Not asked of a legacy `catch-up` binding, which `deliver` walks.
3. `tcw work tracker import` accepts `--parent <slug>` and `--initiative <epic>`,
   validated before anything is claimed, with the same meaning as on `new`.
4. A regression test for the held item: strict, held, owed start record →
   `sync` → `submit` passes.
5. Capability text updated as above.

## Non-goals

- Letting `new --parent`/`--initiative` through under strict mode: both
  advisors read it as breaking the capability's "strict mode creates work only
  from a ticket", a product decision.
- Refusing the merge of a pre-strict epic worktree (it would trap the epic).
- `sync` exiting 0 when it skips a named slug (another item).

## Acceptance criteria

1. Strict, a workflow with no transition from the ticket's status to the
   submit target: `submit` is refused naming that, the item stays active, no
   record is written.
2. Two transitions to the target: refused without a configured name, accepted
   with one that selects exactly one.
3. A held sibling or an unmapped target: not refused by this check.
4. `tracker import <ticket> --parent <slug>` makes the child under `<slug>`;
   `--initiative <epic>` sets it; an unknown parent is refused before any
   tracker write.
5. The held-item regression test passes.
6. Full suite passes.

## Notes

- Advisors (2026-09-26) agreed on every point: refuse "none" and "several"
  through the same call `deliver` makes, with the move name; skip for held
  siblings and unmapped targets; §3 is already fixed; nest through `import`;
  document the epic case; drop the `claim_refusal` cross-reference. Both flagged
  "strict mode may create an item with no ticket" as a person's decision —
  which is why `new` stays refused.
