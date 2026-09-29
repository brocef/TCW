# Refuse a catch-up rework whose ticket is already past the item

From `2026-09-27-close-two-strict-mode-gaps-left-by-the-unfollowable-move-gate`
(2026-09-29): its verifier found an older problem of the same kind, where the
strict gate and `deliver` disagree.

On a binding marked `catch-up` whose ticket is in In Review, `tcw work rework`
passes the strict gate. The item then moves locally, and only afterwards does
`deliver` record a conflict ("past where its item is, so it was not moved
back"). The code before that item behaves the same way, so that item did not
cause it.

Wanted: the gate should refuse, before anything moves, any move that `deliver`
would decline to carry out. Otherwise the move should succeed with no
conflict record.
