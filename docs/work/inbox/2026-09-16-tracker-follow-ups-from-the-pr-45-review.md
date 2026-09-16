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
