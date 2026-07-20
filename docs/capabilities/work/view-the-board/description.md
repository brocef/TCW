As a user, I run `tcw work list` to see the local board, with lifecycle stages,
priority, tags, blockers, and ready-to-close epic state. With
`--include-descendants`, TCW follows the registered project graph and groups
every reachable descendant board by canonical project ID. Descendant items are
qualified as `<project-id>/<slug>`, including deep descendants whose filesystem
location is unrelated to the current project. Unregistered nearby nodes are
never visited.
