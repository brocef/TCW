## Choose which projects a command covers

Every list and show command, `tcw work list|show`, `tcw taxonomy
list|show|search` and `tcw capabilities list|show|search`, takes
`--scope own|up|down|all`. `own`, the default, is the project alone; `up` adds
the projects above it; `down` the projects below it; `all` both. A sibling, a
project that only shares a parent, is never included. `--project <id>` keeps
one of those projects' own results.

`tcw taxonomy list` and `tcw capabilities list` now list only the project's own
entries by default; `--scope up` adds the ones it inherits, as these commands
listed before. `show` of an inherited entry by its path alone needs
`--scope up`, and says so. `list --local` is removed: it stops with a message,
since the default already does what it did.

## A project that is not here is named, not skipped

When a project the scope covers is not on this machine, or cannot be read, the
command still succeeds, and a warning names that project, says what was left
out, and gives the command that fetches it. With `--json`, the document's
`projects` lists every project covered and why any could not be read.

## Each project's status for a capability

Under `--scope down` or `all`, each capability is listed once, with the status
each project gives it: in the JSON as `statuses`, and in
`tcw capabilities show` as a `status by project:` block. Every override of an
entry or capability in those projects is named as `overridden-by`.

## Work across a project's family

`tcw work list --scope down` shows the projects below this one, each with its
own items. An epic's parts filed in other projects show as its children, and
`--parent` finds them. `tcw work show` finds an item by its folder name or
ticket key in any project the scope covers. Projects that keep their items in
one Jira project, and sign in as the same account, are read with one search.
The backlog audit (`tcw work procedure audit-backlog`) covers the projects
below this one, names each item by its full identifier, and reports a project
it could not read as not audited.

## The web app

The web app has a scope control and a project filter in its header, matching
`--scope` and `--project`, kept in the page's address so a link reproduces the
view. It is shown only for a project that has parents or children. Another
project's objects are shown read-only, marked with whose they are, and
another project's work item names the command that moves it in its own
project (`tcw -C tcw://<owner>.path/ work advance …`); links to
them are followed; a project that could not be read is named above the list;
and each capability row shows how many projects give each status.
