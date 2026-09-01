As a project owner, I can keep a project's work items in another filesystem
location without changing the project's canonical ID or ownership. I set
`work.path` in `tcw-config.yaml`, using an absolute path or a relative one.
A relative path is read against the project's own directory; inside a linked
git worktree it is read against the primary checkout only when it points
outside the checkout, while one that stays inside belongs to the worktree like
the default store does (see
[Run TCW from inside a git worktree](tcw://C/cli/run-from-a-git-worktree)). TCW follows symlinks, routes every work
command and web edit to that store, and commits work transitions in the Git
repository containing it while lifecycle hooks and code worktrees remain in the
owning software repository. That routing is uniform: cross-node requests, epic
rollups, capability-drift lookups, and node discovery all resolve the configured
store rather than a default folder, and a leftover `docs/work/` directory beside
a configured store is ignored rather than treated as the store.

Because the configured store is the only authority, a project whose default
`docs/work/` layout is missing its inbox or any status folder counts as having no
work store until I restore it with `tcw work init`.

The same key exists for the other two components —
[taxonomy](tcw://C/taxonomy/configure-the-taxonomy-store-location) and
[capabilities](tcw://C/capabilities/configure-the-capabilities-store-location) —
and all three resolve through one ladder, so what is true of one is true of the
others.

`work.path` says where the store sits on **this** machine. Beside it I can add a
`repository` block saying where the store *comes from*, so a machine that has
never seen it can obtain it — see
[declaring the home repository](tcw://C/work/declare-the-work-stores-home-repository).
The declaration is a fallback and never an override: a store already present at
`work.path` keeps being used untouched, so one configuration serves both a laptop
that has the folder and a fresh checkout that does not.

I can scaffold this layout with `tcw work init --path <path>` or `tcw init
--work-path <path> work`. TCW refuses broken, invalid, non-Git, or colliding
stores — including a store whose items the repository's own ignore rules would
hide, which would otherwise look like a working store holding untracked work —
and never moves an existing non-pristine store automatically. Those refusals
leave nothing behind. A rule that arrives *after* I set the store up — written
by hand, naming a single item, or pulled in from someone else — is no longer
invisible either: the write itself tells me the item will not be recorded.
