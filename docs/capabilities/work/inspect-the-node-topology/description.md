As a user, I run `tcw work nodes` to see where the current project sits in the
connected-project graph. It prints the current node's canonical ID, its
registered parent, and its registered children — each by ID, never by filesystem
path, because IDs are identity and paths are only adapter locators. A project
with no parent prints `parent: (none — root)`; one with no children prints
`children: (none — leaf)`.

Only *registered* projects appear. TCW reads the `connected-projects` section of
`tcw-config.yaml` rather than scanning the disk, so a git repository sitting next
to or inside this one is invisible to the topology until it is registered — being
nearby is not a relationship. A registered project whose work store cannot be
opened here — parent or child alike, marked the same way on both lines — is
still listed, with which of the two reasons applies: `(no work store)` where it
keeps no board at all, `(work store not provisioned here)` where it declares one
this machine has not obtained. Leaving them out made a project with children read
as a leaf, and calling a grouping parent the root hid a whole project from me.

That makes it the command to run first when work in another project is not
behaving: the IDs listed here, unmarked, are the projects
[Delegate a work item to another project](tcw://C/work/delegate-a-work-item-to-another-project)
can reach. If a project I expected is missing, the problem is its registration
or its work store, not the command I was trying to run.

Upstream projects — declared by this node or an ancestor, read here but never
written — are listed apart, under `upstream (read-only):`, each with the project
that declared it and where it is (or `(not in this checkout)`). The section is
printed only when there is one. Delegation does not reach them. See
[Read from an upstream project](tcw://C/cli/read-from-an-upstream-project).
