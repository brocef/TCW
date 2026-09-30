## Fixes

- Completing an item worked in a worktree no longer throws away commits you made
  there while not on a branch (a "detached" checkout). Before, those commits were
  silently lost when the worktree was removed. Now `tcw work complete` stops
  before changing anything, names the commits, and tells you how to keep them on
  a branch. Discarding such an item still works, but leaves the worktree in place
  for you to save them.
