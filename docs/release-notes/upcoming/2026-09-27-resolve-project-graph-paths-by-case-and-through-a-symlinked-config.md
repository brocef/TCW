## Fixes

- Connected projects load once, not twice, when a path to one is written in
  different letter case on macOS or Windows, and when you work inside a git
  submodule in a linked worktree, or in a linked worktree of a repository that
  is itself a submodule.
- A project whose `tcw-config.yaml` is a symbolic link now finds the projects
  its config names relative to its own folder, not the link's target.
