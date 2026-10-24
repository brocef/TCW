As a user, I run `tcw taxonomy extends add <project-id>` to explicitly inherit
the taxonomy of an ancestor. The source project ID is the
inherited namespace, and `taxonomy.extends` in `tcw-config.yaml` stores the list
of project IDs. Inheritance is a property of the project, not of the tree, so
two projects whose `taxonomy.path` resolves to the same folder may inherit
differently. Inheritance is transitive: if A extends B and B extends C, A
resolves both `B/` and `C/` terms under their owning project IDs. Physical
placement does not imply inheritance, and neither does a parent link alone:
the ancestor must also be listed in `taxonomy.extends`. Legacy alias-to-path
maps fail closed. Adding or removing a project changes only the
`taxonomy.extends` lines of `tcw-config.yaml`, keeping my comments and
formatting; a file it cannot edit that way is refused with the exact edit to
make by hand, never rewritten.

Until `extends` is replaced, it may name only an ancestor whose parent links
pass `taxonomy` down to this project: a parent, or a project further up, reached
through links whose `inherit` includes `taxonomy` (see [Name a project's
parents](tcw://C/cli/name-a-projects-parents)). Any other project — a child, a
sibling, a parent with `inherit: none`, or one this project does not name at
all — is refused, by `tcw taxonomy extends add` with exit 2 and the file left
unchanged, and when read, with a message saying to name it under `parents:`
with an `inherit` that includes `taxonomy`. When such an ancestor, or a project
between it and this one, is not on this machine or its parents cannot be read,
a command that reads the taxonomy stops with exit 7, naming the project and how
to fetch it, and `tcw validate` reports it as could not be checked.
