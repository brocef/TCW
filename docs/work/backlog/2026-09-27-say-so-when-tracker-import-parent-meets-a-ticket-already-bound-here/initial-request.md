# Say so when tracker import --parent meets a ticket already bound here

`tcw work tracker import <ticket> --parent <slug>` (and `--initiative`) is new in
the unreleased change
`2026-09-15-make-the-strict-tracker-gate-refuse-unfollowable-moves-and-allow-child-items`.
When the ticket is already bound to an item here and assigned to this account,
the command prints "already bound", exits 0, and ignores `--parent` and
`--initiative`: the item is not nested and nothing says so. A script, or a
person, reads that as success.

Fix this before the next bugfix release, so the new options never ship with a
case where they silently do nothing.

## Notes

- Requested by the user on 2026-09-27, after a review of the follow-ups from the
  autonomous bug run. This was point 2 of
  `2026-09-27-close-two-strict-mode-gaps-left-by-the-unfollowable-move-gate`,
  moved to its own item so that one can wait for a later release.
- The finding suggested pointing the user at `tcw work edit --parent`, but
  `tcw work edit` has no `--parent` option (`tcw/work/cli.py`, the `edit`
  parser); the spec must not send people to a command that does not exist.
- Out of scope: cutting the version, pushing; the other two strict-mode gaps.
- Reference material: asked; none provided beyond the original finding.

## References

- `tcw/work/cli.py` `_tracker_import` — the "already bound" branch.
- `2026-09-27-close-two-strict-mode-gaps-left-by-the-unfollowable-move-gate/intake.md`
  — where the finding was first recorded.
