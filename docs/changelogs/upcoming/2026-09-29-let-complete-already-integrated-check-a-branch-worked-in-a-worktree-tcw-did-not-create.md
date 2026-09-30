## Fixed

- `tcw work complete --already-integrated` checked nothing. It skipped the
  merge-back on the caller's word, and the teardown then ran
  `git branch -D`, so a branch that was never merged was force-deleted with
  its work. It now checks, before anything changes, that the branch reached
  the node repository's `HEAD`: either its tip is an ancestor
  (`git merge-base --is-ancestor`), or `git merge-tree --write-tree` gives
  `HEAD`'s own tree, which is how a squash or rebase merge looks. Otherwise it
  refuses, naming the branch and the commit, and says how to get out when the
  work landed some other way. It also refuses when `HEAD` is the branch itself
  (compared by full ref, so a tag of the same name cannot hide it) or detached,
  and says so separately when git cannot answer (older than 2.38). A recorded
  branch that is already gone still passes. New
  helpers `branch_integration` and `branch_exists` in `tcw/store/fs.py`.

## Added

- `tcw work complete --branch <name>`, only with `--already-integrated`: names
  the branch an item started without `--worktree` was worked on, so a
  hand-made worktree can be completed the same way. It must exist locally,
  must match the recorded branch if there is one, and is never deleted.
  `--already-integrated` on an item with no recorded branch is still refused,
  now naming `--branch`. `--branch` on a discard is a usage error.
