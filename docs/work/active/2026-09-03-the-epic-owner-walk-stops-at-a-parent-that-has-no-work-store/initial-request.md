# The epic owner walk stops at a parent that has no work store

A node that carries no work store of its own should be transparent to the
relations that cross it, not a wall. Today it ends every upward walk, silently.

The request came out of designing a repository-root node for the `proposit-app`
monorepo. The three package nodes there have no edge to each other — each
declares only its parent in another repository — so a checkout that cloned only
the code has no route between siblings sitting in the same tree. The fix on the
consumer side is a node at the repository root whose children are the three
packages. That node holds no board: the work stores stay exactly where they are.

TCW does not tolerate such a node. `parent_node` answers `None` for a parent
without a work store, and the walks built on it stop there — so an item whose
initiative epic lives two levels up is treated as having no epic at all.

What should be true when this is done:

- An intermediate node with no work store does not break a relation that passes
  through it. The walks find the nearest ancestor that *has* a store.
- Nothing silently returns a smaller answer. Where a relation genuinely cannot
  be resolved, it is reported.
- A node with no work store is not described as the root of the graph.

Out of scope: the consumer-side configuration in `proposit-app` that motivated
this. This item is about TCW tolerating the shape, not about adopting it.

## Notes

Asked for reference material; none provided beyond the session itself.

This is not a cloud-only defect and it should not be filed as one. The walk stops
at a work-less ancestor on any machine, and an epic rollup that quietly stops
listing its slices is the visible symptom.
