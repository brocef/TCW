# Plan: descend through a storeless routing node in delegate and reconcile

## Tasks

1. **Tests first** in `tests/test_routing_nodes.py`: criteria 1-4 with real
   registered nodes (see `tests/test_recursion.py`'s node helpers).
2. **`routed_children`** in `tcw/store/fs.py`.
3. **`delegate`** and **`_tasks_for`** in `tcw/work/recursion.py`, and the
   unreachable-target check.
4. **Docs**: `skills/work/references/cross-node-deltas.md` (delegate reaches the
   nearest board per branch; reconcile every descendant), `docs/guide/multi-repo.md`,
   the `delegate`/`reconcile` CLI help, changelog and release notes.

## Verification

Hands-on: the issue's graph built by hand; `delegate`, `reconcile` and `nodes`
from `root` with the worktree's `tcw`.
