As a user, I write `[text](tcw://[<project-id>/]<axis>/<ref>)` to reference a
Taxonomy term, Capability, or Work item. Bare references remain local.
Namespaced work references resolve across the registered project graph;
taxonomy and capability namespaces resolve only to project IDs explicitly
listed by that axis's `extends`. A connection alone never grants inheritance.
`tcw validate` checks resolution. `tcw serve` turns hosted targets into in-app
navigation, marks a real work target outside the served board as off-board and
names its owning project, and shows an unresolved target inert with the reason.

A reference to work that has been completed or discarded still resolves. There
is nothing to open — the item's documents are no longer in the tree — so
`tcw serve` shows it inert and says it names finished work, alongside its
resolution where one was recorded. A reference to a slug the project never held
remains unresolved and reads exactly as it did before.
