## Fixed

- `tcw work complete` no longer loses commits made on a worktree's detached
  `HEAD`. New `unbranched_commits` (`tcw/store/fs.py`) lists commits reachable
  from the worktree's `HEAD` and from no branch, tag or remote-tracking branch,
  after checking that `git rev-parse --show-toplevel` is the worktree itself
  (`git -C` on a plain folder under `.worktrees/` otherwise answers for the
  primary checkout).
  - A completion (merge-back or `--already-integrated`) is refused before
    anything changes when there are any, `--force` included; at most ten short
    hashes are named, with the `git -C <worktree> branch <name>` remedy.
  - `remove_worktree` refuses the same way, so a discard keeps the worktree
    (as it keeps the branch) and warns instead.
