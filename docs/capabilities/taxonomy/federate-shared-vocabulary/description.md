As a user, I run `tcw taxonomy extends add <project-id>` to explicitly inherit
the taxonomy of a registered, reachable project. The source project ID is the
inherited namespace, and `docs/taxonomy/config.yaml` stores `extends` as a list
of project IDs. Physical placement and parent/child connection do not imply
inheritance; legacy alias-to-path maps fail closed.
