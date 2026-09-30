# Refuse a catch-up rework whose ticket is already past the item

## What is being asked for

On a Jira binding still marked `catch-up` (left by the retired
`link --sync-status`), `tcw work rework` on an item whose ticket is in In Review
passes the strict gate; the item then moves back to active locally, and only
afterwards does delivery record a conflict ("…past where its item is, so it was
not moved back"). The gate and delivery disagree.

Wanted: no move should pass the gate that delivery then declines. Either the
gate refuses it before anything moves, or the move succeeds with no conflict
record.

## Notes

- Found by the verifier of
  `2026-09-27-close-two-strict-mode-gaps-left-by-the-unfollowable-move-gate`
  (2026-09-29); the code before that item behaves the same way.
- Written without the requester during an autonomous run (the user asked for
  all four open bug items back to back). References: asked; none provided.

## References

- `tcw/tracker/sync.py` `authorize` (the strict gate) and `deliver`'s
  `catch-up` branch — the two rules that disagree.
