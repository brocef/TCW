As a user, I run any `tcw` command from inside a linked git worktree and get the
same connected projects the primary checkout resolves. A relative path in a
manifest entry was written against the project's position in its primary
checkout, so inside a worktree it would otherwise point at the wrong folder and
every command — including read-only ones — would fail. TCW re-anchors such a
path against the main checkout, but only when the target leaves the worktree: a
target that stays inside is a sibling project on the same branch and stays with
the worktree. A target that leaves the worktree is first read as written: when
it lands on a project in a checkout, main or linked, of another repository, and
of the repository the entry names when it names one, it is read there. So a
copy made of linked worktrees, one inside another, such as a child
repository's worktree placed inside its workspace's worktree, keeps to the
copy, while a worktree made anywhere else reads beside the main checkout.
Hosting
[multiple projects in one repo](tcw://C/cli/host-multiple-projects-in-one-repo)
behaves the same inside a worktree as outside it. The search for a project's
folder works the same way: the folders outside the repository, next to it or
enclosing it, are looked for from the main checkout. A project found in the
main checkout whose copy is in the worktree is the worktree's copy, so it
appears once rather than twice.

The worktree's tracked files are its own: its `.tcw/tcw-config.yaml` and
`.tcw/tcw-manifest.yaml` are the ones on its branch. Its personal files are
not tracked, so a new worktree has none: when it has no
`.tcw/tcw-config.local.yaml` or `.tcw/tcw-manifest.local.yaml` of its own, the
main checkout's is read, as though it sat in the worktree.

A **configured store path** follows the same rule as a manifest path. Whether I
point `work.path`, `taxonomy.path` or `capabilities.path` somewhere else, a
relative one that leaves the checkout re-anchors — at *this project's*
counterpart under the main checkout, so a project nested inside the repository
keeps its own sub-path — unless, read as written, it lands on a folder inside
another repository's checkout, and one that stays inside belongs to the
worktree, exactly as the default does. An absolute store path is never re-anchored.

The project I operate on is the **worktree**: its `docs/work/`,
`docs/capabilities/` and `docs/taxonomy/` are the checked-out ones — as is a
store I relocated with a relative path that stays in the checkout — and a work
item I create lands there.

Nothing changes outside a worktree, and nothing changes for a project that is
not in a git repository at all.
