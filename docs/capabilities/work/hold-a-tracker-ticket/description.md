As a developer whose work items are bound to Jira tickets, I can say that a piece
of work is mine — and later that it is not — without starting it, finishing it,
or moving its ticket anywhere.

`tcw work tracker claim <slug>` records me as the item's owner and assigns its
ticket to me. It applies no workflow transition and changes no status: a backlog
item stays in the backlog, and the ticket stays exactly where it was.
`tcw work tracker release <slug>` gives both back, leaving the item's status, the
ticket's status and the binding alone.

Ownership is one thing rather than two. Both halves are written by the same run,
so if the ticket cannot be assigned nothing is recorded locally either, and I am
told why. Releasing is the same in reverse: where a Jira project does not allow
unassigned issues and refuses the release, my item keeps its owner rather than the
two disagreeing.

Running either command twice is safe. Claiming something I already hold succeeds
and sends nothing, so re-running is how I finish a command that failed halfway.
Releasing something nobody holds does the same.

An item somebody else holds is refused by name, and `claim --take-over` or
`release --force` overrides that — for recovering work from an account that has
gone away. An item with no ticket bound to it is still claimable: I get the local
half, and TCW says the ticket half was skipped. A resolved ticket is refused,
because owning finished work means nothing.

Releasing an item that is already active leaves it active with nobody holding it,
which is what handing work over looks like until the next person claims it.

When two of us claim at once, TCW assigns the ticket and then reads it back, so
whoever got there second is told who holds it instead of silently losing their
claim. Two claims that overlap exactly can still both succeed. Where that is not
acceptable and the Jira workflow genuinely refuses a second claimant, I name a
transition in `work.tracker.exclusive-claim-transition` and a claim asserts
through it — which restores the stronger guarantee and costs a status move on
every claim, so it is off by default.
