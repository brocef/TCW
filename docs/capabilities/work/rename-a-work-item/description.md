As a user, I run `tcw work rename <slug> <new-words>` when an item's scope has
changed and its folder name no longer says what it is. I give the words after
the date (or, in a project that keeps its items in Jira, after the ticket key),
in lower case with hyphens, or the whole new name with the item's own date or
key in front; the item keeps its date or key, because that names it. A new name
that is not in that form, or that carries a different date or key, is refused
(exit 2), and one that another folder beside it already has is refused (exit 3).

The item's folder is renamed in place, and every item nested in its folder
moves with it. Every reference to a moved item in my project's records and
documents is rewritten to its new full identifier, and in a Jira project with the TCW
fields each moved ticket's `TCW Item` is set too. The command prints one `<old> -> <new>`
line per identifier it changed, the renamed item first, or `--json`. It lists,
on stderr as `file:line`, every place that still mentions an old identifier,
such as prose, and leaves it for me to edit. An item in another project that
names it is not changed: `tcw validate` there reports it.

If any item in my project cannot be read, the rename is refused and nothing
moves, because a reference that item holds could not be rewritten. The checks
come first and a refusal writes nothing; a rename that stops partway says what
it wrote, and running the same command again finishes it. TCW never commits
the rename; the change is mine to commit. To put the folder somewhere else
instead, I [move the item](tcw://C/work/move-a-work-item).
