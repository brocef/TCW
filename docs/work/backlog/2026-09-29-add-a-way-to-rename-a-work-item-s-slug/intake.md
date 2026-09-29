# Add a way to rename a work item's slug

## Origin

GitHub issue [#70](https://github.com/brocef/TCW/issues/70), filed 2026-09-29 by @brocef.

> `tcw work edit --title` changes an item's title, but the slug, and with it the folder name and every reference, keeps the old wording. The help says so ("the slug is unchanged"), and no other command renames it.
>
> **Real case:** an item was first written about *removing* a participant. It was then widened to cover adding, removing and stepping down, and retitled to match. Its slug still says removal only, and every command, branch name and cross-reference has to use that misleading slug for the rest of the item's life.
>
> **Asked for:** a `tcw work rename <slug> <new-slug>` (or `edit --slug`) that moves the folder, updates `blocked_by` and initiative references on the board, and leaves a pointer from the old slug to the new one, the way `tombstone` does for deletions. It would pair with the backlog item `add-a-rename-verb-to-tcw-capabilities-and-tcw-taxonomy`.

## Triage notes

Related backlog item: `2026-09-16-add-a-rename-verb-to-tcw-capabilities-and-tcw-taxonomy`.
