# Spec — Close two strict-mode gaps left by the unfollowable-move gate

## Capability changes

None.

## Reproduction

From the code on `bug-run` (2026-09-29), with the fakes in
`tests/test_tracker_strict_gate.py`:

1. Strict node, catch-up binding, item in review, ticket In Review assigned to
   Bob: `tcw work complete <slug> --resolution done` passes `authorize`
   (called with `ownership=False`, `tcw/work/cli.py` ~4085), then `deliver`'s
   `resolving` rule (`tcw/tracker/sync.py` ~401) says a catch-up completion
   needs the ticket held, and a conflict is recorded after the item completed.
2. Strict node, catch-up binding, item active, ticket In Progress, workflow
   `BROKEN_LADDER` (no way out of In Review): `authorize` computes `walked`
   (~1080) and skips `assess_move`; `complete` completes the item, then the
   walk stops in In Review with a `conflicting` record.

## Problem

The gate and `deliver` disagree on a catch-up binding: about whether a
completion needs the ticket held, and about whether a multi-rung walk can be
followed — which the gate cannot know, since Jira reports only the transitions
offered from the ticket's current status.

**Sibling sweep** (`grep -n "catch_up" tcw/tracker/sync.py`): `deliver`'s
`takes_ticket` and `resolving`, the walk at ~812, the conflict note at ~905, and
the gate's `walked`. Only the gate's two decisions are wrong.

## Goals

1. The gate asks who holds the ticket for a catch-up completion, by the same
   rule `deliver` uses — one helper, `needs_claim(move, bound)`, read by both.
2. The gate refuses a move whose catch-up walk is more than one rung, saying
   which statuses the ticket would pass through and to move the item one step at
   a time (for `complete` from active: `tcw work submit` first). Each single
   step is then checked as any other move is.

## Non-goals

- Non-strict mode (no gate runs).
- Clearing `catch-up` by any new path; the one-rung moves clear it as they do today.
- The `tracker import --parent` gap (its own item).

## Design

- `sync.py`: `needs_claim(move, bound) -> bool` = `move not in
  MOVES_NEEDING_NO_CLAIM or (bound.catch_up and move == "complete")`.
  `deliver`'s `resolving` becomes `not needs_claim(assessed, bound)` when
  `assessed` is set (unchanged meaning). In `authorize`, after the binding is
  read, `ownership = ownership or (move is not None and needs_claim(move, bound))`.
- `authorize`: where `walked` is true (and the existing `move`, `target`, `not
  held` guards hold), return a refusal instead of skipping the check:
  "<key> is in '<status>' and would have to pass through <rungs> to follow this
  change, one transition at a time, which cannot be checked before it is made.
  Move <slug> one step at a time (…), so each step is checked."

## Abstraction litmus test

Tracker-gate code; no store operation changes.

## Acceptance criteria

1. Reproduction 1 is refused before anything moves: exit 1, "assigned to Bob"
   in the message, the item still in review, no record, nothing applied.
2. Reproduction 2 is refused before anything moves: exit 1, the message names
   `In Review` and says to move one step at a time; the item still active.
3. On `STRICT_LADDER` (every rung present), the same item is refused at
   `complete` from active, then `submit` passes and `complete` passes, and the
   ticket ends in Done.
4. A catch-up completion with the ticket held by the running account, one rung
   away, still passes.
5. The full test suite passes.

## Risks

- A catch-up binding whose walk would have succeeded now needs one extra command
  (criterion 3). Accepted: the gate exists to make refusal happen before the
  local move, and the rest of the walk cannot be known in advance.
