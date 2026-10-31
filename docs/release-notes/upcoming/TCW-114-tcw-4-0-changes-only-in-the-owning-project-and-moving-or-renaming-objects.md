## Only the owning project changes an object

Only the project that owns a record can change it. A command run in one project
that would change another project's work item, term or capability stops (exit
3), changes nothing, and says which folder to run it in, or that the owning
project is not on this machine. The rule is the same whatever the projects'
relation. Referring to another project's object, as a parent, a blocker or a
link, is still allowed, and so is overriding an inherited capability.

## Run any command as another project

`tcw -C <folder> <command>`, or `tcw -C tcw://<id>.path/ <command>`, runs any
command as if it had been started in that folder, as that project, with its
settings, checks and hooks. `-C` may be given more than once.

## Filing into another project is replaced

`tcw work new --project` and `tcw work edit --blocks` are removed; each now
stops with a message naming what to do instead. Create a part in its own
project with `tcw -C tcw://<id>.path/ work new "<title>" --parent <epic>`, and
record a blocker on the blocked item with `--blocked-by`. The web app's
project choice on the create form and its "Blocks (add)" section are gone.

## Moving and renaming

New: `tcw work move <item> --into <folder>` or `--top`,
`tcw taxonomy rename|move` and `tcw capabilities rename|move`. `tcw work rename`
now works on an item with items inside it. A move or rename carries everything
nested in the folder with it, updates every reference in this project, prints
one `<old> -> <new>` line per identifier it changed, and lists the places it
could not update. It checks everything before writing, and if it stops partway
it says what it did and that running the same command again finishes it.
References in other projects are not changed: `tcw validate` there reports
them.

## Parents and blockers Jira cannot link

In a Jira project, a parent or blocker that Jira cannot link (an item kept in
files, or a ticket on another Jira site) is now kept in the item's folder
rather than refused, and TCW says Jira will not show it. `tcw validate` checks
those values without reading Jira.
