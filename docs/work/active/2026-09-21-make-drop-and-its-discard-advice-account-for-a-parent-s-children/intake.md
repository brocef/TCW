# Make drop and its discard advice account for a parent's children

Found by the combined review of the v2.5.1 batch, where the drop-refusal fix
(2026-09-21-point-a-refused-drop-…) met children with their own status
(2026-09-21-let-a-child-created-under-an-already-active-parent-…):

1. A backlog parent with a `--parent` child: `tcw work drop <parent>` prints
   "Would delete …", and with `--confirm` is refused because a child names it.
   That is the two-step refusal the drop fix set out to remove. Refuse before the
   `--confirm` gate and name the children. When the children are all resolved,
   only re-parenting can help, so don't advise dropping or discarding them.
2. An active or review parent with an open child: drop advises
   `tcw work complete <slug> --resolution wontfix --confirm`, which is refused
   while the child is open. Name the open children in that advice.
3. `tcw work new --parent`'s help still says "create as a child nested under this
   item's slug". Children are now top-level items with a `parent:` field.

## Origin

Combined review of the v2.5.1 batch, 2026-09-21. Bug.
