## One name for every object

Every taxonomy entry, capability and work item now has one name, its full
identifier: `<project>.<namespace>/<id-path>`. It says which project owns the
object, which of the three namespaces holds it, and where it sits in that
store:

    demo.taxonomy/invoice
    demo.capabilities/cli/export-a-report
    demo.work/2026-10-22-add-login

Every command prints it: lists print one per line, and `show` starts with the
full identifier and the owning project. Every command that takes an object
accepts its full identifier, its `tcw://` address, or, for an object of the
project you are in, its id-path alone (`cli/export-a-report`). A work item can
also be named by its tracker key, bare (`TCW-67`) or as `<project>.work/<KEY>`.
Letter case counts: a name that differs only in case is not found, and the
message gives the spelling on disk.

A full identifier may name an object in any project TCW can locate, not only
one this project inherits from. Naming a project is not inheriting from it: an
object in a project you do not inherit from can be read but not changed here.

## Links

A link is the full identifier after `tcw://`, never shortened:

    [the export](tcw://demo.capabilities/cli/export-a-report)

A folder is named by a folder address, `tcw://<project>.path/<folder>` for a
folder in that project's root, or `tcw://<project>.<namespace>.path/<folder>`
for one inside its store. `tcw validate` checks every link; a link to a project
that is named but not on this machine is reported as could not be checked.

## JSON output

Every `--json` document now says `"schema": 2`. Records carry `full-id` and
`owner` in place of `slug`, `qualified`, `path` and `origin`.

## Store locations

A `<component>.path` in `.tcw/tcw-config.yaml` is a path relative to the
project or a folder address, which follows the named project wherever its
checkout is:

    work:
      path: tcw://workspace.path/docs/app/work

An absolute path or one starting with `~` is refused in the shared file; a
folder that sits elsewhere on one machine is placed by an entry in
`.tcw/tcw-manifest.local.yaml`. `tcw validate` fails two stores that are the
same folder or one inside the other, in this project or across the projects it
can locate, and a store location that loops.

## TCW 3.x names

Names, links and stored references in their TCW 3.x form (`tcw://C/cli/x`,
`tcw://core/W/<folder>`, `<project>/<folder>`, a reference stored as a bare
path) are no longer read. They are reported as needing `tcw migrate`, which
converts a project. In a project that keeps its items in Jira, a ticket whose
TCW Item field still holds a 3.x value is left out of `tcw work list`, and one
warning says how many were and names `tcw migrate`.
