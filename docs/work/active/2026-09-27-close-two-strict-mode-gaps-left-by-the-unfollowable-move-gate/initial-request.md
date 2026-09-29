# Close two strict-mode gaps left by the unfollowable-move gate

Two ways strict mode still lets a local move through that `deliver` then cannot
carry to the ticket — leaving the item moved, the ticket behind, and a
`conflicting` record — on a legacy binding carrying `catch-up: true`:

1. `complete` with the ticket held by someone else passes the gate (a completion
   is not asked who holds the ticket), but `deliver` treats a catch-up
   completion as needing the ticket held, and records a conflict ("held by Bob").
2. A catch-up walk of more than one rung is not checked by the gate at all; on a
   workflow broken part-way (no way out of In Review), `complete` exits 1 after
   the item is already completed.

Wanted: the gate refuses both before anything moves.

## Notes

- Unattended run (2026-09-29); from `intake.md`, left by the review and verify
  of `2026-09-15-make-the-strict-tracker-gate-refuse-unfollowable-moves-and-allow-child-items`.
  Reference material: asked; none beyond the intake's.
- The intake's third gap moved on 2026-09-27 to its own item and is out of scope.

## References

- `intake.md` in this folder.
