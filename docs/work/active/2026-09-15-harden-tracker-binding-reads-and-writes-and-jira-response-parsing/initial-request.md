# Harden tracker binding reads and writes, and Jira response parsing

The tracker commands fail badly on input or state they do not expect:

1. A `tracker.yaml` that exists but is not a regular file (a folder) reads as
   "no binding" to `link`, `unlink`, `sync` and strict `drop`, while the board
   shows it as unreadable — so strict `drop` lets the item go.
2. A Jira response of an unexpected shape (a list where a mapping belongs, an
   entry that is not a mapping) raises `AttributeError`, not a tracker error, so
   the command prints a traceback instead of its pending or refused result.
3. Follow-ups from earlier reviews: `link` binds an item waiting for deletion;
   `ClaimOutcome.account_id`/`account_name` are dead; and when `complete`'s
   merge-back is refused by a staged file, the hint only ever names the item's
   own tracker record.

## Notes

- From the intake (Jira TCW-18), triaged 2026-09-15. Written during an
  unattended run (2026-09-26); no requester to ask. References: asked; none
  beyond the intake.
- The intake's named-pipe case no longer blocks: `read_sidecar` already skips
  anything that is not a regular file (that skip is what causes part 1).
- Kept as documented limits, as the intake allows: a binding on a finished,
  gitignored item is never committed; two finished items may hold one ticket.
