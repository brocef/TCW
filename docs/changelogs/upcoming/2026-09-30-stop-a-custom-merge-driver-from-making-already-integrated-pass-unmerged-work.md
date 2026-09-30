## Fixed

- `complete --already-integrated` could delete an unmerged branch in a
  repository with a custom merge driver: `git merge-tree` runs drivers, and one
  keeping `HEAD`'s side (`merge.<name>.driver=true` under a `merge=<name>`
  attribute from any attributes file) produced `HEAD`'s tree.
  `branch_integration` now runs the trial merge with every configured
  `merge.<name>.driver` overridden to `false` via `-c` (which beats an inherited
  `GIT_CONFIG_PARAMETERS`), so such a file conflicts; the refusal names the
  drivers. New `_merge_drivers` fails closed on a driver name containing `=` or
  on `git config` failing.
- Git's built-in `union` driver is overridden the same way, configured or not:
  it keeps both sides' lines, so a line the branch deleted and `HEAD` changed
  came back as `HEAD`'s. For a worktree item the refusal's way out now removes
  the worktree before deleting the branch, which git otherwise refuses.
