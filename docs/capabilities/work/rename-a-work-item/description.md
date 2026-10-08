As a user, I run `tcw work rename <slug> <new-words>` when an item's scope has
changed and its folder name no longer says what it is. I give only the words
after the date, in lower case with hyphens; the item keeps its original date,
because that records when it was made. A new name that is not in that form, or
that carries a date, is refused (exit 2), and one that another item already has
is refused (exit 3).

The item's folder is renamed in place, and every other item in my project that
names it — as its parent or as a blocker — is rewritten to the new full slug.
The command prints the new slug. It lists, on stderr as `file:line`, the lines
in the item's own documents that still mention the old name, and leaves that
prose for me to edit. An item in another project that names it is not changed.

If any item in my project cannot be read, the rename is refused and nothing
moves, because a reference that item holds could not be rewritten. TCW never
commits the rename; the change is mine to commit.
