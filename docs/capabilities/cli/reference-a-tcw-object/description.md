As a user, I write `[text](tcw://[<project-id>/]<axis>/<ref>)` to reference a
Taxonomy term, Capability, or Work item. Bare references remain local.
Namespaced work references resolve across the registered project graph;
taxonomy and capability namespaces resolve only to project IDs explicitly
listed by that axis's `extends`. A connection alone never grants inheritance.
`tcw validate` checks resolution. `tcw serve` turns hosted targets into in-app
navigation, marks a real work target outside the served board as off-board and
names its owning project, and shows an unresolved target inert with the reason.
