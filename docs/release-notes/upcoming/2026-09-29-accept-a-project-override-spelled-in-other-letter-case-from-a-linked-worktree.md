## Fixes

- **A project override works in any letter case from a linked worktree.** On a
  Mac or Windows disk, setting `TCW_PROJECT_<ID>` to a folder spelled with
  different capital letters than the folder has on disk made `tcw validate` fail
  with duplicate projects when run from a linked git worktree. The spelling no
  longer matters.
