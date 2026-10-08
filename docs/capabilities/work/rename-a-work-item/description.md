As a user, I run `tcw work rename <slug> <new-words>` when an item's scope has
changed and its folder name no longer says what it is. I give the words after
the date, in lower case with hyphens, or the whole new name with the item's own
date in front; the item keeps its original date, because that records when it
was made. A new name that is not in that form, or that carries a different
date, is refused (exit 2), and one that another item already has is refused
(exit 3).

The item's folder is renamed in place, and every other item in my project that
names it — as its parent or as a blocker — is rewritten to the new full slug.
The command prints the new slug. It lists, on stderr as `file:line`, every
line in the work store's documents — the item's own and every other item's —
that still mentions the old name, and leaves that prose for me to edit. An item in another project that names it is not changed.

If any item in my project cannot be read, the rename is refused and nothing
moves, because a reference that item holds could not be rewritten. TCW never
commits the rename; the change is mine to commit.
