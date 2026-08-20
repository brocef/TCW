As a project owner, I can keep a project's work items in another filesystem
location without changing the project's canonical ID or ownership. I set
`work.path` in `tcw-config.yaml`, using an absolute path or a path relative to
the owning project's primary checkout. TCW follows symlinks, routes every work
command and web edit to that store, and commits work transitions in the Git
repository containing it while lifecycle hooks and code worktrees remain in the
owning software repository. That routing is uniform: cross-node requests, epic
rollups, capability-drift lookups, and node discovery all resolve the configured
store rather than a default folder, and a leftover `docs/work/` directory beside
a configured store is ignored rather than treated as the store.

Because the configured store is the only authority, a project whose default
`docs/work/` layout is missing its inbox or any status folder counts as having no
work store until I restore it with `tcw work init`.

I can scaffold this layout with `tcw work init --path <path>` or `tcw init
--work-path <path> work`. TCW refuses broken, invalid, non-Git, or colliding
stores — including a store whose items the repository's own ignore rules would
hide, which would otherwise look like a working store holding untracked work —
and never moves an existing non-pristine store automatically. Those refusals
leave nothing behind.
