# Upcoming

User-facing release notes for the next version. Plain language — no jargon or
internal module names.

## Blockers you can actually remove

Clearing a blocker used to fail silently: you would run
`tcw work edit <item> --unblocked-by "…"`, see `edited <item>`, and find the
blocker still there. Three things were wrong, and all three are fixed.

- **Removing a blocker that isn't there is now an error.** The command tells you
  `no such blocker on <item>: <ref>` and stops, instead of reporting success.
- **You can copy the blocker straight off the board.** Items list their blockers
  as `external: waiting on vendor`, and that exact string is now accepted by
  `--blocked-by` and `--unblocked-by`. The bare text still works too.
- **Blocker text can contain commas.** `--blocked-by` and `--unblocked-by` are now
  repeatable — use the flag once per blocker instead of separating them with
  commas.

**If you use commas today, update your commands.** `--blocked-by "a,b"` used to
record two blockers; it now records a single blocker called `a,b`. Write
`--blocked-by a --blocked-by b` instead. (`--blocks` is unchanged.)

One more improvement: if you combine adding and removing blockers in one command
and the removal fails, nothing is applied at all — you no longer end up with a
half-finished edit.
