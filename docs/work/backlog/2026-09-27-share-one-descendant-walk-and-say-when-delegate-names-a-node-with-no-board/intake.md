# Share one descendant walk, and say when delegate names a node with no board

Left by the review of
`2026-09-09-descend-through-a-storeless-routing-node-in-delegate-and-reconcile`
(2026-09-27), outside that item's scope.

1. **Two copies of one walk.** `_tasks_for` (`tcw/work/recursion.py`, the
   `reconcile` table) and `FsWorkStore.initiative_children` (`tcw/store/fs.py`,
   the completion gate) both read `[node, *descendant_nodes(node)]` filtered by
   `initiative == epic`. The routing-node bug came from these two drifting
   apart; nothing now keeps them together except a docstring. One helper
   yielding `(node_path, item)` would let each keep its own shape.
2. **`delegate` aimed at a node with no board** says "no child node 'mid'.
   children: pa, pb" even when `mid` is a registered child — a routing node, or
   one whose board is declared but not provisioned. It should say the node keeps
   no board and name the nodes that do. The message predates the routing change.
