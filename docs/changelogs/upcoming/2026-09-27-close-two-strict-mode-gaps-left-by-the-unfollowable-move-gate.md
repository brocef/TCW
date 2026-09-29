## Fixed

- Strict mode's gate (`sync.authorize`) and `deliver` share one rule for
  whether a move needs the ticket held (`sync.needs_claim`), so a completion on
  a legacy `catch-up` binding whose ticket someone else holds is refused before
  the item moves instead of completing it and recording a conflict.
- The gate refuses a move whose `catch-up` walk is more than one rung, naming
  the statuses in between and asking for one step at a time; it used to skip
  the followability check there, so a workflow broken part-way completed the
  item and left the ticket behind with a `conflicting` record.
