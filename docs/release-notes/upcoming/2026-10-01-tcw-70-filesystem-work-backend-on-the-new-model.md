## Work items, rebuilt

The `tcw work` commands now run on TCW 3.0's simpler work model. This is part
of the 3.0 release; the migration guide that comes with it explains how to
move a project across.

- **An item is a folder that never moves.** Its stage is written in its
  `item.yaml`, so a link or a path to an item keeps working for the item's
  whole life, finished or not.
- **One command moves an item: `tcw work advance`.** It moves the item to its
  next stage, runs that stage's checks first and refuses the move if one
  fails, and `--dry-run` tells you what would happen without moving
  anything. Skipping a stage or overriding a failed check needs `--force` and
  a reason, which is kept with the item.
- **Comments.** `tcw work comment` records a dated remark on an item. Forced
  moves and discards leave their reason as one.
- **`tcw work discard --reason`** closes an item that will not ship.
- **`tcw work rename`** renames an item's folder and updates every other item
  in the project that names it.
- **File work in another project** with `tcw work new --project <id>`. It
  lands in that project's inbox, and the files are left for its owners to
  commit.
- **The inbox is a stage.** `tcw work new --stage inbox` files a raw request,
  and `tcw work list --stage inbox` lists them.
- **TCW no longer commits, pulls or pushes your work items.** Every change is
  left in your working tree for you to commit, as with any other file.
- **Priority** is now a named level, from `lowest` to `highest`.

Removed, with the 2.x work store: `start`, `submit`, `rework` and `complete`
(use `advance`), `drop` and `delete` (TCW never deletes an item), `inbox`,
`tracker`, `tombstone`, `reconcile`, `delegate`, `escalate`, `scaffold`, and
`stage gate` and `stage validate` (use `advance --dry-run`). The
configuration keys `work.lifecycle`, `work.tracker`, `work.retain`,
`work.auto-commit-transitions`, `work.publish-transitions` and
`work.trunk-branch` are now refused with a message naming the migration
guide. Jira support comes back, rebuilt, later in 3.0.

`tcw serve` does not show work items for now; its work view is being rebuilt
on the new model.
