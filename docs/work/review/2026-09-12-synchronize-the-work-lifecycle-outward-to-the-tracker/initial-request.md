# Synchronize the work lifecycle outward to the tracker

## What is being asked for

Child **C3** of `2026-08-04-supplement-filesystem-tcw-work-with-an-external-tracker-bridge`.
A work item's lifecycle should show up in the ticket bound to it: when the item
moves locally, the ticket moves in the tracker, without a local transition ever
being undone because the tracker was briefly unreachable.

The epic's spec (§ Design, C3) is the authoritative statement of the boundary and
is not restated here. In summary it asks for: a deterministic outbound event
recorded with the local transition; the local transition committed first;
immediate delivery attempted; `tcw work tracker sync [<slug> | --all]` retrying
until the remote target is observed; mapping keyed on the existing
`TRANSITION_IDS`; only stable links and short summaries going outward; remote
drift reported and never followed automatically; and the current / pending /
conflicting indicator surfaced in `tcw work show` and `tcw work list`.

## Added on 2026-09-14 — this item now owns claiming a linked ticket

`2026-09-14-make-tracker-link-record-a-cross-reference-without-claiming-the-ticket`
removes claiming from `tcw work tracker link`, which becomes a pure
cross-reference: it writes the binding and changes nothing in the tracker. That
leaves claiming for an already-linked item without a home, and **this item is
that home**, decided deliberately in preference to a separate
`tcw work tracker claim <slug>` verb.

So, in addition to the boundary above:

- **`tcw work start` claims the ticket the item is bound to.** Same rules as
  `import` uses today — the configured claim transition, assigned to the caller
  — against the ticket named by the item's binding. An item with no binding
  starts exactly as it does now.
- **`import` keeps claiming** at import time, unchanged. It creates an item from
  a ticket somebody chose to take, so the claim is the point.
- Until this item lands, **`tracker import` is the only command that claims**.
  Someone who links an item and then starts work has a ticket still sitting in
  its original status. That gap was accepted knowingly when `link` was changed;
  closing it is this item's job.

Two questions this leaves for this item's own `spec`, deliberately not decided
on 2026-09-14:

1. What `start` does when the claim fails — the ticket is held by somebody else,
   the tracker is unreachable, the workflow does not offer the transition. The
   choice is between refusing the local start and starting locally while
   reporting the claim as pending, and it should be settled with the same
   reasoning as the rest of this item's outbound delivery, since it is the same
   problem: a remote call that may fail around a local transition that must not
   be undone.
2. Whether the other lifecycle transitions claim or only transition. `start` is
   the one this session decided; `submit`, `complete` and `discard` were not
   discussed.

## Notes

- This document was written on 2026-09-14 by a session processing a different
  inbox entry. The item had no artifacts at all before it, so everything above
  the "Added" heading is **compiled from existing evidence, not taken from a
  requester**: the epic's `spec.md` § Design C3, the `work/synchronize-external-tracker-work`
  capability (`cap-207f2c`, Missing, planning doc this item), and this item's
  title. The "Added" section is the one part that comes from a decision made
  with the user directly.
- Nobody was asked for reference material for this item, because the session
  that wrote this was not working it. Its `spec` should treat the References
  below as a starting set, not as a set somebody curated for it.
- The epic's `spec.md` records C3 as "Blocked by: C2" and does not yet mention
  the claiming hand-off. That spec was written before 2026-09-14. The blocker
  added here is recorded in this item's state, which is what `tcw work start`
  actually reads.

## References

- `2026-08-04-supplement-filesystem-tcw-work-with-an-external-tracker-bridge`,
  `spec.md` § Design → C3 — the authoritative boundary for this item; read it
  before this document.
- `2026-09-14-make-tracker-link-record-a-cross-reference-without-claiming-the-ticket`
  — why claiming needs a new home, and its `spec.md` § Non-goals, which names
  this item as that home. It is also this item's blocker.
- `tcw/tracker/intake.py`, `claim` — the claim rules `start` would reuse, and the
  numbered refusal rows a failed claim at `start` has to answer for.
- `tcw/store/base.py`, `TransitionCommitError` and `PublicationError` — the
  existing shape for "the local move happened, the remote one did not", which
  question 1 above should be answered in terms of.
