A TCW project: a folder holding a `.tcw/` folder whose `tcw-config.yaml` file
carries a canonical ID, and which owns bounded `docs/{taxonomy,capabilities,work}/`
stores. The folder holding `.tcw/` is the project root: every path in the
configuration is read from there. The nearest enclosing folder, the starting
folder included, that holds `.tcw/tcw-config.yaml` selects the current project;
a TCW 3.x project, with `tcw-config.yaml` at its root instead, is recognised
only to be refused, naming the command that converts it to TCW 4. Relations between
projects come only from the IDs each project declares: its parents under
`parents:`, in order, and the children it lists under `children:`, each of
which must name it back. They never come from how folders are nested or how
git repositories are laid out. A project's family is its ancestors and its
descendants, never its siblings. Where a connected project is on
this machine is a separate fact: `TCW_PROJECT_<ID>`, a manifest entry, or a
search of the folders next to the naming project and enclosing it, which
never looks inside a project. Folder layout is consulted only to find a
project's folder from its ID, and to resolve a relative path to the place it
was written against — as inside a linked git worktree — never to infer a
relation.
