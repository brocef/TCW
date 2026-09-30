## Fixed

- On a legacy `catch-up` binding, `tcw work rework` from review (ticket in
  review) and `tcw work start` of a ticket already further on no longer record
  a conflict after the item has moved. `deliver`'s catch-up branch now declines
  a ticket above its item only for a `sync` with no window of its own
  (`catch_up_declines` in `tcw/tracker/sync.py`); a lifecycle move, or a `sync`
  replaying one, whose ticket is above the item skips the catch-up walk and is
  carried as on a binding without `catch-up` — the move's own transition for a
  rework (not the start transition the walk would use), held for a start. A
  conflict recorded by the old behavior clears on the next `sync`. A table test
  pins that no gated move is declined inside the strict gate's allowed statuses.
