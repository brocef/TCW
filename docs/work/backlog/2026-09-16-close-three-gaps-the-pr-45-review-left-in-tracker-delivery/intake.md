## Inbox manifest

- `2026-09-16-tracker-follow-ups-from-the-pr-45-review.md`

## Inbox body

# Tracker follow-ups from the pull request #45 review

## Desired outcome

Two tracker-sync weaknesses that review of pull request #45 found, and that were
outside that change, are either fixed or shown not to matter.

## Context

Found while reviewing `2026-09-15-follow-late-linked-tickets-and-name-transitions-in-tracker-sync`
(pull request #45). Written by hand, because TCW's own code was being changed on that
branch.

1. **`tcw work start` can move a ticket backwards.** `deliver` in
   `tcw/tracker/sync.py` skips its "already past the claim's own status" check when
   the move is `start` (`starting`), so `start` — and `start --take-over` — applies
   the claim transition from wherever the ticket is. On a workflow that offers the
   claim transition from every status, starting a backlog item whose linked ticket
   is already in review moves the ticket back to In Progress. This predates #45,
   which fixed the same shape only for `link --sync-status` and `sync`. Decide
   whether `start` should refuse, or carry on without a claim when the ticket is
   already assigned to the caller, as `link --sync-status` now does.

2. **The catch-up walk does not check that each step landed where it aimed.** After
   each transition the walk re-reads the ticket and plans the next step from wherever
   it now is. If a Jira automation moved the ticket somewhere else in between, the
   next step starts from that status instead of stopping. Unconfirmed: nobody has
   reproduced a harmful result, and every step is still bounded to statuses the
   project mapped. Worth a test with the fake tracker before deciding whether the
   walk should stop when a step lands off its target.

3. **Under strict mode, a ticket already yours and past In Progress is never asked
   whether its claim is exclusive.** When `link --sync-status` or `sync` carries on
   without a claim, `deliver` in `tcw/tracker/sync.py` runs `claim_refusal` only for
   a ticket on the claim's own status, because that check refuses any other status.
   So a ticket already in review, on a workflow that offers the claim transition from
   every status, is caught up even though a second person could still claim it.
   This is a design question, not a defect: decide whether strict mode should ask a
   different exclusivity question for such a ticket, or accept the gap and document it.

## Triage (2026-09-16)

Accepted whole. All three parts sit in `deliver` in `tcw/tracker/sync.py` and come
from one review, so they are kept as one item rather than split by kind.

- **Part 1 confirmed at `632f023`.** `tcw/tracker/sync.py:297` guards the
  "already past the claim's own status" check with `if not starting:`, so `start`
  and `start --take-over` skip it. Not tracked anywhere else on the board.
- **Part 2** is a gap in the catch-up walk that pull request #45 itself added, so it
  is the most direct follow-up of the four items this review produced.
- **Part 3 overlaps `2026-09-15-make-the-strict-tracker-gate-refuse-unfollowable-moves-and-allow-child-items`**,
  which owns what strict mode refuses (`authorize` and `binding_refusal`). This part
  is about `claim_refusal` inside `deliver`, which that item does not name. Left here
  because it arrived with parts 1 and 2 and reads as one question about delivery;
  a cross-reference is recorded on that item. If either reaches `spec` first, settle
  which one owns the exclusivity question before writing it.
