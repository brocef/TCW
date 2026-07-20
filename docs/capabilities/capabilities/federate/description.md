As a user, I run `tcw capabilities extends <project-id>` to explicitly inherit
capabilities from a registered, reachable project. The source project ID is the
inherited namespace, and `.config.yaml` stores `extends` as a list of project
IDs. Capability inheritance remains independent from taxonomy inheritance and
from graph connections; legacy alias-to-path maps fail closed.
