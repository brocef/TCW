# Let tracker sync name its transitions, bring a late-linked ticket forward, and stop reading ordinary moves as drift

## What is wanted

When a bound item moves, its tracker ticket should follow, in the ordinary
situations a team adopting the Jira integration actually meets. Today four of them
leave the ticket stuck and report it as a conflict someone must repair by hand:

1. **Two transitions lead to the same status** (GitHub #40). Many Jira workflows
   have one transition for finished work and one for abandoned work, both ending in
   `Done`. Sync needs exactly one transition into the mapped status, so `complete`
   (and a discard mapped to the same status) can never sync, and no setting gets
   around it. The reporter wants to be able to say which transition a move uses, the
   way `transitions.claim` already names the claim, so a discard can also use the
   transition that sets the matching Jira resolution.
2. **An item linked after it was started** (GitHub #42). Linking is the documented
   way to tie existing work to a ticket, and existing work is often already active
   or in review. The ticket stays in its old status for good, every later move is
   reported as a conflict, `tracker.yaml` records `claim: done` although nothing was
   claimed, and the conflict message blames a hand move that never happened. Wanted:
   the ticket can be brought forward to where the item is, and the record and message
   say what really happened.
3. **Two failed moves, then a hand move** (lifecycle-sync review, §2). After a failed
   `submit` and a failed `complete`, moving the ticket by hand to `In Review` is
   reported as drift, although it is a status between where the record started and
   where it was going.
4. **`tcw work tracker sync <slug>` skips an item owned by someone else and exits 0**
   (combined review, §2). Under strict mode that leaves an item whose record owes a
   claim stuck: `submit` says "run sync", and sync says "skipped" and succeeds.
5. **Discarding unstarted work leaves its ticket open** (GitHub #41). Every move
   requires the ticket to be assigned to the caller. A backlog item linked to an
   unassigned ticket and then discarded is refused, so the ticket stays open with no
   resolution. Teams whose queue selects unassigned tickets hit this for almost every
   linked backlog item (115 of 125 in the reporter's case), and the refusal describes an
   unassigned ticket as if someone else held it.

## Constraints

- **Multi-step moves are allowed for bringing a late-linked ticket forward.** The
  sync item's spec made "a ticket that does not offer exactly one transition is
  never moved by chaining" a non-goal. The maintainer lifted that for this case at
  triage: the request permits walking a ticket through more than one transition (for
  example `Start`, then `Submit`) to reach the item's status. How far that goes is
  for the spec.
- **An unassigned ticket may be moved by a discard only** (decided with the maintainer
  after triage, choosing the issue's "discard only" option over "assign first"). Every
  other move keeps today's rule that the ticket must be assigned to the caller, and this
  revisits the sync spec's agreed "unassigned counts as not assigned" rule for discards
  alone.
- A ticket assigned to a **different** account is still not moved.
- When no transition is named, today's rule (exactly one transition into the target)
  keeps working for projects that rely on it.
- `tcw validate` checks any new `work.tracker` keys for shape only, as it does
  `statuses` today.

## Out of scope

- Assigning an unassigned ticket to the caller before a move (GitHub #41's other
  option), and moving an unassigned ticket for anything but a discard.
- §1 of the lifecycle-sync entry (staged records blocking a worktree merge-back) —
  tracked in `2026-09-15-harden-tracker-binding-reads-and-writes-and-jira-response-parsing`.
- Checking a workflow ahead of time — GitHub #44, tracked in
  `2026-09-15-check-the-tracker-s-workflow-against-the-statuses-mapping-in-tcw-validate`.

## Notes

- Merged at triage from GitHub #40, #42 and #41 and two review follow-ups, because all
  change how sync decides and reports a move; the maintainer asked for items touching
  the same feature to be combined. Every source is kept verbatim in `intake.md`.
- Bringing a late-linked ticket forward (part 2) may itself need to claim, and so
  assign, the ticket; that is the claim's existing behaviour, not the "assign first"
  option excluded above.
- Reference material: asked; none provided beyond what `intake.md` cites.
- GitHub #40, #41 and #42 were filed by the maintainer and stay open until the fix ships
  (see `CLAUDE.md`, "Closing the originating GitHub issue waits for publication").

## References

- `docs/work/completed/2026-09-12-synchronize-the-work-lifecycle-outward-to-the-tracker/spec.md` —
  the rules this changes: § 4 step 5 (assignment), step 7 (exactly one transition),
  and the "never moved by chaining" non-goal.
- `docs/work/completed/2026-09-14-make-tracker-link-record-a-cross-reference-without-claiming-the-ticket/spec.md` —
  its Risks section accepted "nothing claims a linked ticket" as a known gap, which
  #42 is the consequence of.
