## Changed

- **`tcw validate` warns about a project override that reads another
  branch.** Suppose a `TCW_PROJECT_<ID>` variable points at your main
  checkout's copy of a project, and you run from a linked worktree that has
  its own copy. TCW still follows the variable, but it now warns that this
  project is being read from a different branch than everything else. Point
  the variable at the worktree's copy, or unset it, if that was not intended.
