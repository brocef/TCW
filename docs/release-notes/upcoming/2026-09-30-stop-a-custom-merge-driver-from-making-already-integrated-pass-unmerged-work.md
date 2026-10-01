## Fixes

- `tcw work complete --already-integrated` could mistake an unmerged branch for a
  merged one, and delete it, in a repository that sets its own merge rules for
  some files, including git's own "union" rule. It no longer lets those rules
  decide. In such a repository, a
  branch merged by squashing that changed one of those files may now be refused;
  delete the branch yourself and run the command again. If the item has its own
  worktree, remove that worktree first: git will not delete a branch a worktree
  is using. The refusal prints the command for it.
