A TCW project: a folder holding a `.tcw/` folder whose `tcw-config.yaml` file
carries a canonical ID, and which owns bounded `docs/{taxonomy,capabilities,work}/`
stores. The folder holding `.tcw/` is the project root: every path in the
configuration is read from there. The nearest enclosing folder, the starting
folder included, that holds `.tcw/tcw-config.yaml` selects the current project;
a TCW 3.x project, with `tcw-config.yaml` at its root instead, is recognised
only to be refused, naming the command that converts it to TCW 4. Relations between
projects come only from the entries each project declares under its `projects:`
key (a parent and its child must name each other), never from how folders are
nested or how git repositories are laid out. Folder layout is consulted only to
resolve a relative location to the place it was written against — as inside a
linked git worktree — never to discover a project or infer a relation.
