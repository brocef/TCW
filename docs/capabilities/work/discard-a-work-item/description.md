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

TCW commits the status move itself, scoped to the item's own folders so unrelated edits in my working tree are never swept in. Where `work.retain` says this status is not kept, that is two commits rather than one — the item is committed where it landed, then removed — so the documents are in the history even though the folder is gone (see [what happens to resolved work](tcw://C/work/keep-resolved-work-out-of-git)). I turn that off with `work.auto-commit-transitions: false` in `tcw-config.yaml`, and `work.trunk-branch` adds an advisory warning when I transition from some other branch.

Discarding records the item's slug exactly as completing does, carrying the
resolution I gave, so references to an abandoned item resolve rather than
reading as mistakes. See [Complete a work item](tcw://C/work/complete-a-work-item).
