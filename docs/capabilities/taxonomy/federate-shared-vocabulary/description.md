As a user, I inherit the taxonomy of every parent whose `inherit` includes
`taxonomy`, named under `parents:` in my project's `.tcw/tcw-config.yaml` (see
[Name a project's parents](tcw://C/cli/name-a-projects-parents)), through every
level: a parent's own parents pass their taxonomy down too, as far as each
link's `inherit` allows, without my listing them. Nothing else makes a taxonomy
inherited. TCW 4.0 removed the separate list of inherited projects that the
`taxonomy:` section used to hold, and the commands that edited it; a list of
that kind left in my own `.tcw/tcw-config.yaml` is an error naming `parents:`,
and every `tcw taxonomy` command exits 1 until I name its projects under
`parents:` and delete it. A parent that keeps no taxonomy adds nothing and is
not an error. Inheritance is a property of the project, not of the tree, so two
projects whose `taxonomy.path` resolves to the same folder may inherit
differently.

An inherited term is read by its path like one of my own, once per path,
combined from the projects that have a term there, and its full identifier
names the project it belongs to. To change one, I put my own term at the same
path (see [Override an inherited
term](tcw://C/taxonomy/override-an-inherited-term)). Opening my taxonomy reads
no other project: inherited terms are read only when a command needs them.
When a parent, or a project between it and mine, is not on this machine or its
parents cannot be read, a command that needs the inherited terms stops with
exit 7, naming the project and how to fetch it; one that reads only my own
terms still works, and `tcw validate` reports the inherited taxonomy as could
not be checked.
