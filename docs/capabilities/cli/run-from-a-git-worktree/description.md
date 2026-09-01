As a user, I run any `tcw` command from inside a linked git worktree and get the
same project graph the primary checkout resolves. A relative
`connected-projects` locator was written against the node's position in its
primary checkout, so inside a worktree it would otherwise point at the wrong
directory and every command — including read-only ones — would fail. TCW
re-anchors such a locator against the main worktree root, but only when the
target leaves the worktree: a target that stays inside is a sibling node on the
same branch and stays with the worktree, so hosting
[multiple projects in one repo](tcw://C/cli/host-multiple-projects-in-one-repo)
behaves the same inside a worktree as outside it. An absolute locator is never
re-anchored — but if it names the current project's counterpart in the primary
checkout, it still resolves to the worktree copy, so the project appears once
rather than twice.

A **configured store path** follows the same rule. Whether I point
`work.path`, `taxonomy.path` or `capabilities.path` somewhere else, a relative
one that leaves the checkout re-anchors — at *this node's* counterpart under the
main worktree, so a node nested inside the repository keeps its own sub-path —
and one that stays inside belongs to the worktree, exactly as the default does.
An absolute store path is never re-anchored.

The node I operate on is the **worktree**: its `docs/work/`,
`docs/capabilities/` and `docs/taxonomy/` are the checked-out ones — as is a
store I relocated with a relative path that stays in the checkout — and a work
item I create lands there. Only the shape of the graph is resolved through the
primary checkout, so the current project appears once, not twice.

Nothing changes outside a worktree, and nothing changes for a project that is
not in a git repository at all.

One thing I cannot do from inside a worktree is
[complete the work item](tcw://C/work/complete-a-work-item) that worktree
belongs to — the merge-back and teardown act on the primary checkout, so TCW
refuses and tells me where to re-run it.
