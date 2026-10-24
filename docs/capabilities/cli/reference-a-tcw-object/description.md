As a user, I write `[text](tcw://<project>.<namespace>/<id-path>)` to
reference a taxonomy entry, capability or work item by its full identifier,
never shortened. A link may name an object in any project TCW can locate,
not only one this project inherits from. A folder is named by a folder address,
`tcw://<project>.path/<folder>` or `tcw://<project>.<namespace>.path/<folder>`.
A full identifier names its owner's own object as its owner sees it, combined
with what the owner inherits, so a link to `core.capabilities/cli/x` reaches
`core`'s capability, never a project's override of it; an object a project only
inherits is not found under that project's identifier.
`tcw validate` checks that every link resolves: an object that is not there
is an error, and a project that is named but not on this machine is reported
as could not be checked. A link in a TCW 3.x form (`tcw://C/…`, `tcw://W/…`,
`tcw://<project>/T/…`) is reported as needing tcw migrate, and is never
resolved. `tcw serve` turns a link to this project's objects, and to those it
inherits, into in-app navigation, shows a link to another project's object as
a labelled name that names its project, and shows an unresolved target inert
with the reason.

A work link names the item's folder, `tcw://<project>.work/<folder>`. An
item's folder does not move with its stage, so a reference to finished work —
completed or discarded — resolves exactly as one to unfinished work does. A
reference to a folder the project does not hold is unresolved. When I move or
rename an object, its project's own links to every identifier that changed are
rewritten; links in other projects are left, and `tcw validate` there reports
them.

A reference into another project reads: `show`, `path` and links resolve.
Changing the object it names is refused from here, whatever the projects'
relation, and the refusal names the folder to run the command in
([Change objects only in the project that owns them](tcw://C/cli/change-objects-only-in-the-project-that-owns-them)).
