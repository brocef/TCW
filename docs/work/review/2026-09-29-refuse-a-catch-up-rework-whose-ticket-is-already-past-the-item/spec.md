# Spec — Refuse a catch-up rework whose ticket is already past the item

## Capability changes

- **changed:** the capability describing how lifecycle moves are carried to a
  bound ticket (found by grep for `catch-up`/`rework` under
  `docs/capabilities/work/`) — a move on a legacy `catch-up` binding is carried
  as on any other binding when its ticket is where the move expects it.

## Problem

`deliver` (`tcw/tracker/sync.py:351`) has a branch for bindings still carrying
`catch-up: true` (`sync.py:822-834`). Before walking the ticket up, it declines
— CONFLICTING, "…is in '<status>', which is past where its item is, so it was
not moved back" — whenever the ticket's rung (`lowest_rung`) is above
`_RUNG_ORDER` of the item's **new** status (`local`). That check is meant for
the forward catch-up walk ("a walk takes hops by the item's moves, and from
there the first one could only move it back"), but it runs for every move:

- **rework**: the item was in review; its ticket is in In Review, exactly in
  step; the item's new status is active (rung 0) and the ticket's rung is 1.
  The gate (`authorize`, `sync.py:1032-1117`) allows it — In Review is in the
  rework window (`_MOVED_FROM`, `sync.py:114`; `expected_statuses`) — the item
  moves, and delivery records a conflict. A binding without `catch-up` applies
  the rework transition instead (`assess_move`). Without strict mode there is
  no gate at all, and the same conflict is recorded. The record then refuses
  every later strict move (`binding_refusal`), and `sync` replays the rework
  into the same check, so it cannot be cleared.
- **start**: a catch-up binding on a backlog item whose ticket is already in
  In Review and held by this account. `_strict_claim` (`tcw/work/cli.py:524`)
  passes; the catch-up check fires before the forward-only HELD branch
  (`sync.py:866-875`) that a normal binding reaches, and records a conflict
  where a normal binding records nothing.

Every other gated move is safe: submit's window is rungs 0-1 and its
destination rung 1; complete and discard land on the top rung. (Worked out by
two advisors independently; the table test below pins it.)

## Goals

1. On a `catch-up` binding, a lifecycle move is carried exactly as it would be
   on the same binding without `catch-up` whenever the ticket is above the
   item's new rung: rework applies its transition and leaves no record; start
   is held with no record.
2. `sync` with no move and no window still declines to pull back a ticket that
   is past its item (`test_sync_status_does_not_pull_back_a_ticket_already_past_its_item`,
   `tests/test_tracker_sync.py`).
3. No gated move passes `authorize` or `_strict_claim` that `deliver` then
   records as a conflict from this branch — pinned by a table over every move
   and ticket status.
4. A conflict recorded by the old behavior clears on the next `sync`.

## Non-goals

- A new refusal in `authorize`: once goal 1 holds, nothing inside the gate's
  allowed statuses reaches the decline, so such a refusal could never fire.
- The forward walk itself, and `authorize`'s multi-rung refusal
  (`sync.py:1090-1103`), which is empty for a backward move.
- Writing `catch-up`: nothing does any more.

## Design

In `deliver`'s catch-up branch, decline only for a `sync` that brings no window
of its own (`syncing and not expected`), which is the case the decline is for.
Otherwise, a ticket above the item's rung skips the catch-up branch entirely —
not only the decline but the walk, which hops by `MOVE_ONTO` and would apply the
*start* transition for a rework — and continues to the path a binding without
`catch-up` takes: `assess_move` with the move's own window and configured
transition for rework, the forward-only HELD branch for a start. `catch-up` is
cleared as it already is once the delivery is CURRENT (`drop_note`,
`sync.py:501`; `with_status_synced`, `tcw/tracker/intake.py:348-351`).

The rule sits in one small function beside `needs_claim`,
`catch_up_declines(statuses, ticket_status, local, expected, syncing)`, which
`deliver` calls; its table test states the gate's allowed statuses for each move
and asserts it never declines inside them.

Litmus: tracker delivery is already an adapter concern; no store operation
changes.

## Acceptance criteria

With the fake Jira of `tests/tracker_fake.py` and the fixtures of
`tests/test_tracker_strict_gate.py` / `tests/test_tracker_sync.py`:

1. Strict mode, catch-up binding, item in review, ticket In Review and held:
   `tcw work rework` exits 0; the item is active; the ticket is In Progress by
   the configured rework transition (not the start transition); no conflict
   record; `catch-up` is gone from the binding.
2. The same without strict mode.
3. Strict and non-strict, catch-up binding, backlog item, ticket In Review and
   held: `tcw work start` exits 0; the item is active; the ticket is unchanged;
   no conflict record.
4. A conflict record written by the old behavior (catch-up binding, record
   `{move: rework, since: In Review}`, item active, ticket In Review): `sync`
   delivers the rework and clears the record.
5. Still refused / declined: a strict rework with the ticket in Done moves
   nothing; `sync` of a ticket past its item still does not pull it back (the
   existing test).
6. Table: for each gated move and every status in the gate's allowed set,
   `catch_up_declines` answers no.
7. Existing tracker tests pass unchanged; the full suite passes as CI runs it.

## Risks

- **A `sync` replay can now move a legacy binding's ticket back** *(added at
  verify)*. A `sync` replaying a recorded move other than a start — say a
  `submit` recorded while the item was in review, the item since back in
  active, the ticket in review — used to be declined on a `catch-up` binding.
  It now takes the plain binding's path: the ticket is put back to the item's
  status and the output says so ("was in … and was put back to …"). Intended
  (the same as any other binding) and rare: it needs a recorded move out of
  step with the item.
- **Moving a ticket someone advanced on purpose.** Only statuses inside the
  move's window reach the transition; a ticket beyond it is refused by
  `assess_move` and, under strict mode, by the gate first.
- **Rare case.** Only legacy bindings reach this; the change is small.

## Notes

- Designed with two advisors (Opus; Sonnet in place of Codex, at its usage
  limit). Both: fix `deliver` (option B), add no gate refusal. Split on scope:
  Sonnet limited the fix to backward moves in the window; Opus generalised it
  and found the start mismatch. Taken: Opus's rule — checked against the code
  order in `deliver` (the catch-up branch returns before the HELD branch).
