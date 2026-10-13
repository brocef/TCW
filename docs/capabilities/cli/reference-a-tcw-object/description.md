As a user, I write `[text](tcw://[<project-id>/]<axis>/<ref>)` to reference a
Taxonomy term, Capability, or Work item. Bare references remain local.
Namespaced work references resolve across the declared connected projects;
taxonomy and capability namespaces resolve only to project IDs explicitly
listed by that axis's `extends`. A connection alone never grants inheritance.
`tcw validate` checks that every link resolves. `tcw serve` turns hosted targets into in-app
navigation, marks a real work target outside the served board as off-board and
names its owning project, and shows an unresolved target inert with the reason.

A work reference names the item's folder, `tcw://W/<folder>`. An item's folder
never moves, whatever its stage, so a reference to finished work — completed or
discarded — resolves exactly as one to unfinished work does. A reference to a
folder the project does not hold is unresolved.

A qualified work reference into a read-only `upstream` project reads — `show`,
`path`, links and `tcw serve`'s item view resolve — and refuses to write: every
command or web route that would change the item says it is read-only here. See
[Read from an upstream project](tcw://C/cli/read-from-an-upstream-project).
