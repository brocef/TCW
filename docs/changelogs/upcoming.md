# Upcoming

Developer changelog for the next version. Technical and precise; grouped by
category, with commit hash ranges so entries trace back to source.

## Fixed

- `tcw work complete` on a `--worktree` item now **merges the work branch into
  the primary checkout before teardown**, closing a silent data-loss bug: no
  merge step existed in the code, so `complete` deleted `work/<slug>` while its
  commits were unmerged — any commit made in the worktree became a dangling
  object while the command still printed `completed`. New `merge_worktree()` in
  `tcw/store/fs.py`, called from `_complete` before `st.complete()` (so the merge
  sees the item docs still under `active/`, with no rename/modify overlap). It
  **fails closed**: a conflict aborts the half-merge, leaves the branch +
  worktree intact, keeps the item `active`, and exits non-zero (`--force` does
  not override). A missing branch (recovery re-run) is a quiet no-op.
  `remove_worktree` now swallows the `"is not a working tree"` case (already
  absent) instead of printing a failure line. Regression tests:
  `test_complete_merges_worktree_branch_before_teardown`,
  `test_complete_aborts_on_merge_conflict`. (`b50fbee`..HEAD)
