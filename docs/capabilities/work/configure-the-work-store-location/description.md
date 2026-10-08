As a project owner, I can keep a project's work items in another filesystem
location without changing the project's canonical ID or ownership. I set
`work.path` in `tcw-config.yaml`, using an absolute path or a relative one.
A relative path is read against the project's own directory; inside a linked
git worktree it is read against the primary checkout only when it points
outside the checkout, while one that stays inside belongs to the worktree like
the default store does (see
[Run TCW from inside a git worktree](tcw://C/cli/run-from-a-git-worktree)). TCW follows symlinks and routes every
work command to that store, while lifecycle hooks still run in the owning
software project. That routing is uniform: delegation into another project,
capability drift, `tcw validate` and the project graph all resolve the
configured store rather than a default folder, and a leftover `docs/work/`
directory beside a configured store is ignored rather than treated as the store.

A work store is present when its folder is. Nothing inside it is required, so
an empty store is a real one.

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
--work-path <path> work`. TCW refuses a broken, invalid or non-Git location, and
never moves a store that holds a work item: that move is mine to make. Those
refusals leave nothing behind. TCW never commits what it writes there; the
store's files are mine to commit.
