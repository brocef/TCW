# Add a way to rename a work item's slug

From GitHub issue [#70](https://github.com/brocef/TCW/issues/70) (filed
2026-09-29 by @brocef), preserved as this item's `intake.md`.

## The request

`tcw work edit --title` changes an item's title but not its slug, so the
folder name, branch name and every reference keep the old wording for the rest
of the item's life. Nothing renames a slug.

Real case: an item written about *removing* a participant was widened to cover
adding, removing and stepping down, and retitled to match. Its slug still says
removal only, and every command and cross-reference must use it.

Asked for: `tcw work rename <slug> <new-slug>` (or `edit --slug`) that moves
the folder, updates `blocked_by` and initiative references on the board, and
leaves a pointer from the old slug to the new one, as `tombstone` does for a
deletion. It would pair with the rename verb planned for capabilities and
taxonomy.

## Notes

- Written autonomously (an `/autonomous-work` run); there was no requester to
  ask. Reference material: the issue.
- Today a slug can be renamed by hand — rename the folder, update every
  reference — which is what the project guide describes for driving the work
  system manually; nothing in the CLI does it.

## References

- `2026-09-16-add-a-rename-verb-to-tcw-capabilities-and-tcw-taxonomy` — the
  same verb for the other two axes; the two should read alike.
