As a user, I run `tcw work list` to see the local board, with lifecycle stages,
priority, tags, blockers, and ready-to-close epic state. The board shows live work
and hides both closed columns — `completed` and `discarded` — so `--all` or
`--status discarded` is how I look at what was closed. Items in `review` are
live work, not closed, so they stay on the default board. With
`--include-descendants`, TCW follows the registered project graph and groups
every reachable descendant board by canonical project ID. Descendant items are
qualified as `<project-id>/<slug>`, including deep descendants whose filesystem
location is unrelated to the current project. Unregistered nearby nodes are
never visited. The shorter `-i` and `--incl-desc` spellings are aliases for
`--include-descendants`. In the aggregate view, initiative tasks are indented
beneath their visible owning epic even when a task lives in a descendant node;
the qualified task address is preserved and each task is printed once.
Active board rows show the claimant and UTC start time. Legacy or reworked
active items without claim metadata are shown as unclaimed.

The board also tells me how much raw intake is waiting behind it. After the rows,
on stderr, it says how many inbox entries the node is holding, and with
`--include-descendants` it does so for every node in the board, naming each one
by its project ID. A node with an empty inbox is not mentioned, so a wide sweep
names only the nodes that need a look. The counts are never board rows — an
inbox entry has no slug, status, or lifecycle — so what I pipe is still one line
per work item.
