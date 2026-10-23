As a user, I write `[text](tcw://<project>.<namespace>/<id-path>)` to
reference a taxonomy entry, capability or work item by its full identifier,
never shortened. A link may name an object in any project TCW can locate,
not only one named by `extends`. A folder is named by a folder address,
`tcw://<project>.path/<folder>` or `tcw://<project>.<namespace>.path/<folder>`.
`tcw validate` checks that every link resolves: an object that is not there
is an error, and a project that is named but not on this machine is reported
as could not be checked. A link in a TCW 3.x form (`tcw://C/…`, `tcw://W/…`,
`tcw://<project>/T/…`) is reported as needing tcw migrate, and is never
resolved. `tcw serve` turns a link to this project's objects, and to those it
inherits, into in-app navigation, shows a link to another project's object as
a labelled name that names its project, and shows an unresolved target inert
with the reason.

A work link names the item's folder, `tcw://<project>.work/<folder>`. An
item's folder never moves, whatever its stage, so a reference to finished
work — completed or discarded — resolves exactly as one to unfinished work
does. A reference to a folder the project does not hold is unresolved.

A qualified work reference into a read-only `upstream` project reads — `show`,
`path` and links resolve — and refuses to write: every command or web route
that would change the item says it is read-only here. See
[Read from an upstream project](tcw://C/cli/read-from-an-upstream-project).
