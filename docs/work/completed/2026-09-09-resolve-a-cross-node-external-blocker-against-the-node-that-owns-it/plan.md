# Plan: resolve a cross-node external blocker against the node that owns it

## Tasks

1. **Tests first** in `tests/test_cross_node_blockers.py`: criteria 1-5 with two
   registered nodes (and a routing layout from `tests/test_routing_nodes.py`).
2. **Store**: `external_blocker_state` on `WorkStore` (default) and
   `FsWorkStore`; `unresolved_blockers` uses it; `_entry_for` tombstones.
3. **Reconcile**: `_ready` through each row's store.
4. **Docs**: `skills/work/references/cross-node-deltas.md` (how to record a
   cross-node dependency: `--blocked-by <project-id>/<slug>`), `docs/guide/work.md`
   blockers, changelog, release notes.

## Verification

Hands-on: the request's repro with two nodes and the worktree's `tcw`.
