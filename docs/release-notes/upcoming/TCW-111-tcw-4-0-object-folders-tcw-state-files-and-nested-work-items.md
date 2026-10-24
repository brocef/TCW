## Object folders and state files

Each kind of record now has its own named file, and that file is what makes a
folder a record: `tcw-taxonomy.yaml` for a taxonomy entry,
`tcw-capability.yaml` for a capability, and `tcw-work-item.yaml` for a work
item. Each starts with `tcw-version`, so a file written by a newer TCW is
reported rather than misread.

A record's folder holds its own files, the folders of the records below it,
and one `resources/` folder for anything else: diagrams, notes, sample files.
A term's attachments are the files in its `resources/` folder, and a
capability's extra documents are named there too. `tcw validate` reports a
file or folder that does not belong, and a folder whose name is reserved, such
as `resources`.

A folder with no state file can group records in any of the three stores. It
is never listed as a record itself, but its name is part of the name of every
record inside it, so `2026/2026-10-01-add-login` is a work item in a `2026`
folder.

## Nested work items

`tcw work new 'Part' --parent 2026-10-01-epic --nest` makes the new item's
folder inside its parent's folder, in either backend, so the folders read the
way the items relate. Without `--nest` a child is made at the top, as before.
The web app's new item form has the same choice, unticked by default. Work
items are found, listed, shown, edited, moved and renamed wherever their folder
sits.

## Parents for terms and capabilities

A term or a capability may name its parent: `tcw taxonomy add --parent` writes
it, and `tcw capabilities add` and `set` take `--parent`. Records and `show`
include it. `tcw validate` reports a parent that names nothing, the record
itself, or a loop, and warns where a record sits in another record's folder
that its parent does not name; the parent is what counts.

## Names stay within 255 characters

No name, project and path together, is longer than 255 characters. A new item's
title words are shortened to fit under a deeply nested parent, and a command
that would need a longer name is refused before it writes anything.

## TCW 3.x files

A folder still holding a TCW 3.x `meta.yaml` or `item.yaml` is not read as a
record. `tcw validate` names each one and says to run `tcw migrate`, and
removing a record with such a folder below it is refused until then.
