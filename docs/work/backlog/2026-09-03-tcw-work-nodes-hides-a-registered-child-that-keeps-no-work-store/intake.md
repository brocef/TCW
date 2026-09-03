Found verifying the hierarchical Proposit workspace, 2026-09-03.

At the orchestration root, with every repository on disk:

    $ tcw work nodes
    node:   proposit-app
    parent: (none — root)
    children: (none — leaf)

`proposit-app-repo` is a registered child. It keeps no work store — it is the
monorepo's routing node, and the boards belong to the three packages under it —
so `child_nodes` filters it out and the topology reads as a leaf.

The parent half of exactly this was fixed while adding routing nodes: a
registered parent without a board prints `parent: <id> (no work store)` rather
than `(none — root)`. The children half was not, and the asymmetry is worse on
this side, because a node can have several children and the line says the node
has none at all.
