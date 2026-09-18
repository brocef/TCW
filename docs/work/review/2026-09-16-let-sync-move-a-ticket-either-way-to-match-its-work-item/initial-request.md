# Let sync move a ticket either way to match its work item

## What is wanted

This item is the second child of the epic
`2026-09-16-separate-claim-from-status-movement-in-the-tracker-verbs`. The epic's
spec is the request; this file records what it asks of this child, in the
requester's terms, so someone resuming cold does not have to reconstruct it.

Two things, deliberately put in one item.

**One — `tcw work tracker sync` makes the ticket match the item, in either
direction.** Today the item's status is only ever pushed forward: a ticket that
somebody moved on in the tracker is reported as a conflict and left there, and a
ticket that is simply not where its item says is not moved at all unless TCW has
a record proving it owes the move. The requester's decision is that **the work
item is the source of truth for status**. A ticket ahead of its item is brought
back; a ticket behind it is brought forward.

The one case that must not be broken is the `--part` hold. Where two work items
are bound to the same ticket as different parts, the ticket legitimately lags the
item being synced, because the other part is still open. That is not drift and
must not be "corrected".

**Two — the `claim: owed | done` key is removed from the binding's `sync`
record.** The epic moved this here from the first child. What `owed` really
decides is which tickets `deliver` claims and walks forward, and rewriting those
rules is this child's subject, so the key goes where its meaning is rewritten.

A `tracker.yaml` already on disk that still carries the key must stay readable:
the binding must not become malformed, and the item must not lose its ticket.

## Constraints

- The requester has decided that old versions of `tcw` reading new data is not a
  case to plan for — everyone runs the new version. New code reading old files on
  disk is still a real constraint, which is why the stale `claim:` key must be
  read without complaint.
- The first child has landed: `tcw work tracker claim` and
  `tcw work tracker release` exist, with `tcw/tracker/ownership.py` behind them.
  This item reads ownership from the tracker rather than from the claim record.
- A third child is being implemented at the same time and edits the tracker
  configuration surface in `tcw/store/base.py` — the transition keys and what
  `tcw validate` checks. This item also touches `tcw/store/base.py`, at
  `SYNC_FIELDS`. Edits stay narrow and local so the two merge cleanly.
- The epic names a risk this item has to answer rather than inherit: moving a
  ticket back silently undoes a move somebody made on purpose. Whether that
  deserves a warning, a confirmation, or a record is this item's decision.
- The epic also requires this item to read
  `docs/work/backlog/2026-09-15-record-lasting-evidence-of-a-tracker-hold-on-a-shared-ticket`
  before deciding anything about the hold, so that the hold is not re-broken.

## Out of scope

- Retiring `link --sync-status`, and the lifecycle moves composing claim and
  sync. Both are the fourth child.
- Renaming `transitions.claim` to `transitions.start`. That is the third child,
  in flight now.
- The catch-up walk's own defects, tracked in
  `2026-09-16-close-three-gaps-the-pr-45-review-left-in-tracker-delivery`.
- Durable evidence of a `--part` hold that survives a clone, which is
  `2026-09-15-record-lasting-evidence-of-a-tracker-hold-on-a-shared-ticket` and
  stays in the backlog.

## Notes

- Written from the epic's spec and the code, not from a conversation: the
  requester's decisions are quoted from that spec and from the instruction that
  opened this item. No separate requester interview happened, so nothing here is
  inferred beyond what those two say.
- The facts the epic states about the code were checked against the working tree
  rather than taken on trust; what they turned out to be is recorded in the spec.

## References

- `docs/work/active/2026-09-16-separate-claim-from-status-movement-in-the-tracker-verbs/spec.md`
  — the authoritative statement of scope, especially the C2 section, the goals,
  the non-goals and acceptance criteria 8, 9 and 11.
- `tcw/tracker/sync.py` — the module docstring states the forward-only rule this
  item reverses, and `deliver` is where every decision described above is made.
- `tcw/tracker/ownership.py` — what the first child added, and the verb a refusal
  should now send people to.
- `docs/work/backlog/2026-09-15-record-lasting-evidence-of-a-tracker-hold-on-a-shared-ticket`
  — why a `--part` hold leaves no evidence outside the checkout it happened in,
  and why this item must not assume it can see one.
