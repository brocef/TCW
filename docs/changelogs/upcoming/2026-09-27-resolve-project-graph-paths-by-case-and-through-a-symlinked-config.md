## Fixed

- `FsProjectRegistry` (`tcw/store/project.py`) keys nodes by folder identity
  (`_canonical`, first spelling kept), so a locator spelled in other letter case
  on a case-insensitive disk no longer loads a node twice.
- Config paths are resolved with `_config_file` (folder resolved, file not
  followed), so a symlinked `tcw-config.yaml` belongs to the folder it sits in
  and its relative locators are read from there.
- `worktree_anchors` finds a submodule repository's main worktree from its
  `core.worktree`, and a submodule checked out in a superproject's linked
  worktree takes the superproject's anchors; both layouts used to get none and
  report duplicates.
