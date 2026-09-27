# Close two strict-mode gaps left by the unfollowable-move gate

From the review of `2026-09-15-make-the-strict-tracker-gate-refuse-unfollowable-moves-and-allow-child-items`:

1. On a legacy `catch-up` binding, `complete` with the ticket held by someone
   else passes the strict gate (`ownership=False`), but `deliver` does not treat
   it as a no-claim resolution and records a conflict ("held by Bob",
   tests/test_tracker_sync.py ~3086). Predates that item.
2. `tracker import <ticket> --parent <slug>` on a ticket already bound here
   answers "already bound" and exits 0 without nesting the item, with no hint to
   use `tcw work edit --parent`.
3. From verify of the same item: on a legacy `catch-up` binding more than one
   rung away, the gate does not ask; on a workflow whose rung-by-rung path is
   broken part-way (`STRICT_LADDER` with no way out of In Review), `complete`
   exits 1 but leaves the item completed, the ticket in In Review and a
   `conflicting` record — the pattern the gate otherwise now prevents.
