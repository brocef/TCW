A TCW project: a folder whose `tcw-config.yaml` file carries a canonical ID and
which owns bounded `docs/{taxonomy,capabilities,work}/` stores. The nearest
enclosing `tcw-config.yaml` selects the current project. Relations between
projects come only from the entries each project declares under its `projects:`
key (a parent and its child must name each other), never from how folders are
nested or how git repositories are laid out. Folder layout is consulted only to
resolve a relative location to the place it was written against — as inside a
linked git worktree — never to discover a project or infer a relation.
