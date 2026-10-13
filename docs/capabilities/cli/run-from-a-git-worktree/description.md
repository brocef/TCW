As a user, I run any `tcw` command from inside a linked git worktree and get the
same connected projects the primary checkout resolves. A relative location under
`projects:` was written against the project's position in its primary checkout,
so inside a worktree it would otherwise point at the wrong folder and every
command — including read-only ones — would fail. TCW re-anchors such a location
against the main worktree root, but only when the target leaves the worktree: a
target that stays inside is a sibling project on the same branch and stays with
the worktree, so hosting
[multiple projects in one repo](tcw://C/cli/host-multiple-projects-in-one-repo)
behaves the same inside a worktree as outside it. An absolute location is never
re-anchored — but if it names the current project's counterpart in the primary
checkout, it still resolves to the worktree copy, so the project appears once
rather than twice.

A **configured store path** follows the same rule. Whether I point
`work.path`, `taxonomy.path` or `capabilities.path` somewhere else, a relative
one that leaves the checkout re-anchors — at *this project's* counterpart under
the main worktree, so a project nested inside the repository keeps its own
sub-path — and one that stays inside belongs to the worktree, exactly as the
default does. An absolute store path is never re-anchored.

The project I operate on is the **worktree**: its `docs/work/`,
`docs/capabilities/` and `docs/taxonomy/` are the checked-out ones — as is a
store I relocated with a relative path that stays in the checkout — and a work
item I create lands there. Only the connections between projects are resolved
through the primary checkout, so the current project appears once, not twice.

Nothing changes outside a worktree, and nothing changes for a project that is
not in a git repository at all.
