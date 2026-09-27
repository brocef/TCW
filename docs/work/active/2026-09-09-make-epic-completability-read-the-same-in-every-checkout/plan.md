# Plan — Make epic completability read the same in every checkout

Starts after `2026-09-09-descend-through-a-storeless-routing-node-in-delegate-and-reconcile`
merges (it changes `reconcile`'s `_tasks_for`).

1. **Tests first** — `tests/test_epic_completability_across_checkouts.py`,
   criteria 1-9 (a folder removed by hand stands in for another clone).
2. **Record** — `tcw/store/fs.py`: write `initiative` in the tombstone record,
   carry it through the deletion rewrite and nested items; `Tombstone` gains
   `initiative` (base.py); keep the record in step on an `initiative` edit of a
   retained resolved item.
3. **Store operation** — `resolved_initiative_children` (base default, Fs
   override over this node and `descendant_nodes`); use it in
   `epic_children_all_resolved` and `check_type_change`.
4. **Graph note** — `relation` on `UnreachableProject` (base.py) set in
   `tcw/store/project.py`; registry method for unreachable entries below;
   `incomplete_graph_note(below=True)`; switch the three callers.
5. **Reconcile** — tombstone rows in `tcw/work/recursion.py`.
6. **Docs** — the `Tombstone` docstring (why the record grew), the epic
   section of `skills/work/references/epic-deltas.md` (legacy recovery),
   `docs/guide/work.md`, changelog, release notes; capabilities step.

Verification: the reproduction by hand in a scratch node and a clone of it.
