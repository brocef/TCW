As a user, I raise something to the coordinating project with
`tcw work escalate "<title>"`, piping the body on stdin and optionally stamping it
with `--initiative <epic-slug>`. There is no target argument: a project has at
most one registered parent, and TCW resolves it. What it resolves to is the
nearest registered ancestor that keeps a work store, so a grouping project
between me and the board I mean is passed through rather than treated as a
wall. At the root of the graph the command refuses — *"no parent node to
escalate to (this is the root)"* — rather than silently doing nothing, and
where I do have registered ancestry but none of it keeps a board it says that
instead, which sends me somewhere different to fix it.

This is the upward half of the cross-node request channel, and it obeys the same
boundary as its downward counterpart,
[Delegate a request to a child node](tcw://C/work/delegate-a-request-to-a-child-node):
the request lands in the parent's `inbox/` and nowhere else, carries my project's
canonical ID as `from:`, goes to the parent's **configured** store wherever
`work.path` puts it, and fails loudly rather than inventing a phantom inbox if
that store cannot be reached or is not in a Git repository.

It is what I use when work in this project turns out to need a decision or a
change that is not mine to make — a cross-repository scope question, an API another
project owns, or canonical product wording held by the coordinator. Because the
channel is non-blocking, I escalate and carry on: the reply arrives later as a
delegated request in my own inbox, and nothing about my local work waits on it.

The parent decides what becomes of it, through
[Manage the work inbox](tcw://C/work/manage-the-work-inbox).
