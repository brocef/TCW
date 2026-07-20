As a user, I write `[text](tcw://[<project-id>/]<axis>/<ref>)` to reference a
Taxonomy term, Capability, or Work item. Bare references remain local.
Namespaced work references resolve only to registered descendants; taxonomy and
capability namespaces resolve only to project IDs explicitly listed by that
axis's `extends`. A connection alone never grants inheritance. `tcw validate`
checks resolution and `tcw serve` turns hosted targets into in-app navigation.
