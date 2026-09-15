# Publish concise progress links and comments to a bound tracker ticket

## The request

The tracker bridge epic set out to keep a Jira ticket current as its linked TCW
work moves along. Goal 4 of the epic asks for more than the ticket's status. It
also asks for **concise progress links**, and the epic's original request says what
that means: "mapped lifecycle events update the tracker with status plus concise
work, branch, and review links," and discard resolutions carry "concise reason
summaries."

`2026-09-12-synchronize-the-work-lifecycle-outward-to-the-tracker` delivered the
status half. When a bound item is started, submitted, reworked, completed or
discarded, its ticket moves to the mapped status. This item is the other half.
Someone who reads only the ticket, such as a product owner with no checkout, should
be able to see from the ticket that work started, went to review, finished, or was
abandoned and why. Where a stable place exists to follow the work, they should get a
link to it.

What the requester asked for, from the epic's request:

- **Short summaries and stable links only.** "Only stable links and short summaries
  are written back." No `spec.md`, `plan.md`, `outcome.md`, `refined-outcome.md`,
  capability prose, diffs or code references are copied to the ticket.
- **Per lifecycle event.** `start`, especially `start --worktree`, which should
  "publish the branch/work link when `--worktree` creates it"; `submit`, as a review
  link; `complete`; and a discard with its reason.
- **Never twice.** "Remote already reflects the event: treat delivery as successful
  and do not duplicate comments or transitions" (epic acceptance criterion 6).
- **Never undoes local work.** A failure to publish leaves the item where it moved.
  The command says the tracker is behind, and `tcw work tracker sync` retries. This
  is the same promise the status half keeps.
- **Where Jira allows it**, the comment may travel with the transition in one call.

## Constraints

- A project with no tracker configured, or an item with no binding, behaves exactly
  as before, and no tracker code is loaded.
- No credential appears in any file, sidecar or output (epic criterion 8).
- `tcw validate` never contacts the tracker.
- The requester's split of authority stands. The tracker owns product
  coordination, and TCW owns technical artifacts. Nothing flows back from ticket
  comments into TCW.
- This run may not write to a real Jira. The fake tracker in
  `tests/tracker_fake.py` stands in for it, and everything must be provable
  against it.

## Out of scope

- Mirroring technical lifecycle artifacts into ticket fields or comments.
- Reading, editing or deleting comments other people wrote.
- Progress events other than lifecycle moves, such as stage artifacts being written.
- Pushing branches. TCW does not push, and this item does not make it.

## Notes

- **No user was available to ask.** This request was compiled on 2026-09-15 by the
  autonomous session driving the epic, from the epic's `initial-request.md`, its
  `spec.md` (goal 4 and § C7), and this item's `intake.md`. References were asked
  for; none were provided beyond those documents. Everything below is inference
  for `spec` to settle.
- **Open questions carried from the split:**
  - What is stable enough to link to? TCW pushes no branches, a local worktree path
    means nothing to a ticket reader, and `work.repository` is optional. Where it is
    present, it describes where the store comes from, which is not necessarily a
    browsable address.
  - When is a comment published, and is it one per move?
  - How is a comment recognised as already posted? The status half keeps no record
    of success, only of failure.
- **The team lead's direction (2026-09-15):** build this item in this run rather than
  discarding it or leaving it for later, reusing the status half's outbound delivery
  path. Stop only if it needs a live-tracker capability the fake cannot stand in for,
  or a design question both advisors say lacks information on something hard to
  undo.

## References

- `docs/work/active/2026-08-04-supplement-filesystem-tcw-work-with-an-external-tracker-bridge/initial-request.md`
  § Intended workflow, § Lifecycle mapping, § Failure and recovery scenarios: the
  requester's own words for what goes outward.
- The epic's `spec.md`, goal 4, § C7 and acceptance criterion 6: the split, and the
  no-duplicate rule.
- `docs/work/completed/2026-09-12-synchronize-the-work-lifecycle-outward-to-the-tracker/`
  (in Git history): the delivery path, the `sync` record and `tcw work tracker sync`
  this item extends.
- `tcw/tracker/sync.py` and `tcw/tracker/jira.py`: the code that path lives in.
