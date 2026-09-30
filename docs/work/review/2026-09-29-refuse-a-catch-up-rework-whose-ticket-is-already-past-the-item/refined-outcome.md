# Refined outcome

**Verify decision: accept.** Decided autonomously (the `/autonomous-work` run).

## Evidence

- `tcw:verifier` found all seven acceptance criteria met. It ran the item's 21
  tests and 365 surrounding tracker tests. It closed one gap with a probe: the
  fixtures configure no rework transition, so the rework test proves only that
  the start transition was not used. With a second route and
  `transitions.rework` configured, the rework applied the configured one.
- The full suite at 7e0e8356 (5005 passed, 3 skipped) describes this code; the
  only later commits touch the item's own folder.
- The review fix (a replayed start, held) was probed against the cases where
  it could hide a real conflict. Each still conflicts:
  - a ticket in an unmapped status;
  - a ticket held by someone else, or by nobody, which the claim branch stops
    first;
  - a resolved ticket;
  - a binding without `catch-up`, which never reaches the branch.

## Noted at verify

- `test_no_gated_move_is_declined_inside_its_window` cannot fail as written:
  with `syncing=False`, `catch_up_declines` is always false. What it still
  pins is that a lifecycle move is never declined. The replay table added
  after review, `test_a_replayed_move_other_than_start_brings_a_window`, is
  the one that tests windows.
- A `sync` replaying a recorded non-start move out of step with the item can
  now move a legacy binding's ticket back, as on any binding, and says so.
  This was intended but not written down; it is now added to the spec's Risks.
- The plan's by-hand CLI rework was replaced by the tests, which drive the
  real commands against a fake tracker. That was disclosed in `outcome.md`
  but not listed there as a deviation.

## Follow-up filed

- A plain binding (no `catch-up`) with a recorded start whose ticket has
  since moved on still ends in a conflict on every `sync`. It is the same
  stuck record this item fixed for legacy bindings, and it existed before.
  Filed to the inbox.

No GitHub issue originated this item, so there is nothing to answer or close.
