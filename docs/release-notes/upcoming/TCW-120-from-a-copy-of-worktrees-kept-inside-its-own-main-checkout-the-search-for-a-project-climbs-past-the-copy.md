## Fixes

- **Working from a copy kept inside your project's own folder.** When a set
  of nested repositories is copied as git worktrees inside the main folder,
  as Claude Code does in `.claude/worktrees/`, TCW no longer reports a
  project as "declared by more than one folder", no longer asks you to
  migrate the original, and no longer reads the original's project when the
  copy lacks it. Looking up a project from the copy now stays inside the
  copy and the folders above the original, as it already did for a copy
  kept anywhere else. This also holds when the copied repository is a git
  submodule. `tcw migrate` run in such a copy no longer writes a manifest
  entry the original's run does not.
