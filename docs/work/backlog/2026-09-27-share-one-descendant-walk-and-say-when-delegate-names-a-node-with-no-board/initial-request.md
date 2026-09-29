# Share one descendant walk, and say when delegate names a node with no board

1. **Two copies of one walk.** `_tasks_for` (`tcw/work/recursion.py`, the
   `reconcile` table) and `FsWorkStore.initiative_children` (`tcw/store/fs.py`,
   the completion gate) each read "this node and every descendant with a board,
   filtered by `initiative == epic`". The routing-node bug came from these two
   drifting apart; only a docstring keeps them together now.
2. **`delegate` aimed at a registered node with no board** — a routing node, or
   one whose board is declared but not provisioned — says "no child node 'mid'.
   children: pa, pb", as if `mid` were not registered.

Wanted: one helper both callers use, and a `delegate` refusal that says the node
keeps no board (or that its board is not provisioned) and names the nodes that do.

## Notes

- Unattended run (2026-09-29); from `intake.md`, left by the review of
  `2026-09-09-descend-through-a-storeless-routing-node-in-delegate-and-reconcile`.
  Reference material: asked; none beyond the intake's.
- Reproduced 2026-09-29 with `tests/test_routing_nodes.py`'s `node` helper:
  root → mid (no board) → pa, pb; `delegate(root, "mid", …)` raised
  "no child node 'mid'. children: pa, pb".

## References

- `intake.md` in this folder.
