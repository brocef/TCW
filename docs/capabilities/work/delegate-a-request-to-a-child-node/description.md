As a user, I ask a child project to do something with
`tcw work delegate <child-id> "<title>"`, piping the body on stdin and optionally
stamping it with `--initiative <epic-slug>` so the resulting item joins an epic.
TCW prints the path of the request it wrote.

The first argument is the child's **canonical project ID**, not a filesystem path
— identity, not location. `tcw work nodes` lists the IDs that will be accepted,
and an unrecognised one is refused with the valid children named, so I never have
to guess. See [Inspect the node topology](tcw://C/work/inspect-the-node-topology).

The write boundary is the point of this command. A request lands in the child's
`inbox/` and nowhere else: I cannot create, move, or edit an item in another
project's tracked work. What arrives is a proposal, and the child project decides
whether it becomes a work item — see
[Manage the work inbox](tcw://C/work/manage-the-work-inbox). Each entry records
the sending project's canonical ID as `from:`, so a request always says who asked.

The request goes to the child's **configured** inbox, wherever its `work.path`
puts it, including another repository. If that store cannot be reached the command
fails with a non-zero exit and an error rather than creating a plausible-looking
`docs/work/inbox` folder in the child's code repository — a request I believe I
sent is worse than one I know failed. See
[Configure the work-store location](tcw://C/work/configure-the-work-store-location).

Two requests with the same title on the same day do not collide; the second gets a
numeric suffix.
