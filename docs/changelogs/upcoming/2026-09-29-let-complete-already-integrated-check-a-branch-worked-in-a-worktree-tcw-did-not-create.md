## Fixed

- `tcw work complete --already-integrated` checked nothing. It skipped the
  merge-back on the caller's word, and the teardown then ran
  `git branch -D`, so a branch that was never merged was force-deleted with
  its work. It now checks, before anything changes, that the branch reached
  the node repository's `HEAD`: either its tip is an ancestor
  (`git merge-base --is-ancestor`), or `git merge-tree --write-tree` gives
  `HEAD`'s own tree, which is how a squash or rebase merge looks. Otherwise it
  refuses, naming the branch and the commit. It also refuses when `HEAD` is the
  branch itself. A recorded branch that is already gone still passes. New
  helpers `branch_integration` and `branch_exists` in `tcw/store/fs.py`.

## Added

- `tcw work complete --branch <name>`, only with `--already-integrated`: names
  the branch an item started without `--worktree` was worked on, so a
  hand-made worktree can be completed the same way. It must exist locally,
  must match the recorded branch if there is one, and is never deleted.
  `--already-integrated` on an item with no recorded branch now asks for
  `--branch` instead of refusing outright.
