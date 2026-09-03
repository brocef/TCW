As a user, I run `tcw work nodes` to see where the current project sits in the
connected-project graph. It prints the current node's canonical ID, its
registered parent, and its registered children — each by ID, never by filesystem
path, because IDs are identity and paths are only adapter locators. A project
with no parent prints `parent: (none — root)`; one with no children prints
`children: (none — leaf)`. A registered parent that keeps no work store prints
`parent: <id> (no work store)` — it is a grouping project, not the top of the
graph, and the two used to read identically.

Only *registered* projects appear. TCW reads the `connected-projects` section of
`tcw-config.yaml` rather than scanning the disk, so a git repository sitting next
to or inside this one is invisible to the topology until it is registered — being
nearby is not a relationship. A registered project whose work store cannot be
opened here is still listed, and marked with which of the two reasons applies —
it keeps no board at all, or it keeps one this machine has not obtained.
Omitting them made a project with children read as a leaf. What the *unmarked*
entries print is the set of nodes the cross-node commands can actually reach.

That makes it the command to run first when a cross-node operation is not
behaving: the IDs listed here are exactly the ones
[Delegate a request to a child node](tcw://C/work/delegate-a-request-to-a-child-node)
accepts, and the descendants
[Reconcile an epic rollup](tcw://C/work/reconcile-an-epic-rollup) will follow. If
a project I expected is missing, the problem is its registration or its work
store, not the command I was trying to run.

The board view is separate: `tcw work list --include-descendants` aggregates the
*items* held across the same graph, while this shows the graph itself. See
[View the board](tcw://C/work/view-the-board).
