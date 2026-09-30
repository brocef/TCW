## Fixed

- On a case-insensitive disk, a `TCW_PROJECT_<ID>` override spelling the
  primary checkout's folder in other letter case no longer makes `tcw validate`
  in a linked worktree fail with duplicate ids and reciprocity errors. A new
  private `_below(path, root)` in `tcw/store/project.py` decides "inside this
  folder" by device and inode when the text comparison fails; `_locator_path`
  (Rule 1), `_worktree_copy` (Rule 2), and in `tcw/store/fs.py`
  `anchor_configured_path` and `worktree_node_root` use it.
  `worktree_node_root` no longer raises `ValueError` for a node path spelled
  differently from git's worktree root.
