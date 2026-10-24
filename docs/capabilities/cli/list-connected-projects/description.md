As a user, I run `tcw project list` to see which projects the current project
is connected to. It prints one project ID per line: this project first, then its
parents in the order it lists them, then its children, each once. Projects are
named by ID, never by folder, because the ID is a project's identity and a
folder is only where it happens to sit on one machine.

Only _declared_ projects appear. TCW reads `parents:` and `children:` in
`.tcw/tcw-config.yaml`, and the children listed in my personal
`.tcw/tcw-config.local.yaml`, so a git repository sitting next to or inside
this one is not connected until it is declared — being nearby is not a
relationship, and listing a project in a manifest does not connect it either.
A declared project that is not on this machine is still listed, so a project
with children never reads as one without any.

`tcw project list --json` prints `{"schema": 2, "projects": [...],
"load-order": [...], "load-order-complete": ..., "load-order-warning": ...}`.
Each project has its ID, its relation to this one (`current`, `parent` or
`child`), whether it is present on this machine, its folder when it is, and
`found`, which says how TCW found it: `{"by": "manifest", "file": <the
manifest>}`, `{"by": "variable", "name": "TCW_PROJECT_<ID>"}` or
`{"by": "search"}` (see [Find a project's folder from its
ID](tcw://C/cli/find-a-projects-folder-from-its-id)); it is `null` for this
project and for one not on this machine. A parent adds `inherit`, the axes it
passes down (`[]` when it passes none); a child adds `personal`, true when only
my personal file lists it. `load-order` is the order this project's ancestors are read in (see
[Read a project's ancestors in one load
order](tcw://C/cli/read-ancestors-in-one-load-order)), `load-order-complete` is
false when one of them is not on this machine or its parents could not be read,
and `load-order-warning` is the warning given when no order keeps every
project's own order of parents, or `null`.

That makes it the command to run first when something in another project is not
behaving: the projects listed here as present are the ones
full identifiers and `tcw -C` can reach. If a project I expected is missing, the
problem is its declaration or its manifest entry, not the command I was trying
to run.
