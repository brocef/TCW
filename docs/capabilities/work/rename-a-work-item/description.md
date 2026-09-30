As a user, I run `tcw work rename <slug> <new-slug>` when an item's scope has
changed and its slug no longer says what it is. I give the new slug in full,
or only the part after the date; the item keeps its original date, because
that records when it was made. The new slug must already be in slug form and
not taken by another item, a resolved item's record, or an earlier rename.

The item's folder moves in place, and everything on my board that names it
follows in the same commit: other items' blockers, a child's parent and
initiative, a resolved child's record, and a capability's `Planning doc:`.
For an epic, its initiative children on other boards follow too, committed
in their own repositories. The old slug is recorded in `renames.yaml`, so it
keeps working where I could not rewrite it: `tcw work show` and `tcw work path`
follow it and say so, a blocker naming it — even from another project — reads
the renamed item's real status, and no new item is ever given it. A command
that changes an item refuses the old slug and names the new one.

Only an open item is renamed, and only by its holder. An item with a worktree
or branch is refused, with the manual steps, and so is a resolved one. The
command lists files in the item that still mention the old slug in their
prose, and says when a tracker ticket was written naming it; it rewrites
neither.
