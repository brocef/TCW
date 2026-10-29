As a user, I run `tcw work move <item> --into <id-path>` to put an item's
folder inside another item's folder or an organising folder, or
`tcw work move <item> --top` to put it at the top of the work store. Every
item nested in its folder moves with it, and every reference to a moved item
in this project's records and documents is rewritten to its new full
identifier; in a project that keeps its items in Jira with the TCW fields, each
moved ticket's `TCW Item` is set as well. The command prints one `<old> -> <new>` line per
identifier it changed, the item first, or `--json`.

A destination that does not exist is made as organising folders. A
destination inside the item itself, inside a stage folder or `resources/`, or
one that already holds a folder of that name, is refused before anything is
written. Moving an item into a folder that is not its parent's warns that the
`parent:` value, not the folder, decides what it is part of.

A move checks everything first and writes nothing when it refuses. If it stops
partway, it says what it wrote and where the folder is, and running the same
command again finishes it; nothing it wrote is set back. It lists, on stderr,
the places it did not rewrite, such as prose that mentions an old identifier.
References in other projects are not rewritten: `tcw validate` there reports
them. TCW never commits the move.
