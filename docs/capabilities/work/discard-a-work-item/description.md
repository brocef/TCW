As a user, I close a work item that will not ship by running
`tcw work complete <slug> --resolution <wontfix|duplicate|superseded> --confirm`,
and the item lands in `discarded/` rather than `completed/` — so `completed/`
answers "what shipped?" on its own.

I can discard directly from `backlog` without first starting the item, which is
the common case: an idea I decide against was usually never started. Discarding
is terminal; reviving an abandoned idea means raising a fresh item.

Because a discard is not a shipment, the Definition-of-Done checklist, the
capability-reconciliation gate, and the unresolved-blocker check do not apply — I still confirm the closure
explicitly, and TCW warns me (without blocking) if the item declared
capabilities I should mark `Omitted`. A discarded item counts as resolved: it
stops blocking whatever it blocked, and it lets its parent epic close.
