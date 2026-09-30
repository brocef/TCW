# Detect a blocker cycle that runs across nodes

## What is being asked for

When two items in different nodes of a connected-project graph are made to wait
on each other — `A/x` blocked by `B/y`, and `B/y` blocked by `A/x` — the second
edit should be refused as a blocking cycle, exactly as it already is when both
items live in one node. Today it is accepted: the cycle check follows only
blockers stored as local slugs, and a blocker in another node is stored as
`external: <project-id>/<slug>`, which the check never follows. Both items then
block each other forever, and the only way to start either is `--force`.

The same holds for longer cycles that leave a node and come back, through any
number of nodes.

## Constraints

- The local half is already fixed: a reference qualified with the node's *own*
  project id is recorded as a local slug and meets the existing checks
  (2026-09-27-refuse-a-blocker-that-names-its-own-item-by-qualified-ref-and-settle-status-path-blockers).
- Nothing about how blockers are stored, displayed or settled changes; only the
  refusal of an edit that would close a cycle.

## Notes

- Written without the requester during an autonomous run (the user asked for
  all four open bug items to be done back to back); this is the intake's
  report restated, with no added scope.
- References: asked; none provided beyond the intake's code pointers.

## References

- `tcw/store/base.py` `_check_new_blocker`, `_reaches`, `check_blocker_edits` —
  the cycle checks that follow only `slug:` entries.
- `tcw/store/fs.py` `external_blocker_state`, `resolve_qualified_work_ref` —
  how a `<project-id>/<slug>` blocker is already resolved for settling.
- `2026-09-29-see-a-blocker-cycle-that-runs-through-an-item-whose-state-yaml-cannot-be-read`
  — the next item in this run, changing the same walk.
