# Requester decisions taken at the epic's verify

Kept as its own file because the epic cannot reach `verify` until its last child
lands, and these were answered before then. They fold into `refined-outcome.md`
when that is written; this file goes away with them.

## Risk 2 — "the item is truth" silently undoing a deliberate Jira move

The spec's risk 2 asked whether it is tolerable that `sync` reverses a status
somebody set by hand in the tracker, because no test can answer it. The plan
reserved it for the requester at this stage.

**Answered 2026-09-23: the rule always applies.** The item is the source of truth
for status without exception, and `sync` moving a ticket back to match its item is
correct behavior rather than a case needing a carve-out.

This closes risk 2. It also means the epic ships with that behavior deliberately,
not by omission, and `docs/guide/jira.md` should read as a statement of the rule
rather than a caveat about it.

**One thing this does not settle**, and which is filed rather than assumed: the
closeout review found that a `sync` delivering a resolution over a ticket another
account holds says nothing about having done so. The rule above says it is right to
do it. Whether it should say so on the way past is a separate question about what
the command prints, and the recommendation is that it should — taking a ticket out
of somebody else's hands is worth one line of output even when it is correct.

## The real-Jira walkthrough

The epic's plan lists a walkthrough against a live Jira project as something the
test suite cannot substitute for: criteria 5, 6, 7 and 8, with one throwaway ticket
taken through the whole lifecycle. Every child so far has deferred it, and C4's
`refined-outcome.md` records the deferral.

**Answered 2026-09-23: it is required before this ships.** The deferral ends here.

Consequences, recorded so the sequencing is not rediscovered later:

- It runs **after** the last child lands, because the point is to exercise the
  shipped code, not an intermediate state.
- It runs against a real project and creates and moves a real ticket. That ticket
  is a throwaway and is cleaned up afterwards.
- It is the last gate before the epic closes. If it disagrees with the fake
  tracker, the fake tracker is what is wrong, and that becomes its own item rather
  than a silent amendment to a criterion.
