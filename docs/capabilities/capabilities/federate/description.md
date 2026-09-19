As a user, I run `tcw capabilities extends <project-id>` to explicitly inherit
capabilities from a registered, reachable project. The source project ID is the
inherited namespace, and `capabilities.extends` in `tcw-config.yaml` stores the
list of project IDs. Inheritance is a property of the project, not of the
ledger, so two projects whose `capabilities.path` resolves to the same folder
may inherit differently. Capability inheritance remains independent from
taxonomy inheritance and from graph connections; legacy alias-to-path maps fail
closed.
