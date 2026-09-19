As a user, I run `tcw taxonomy extends add <project-id>` to explicitly inherit
the taxonomy of a registered, reachable project. The source project ID is the
inherited namespace, and `taxonomy.extends` in `tcw-config.yaml` stores the list
of project IDs. Inheritance is a property of the project, not of the tree, so
two projects whose `taxonomy.path` resolves to the same folder may inherit
differently. Inheritance is transitive: if A extends B and B extends C, A
resolves both `B/` and `C/` terms under their owning project IDs. Physical
placement and parent/child connection do not imply inheritance; legacy
alias-to-path maps fail closed.
