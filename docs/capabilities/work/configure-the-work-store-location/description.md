As a project owner, I can keep a project's work items in another filesystem
location without changing the project's canonical ID or ownership. I set
`work.path` in `tcw-config.yaml`, using an absolute path or a path relative to
the owning project's primary checkout. TCW follows symlinks, routes every work
command and web edit to that store, and commits work transitions in the Git
repository containing it while lifecycle hooks and code worktrees remain in the
owning software repository.

I can scaffold this layout with `tcw work init --path <path>` or `tcw init
--work-path <path> work`. TCW refuses broken, invalid, non-Git, or colliding
stores and never moves an existing non-pristine store automatically.
