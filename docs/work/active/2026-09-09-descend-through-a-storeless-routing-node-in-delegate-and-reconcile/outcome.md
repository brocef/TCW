# Outcome — Descend through a storeless routing node in delegate and reconcile

## What changed

- `tcw/store/fs.py`: `routed_children(root)` (the nearest node with a board on
  each branch) and `routed_unreachable_children(root)` (declared children found
  absent on the way down), both from one walk, `_routed`, over the root's own
  registry.
- `tcw/work/recursion.py`: `delegate` targets `routed_children` and reports a
  declared-but-absent target behind a routing node as absent, not unknown.
  `_tasks_for` (the `reconcile` table) reads `[node, *descendant_nodes(node)]`,
  the same set `initiative_children` and the completion gate read.
- `tcw work nodes` is unchanged: it prints the direct topology.
- Docs: `skills/work/references/cross-node-deltas.md`, `docs/guide/multi-repo.md`,
  the `delegate`/`reconcile` help, the `reconcile` docstring, the README command
  table, the changelog and release notes.
- Tests: `tests/test_routing_nodes.py` (7). Criteria 1–3 fail on the old code;
  the worktree test fails on the first version of the walk.

## Verification

- Full suite on 3cbe1b1f: see the verify notes below.
- By hand, the issue's graph (root → mid with no board → pa, pb): `nodes` shows
  `mid (no work store)`; `delegate pa` writes into `mid/pa`'s inbox; `reconcile`
  lists both slices and names them under Next.

## Autonomous decisions

- **Reconcile scope** — the table reads every descendant with a board, not just
  the nearest level. Codex: fix the code; `initiative_children` and the
  completion gate already read all descendants, so a narrower table can show
  fewer slices than the gate counts. Opus agreed. Taken.
- **Delegate scope** — nearest board per branch, the downward mirror of
  `nearest_work_ancestor`; a node with a board is the target, not passed
  through. Both advisors agreed. Taken.
- **Review finding 1 (blocking, accepted)** — reopening a registry at each
  routing node broke `delegate` from a linked worktree, even to a direct child.
  Fixed with one registry opened at the root; regression test added and
  mutation-checked.
- **Review, accepted**: stale `reconcile` help and docstring; README rows;
  tighter assertion in the stacked test.
- **Review, deferred to follow-ups** (not this change): one shared walk for
  `_tasks_for` and `initiative_children`; a clearer refusal when `delegate`
  names a routing node or a node whose board is not provisioned (the message
  predates this change). Slug-only matching in `_ready` belongs to
  `2026-09-09-resolve-a-cross-node-external-blocker-against-the-node-that-owns-it`,
  whose plan already rewrites `_ready`.
- **Rejected**: none.
