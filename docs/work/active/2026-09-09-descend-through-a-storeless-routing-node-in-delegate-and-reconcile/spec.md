# Spec: descend through a storeless routing node in delegate and reconcile

## Capability changes

None to the ledger: `delegate` and `reconcile` reach what the documentation says
they reach.

## Problem

`delegate` (`tcw/work/recursion.py`) and `reconcile`'s `_tasks_for` build from
`child_nodes` (`tcw/store/fs.py`): direct children that keep a board. A child
without one is dropped, not passed through, so nodes behind it are unreachable.
Meanwhile `initiative_children` — which the completion gate and
`--complete-when-ready` use — already walks every descendant with a board, so
`reconcile`'s table can omit slices the gate counts.

## Goals

1. `routed_children(root)` in `tcw/store/fs.py`: for each registered child, the
   child if it has a usable work store, otherwise its own routed children — the
   nearest board on each branch, the downward mirror of `nearest_work_ancestor`.
   A declared but unprovisioned store counts as no board, as it does going up.
2. `delegate` resolves its target among `routed_children`; its error lists them;
   a target declared below a routing node but not present in this checkout is
   reported as such, not "no child node".
3. `_tasks_for` rolls up from `[node_root, *descendant_nodes(node_root)]`, the
   same set `initiative_children` uses, including below a child with a board.
4. `child_nodes` is unchanged for `tcw work nodes`, which prints the direct
   topology.

## Acceptance criteria

1. `root → mid (no board) → a, b, c`: `delegate a …` from `root` writes into
   `a`'s inbox; `reconcile <epic>` lists slices on `a`, `b` and `c`.
2. `root → x (board) → y (board)` with a slice of `root`'s epic on `y`:
   `reconcile` lists it; `delegate y` from `root` is refused naming `x` as the
   target (nearest board).
3. A declared target behind a routing node that is not in this checkout: the
   refusal says it is declared but not reachable here.
4. `tcw work nodes` output unchanged.
5. Full suite passes.

## Notes

- Advisors (2026-09-27), in agreement: fix the code, not the docs; nearest board
  per branch for `delegate`, every descendant for `reconcile` (as the gate
  already does); extend delegate's unreachable check; keep `child_nodes` for the
  topology view. Codex: the blocked cross-node-blocker item should resolve
  blockers against their owning node regardless of this roll-up scope.
- GitHub #30 closes only after publication.
