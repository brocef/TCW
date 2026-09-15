# Follow-ups the lifecycle synchronization review left

Found by the adversarial review of
`2026-09-12-synchronize-the-work-lifecycle-outward-to-the-tracker`. Each was judged
to need its own change rather than a fix on that branch.

## 1. Any staged sidecar write blocks a worktree item's merge-back

`tcw work complete` merges the item's work branch into the primary checkout
(`merge_worktree`, `tcw/store/fs.py`). The branch carries the item's folder, so a
staged but uncommitted file in that folder on the primary checkout makes git refuse
the merge ("would be overwritten by merge"). Sidecar writes are staged, never
committed: `tracker link`, `tracker unlink`, and now the synchronization record all
do it. The synchronization item added a hint naming the record when one exists;
`link` and `unlink` on a worktree item still produce only git's message.

Options: commit sidecar writes made to an item with a worktree, or check for staged
changes in the item's folder before merging and name them.

## 2. Two failed moves and a hand move read as drift

A `submit` whose delivery fails records `since: In Progress`. A `complete` that
also fails keeps that `since` and replaces the move. If someone then moves the
ticket by hand to `In Review`, `sync` accepts `since` (`In Progress`) or the recorded
move's target (`Done`), not `In Review`, and reports the ticket as moved in the
tracker. Accepting every mapped status between `since` and the target would close
it.
