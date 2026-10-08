As a user, I close a work item that will not ship with
`tcw work discard <slug> --reason "<why>"`. The item moves to the `discarded`
stage, so a finished item tells shipped work and abandoned work apart by its
stage alone, and the command prints `discarded`.

I can discard from any stage, which covers the common case: an idea I decide
against was usually never started. The reason is required, and is recorded as a
comment on the item (`tcw://C/work/comment-on-a-work-item`).

Because a discard is not a shipment, the capability-records and completion
gates do not apply. A discarded item counts as finished: it stops blocking
whatever it blocked. Its folder stays where it is, so a reference to it still
resolves. Reopening it is a move like any other (`tcw://C/work/advance-a-work-item`)
and needs a reason.

TCW never commits the change; the item's files are mine to commit.
