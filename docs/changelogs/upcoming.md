# Upcoming

Developer changelog for the next version. Technical and precise; grouped by
category.

### Changed

- `_tracker_import` (`tcw/work/cli.py`), and so `inbox accept` of a ticket, puts
  a ticket its claim moved back to where the claim found it, once the backlog item
  and its binding are written. New `intake.put_back(client, outcome)` re-reads the
  ticket, picks the one offered transition to `outcome.claimed_from` with
  `sync.assess_move` (no named transition), applies it and reads the status back.
  It returns `(status, reason)` and never raises a tracker error. A failure is a
  `warning:` line, and the import still exits 0. The move is skipped under
  `work.tracker.strict`, whose exclusivity proof is the status the claim led to,
  and when the ticket is still in `claimed_from` (row `1e`: a ticket already held,
  which the claim does not move). That second guard also keeps a ticket already
  under way from costing extra tracker reads.

### Added

- `ClaimOutcome.claimed_from` (`tcw/tracker/intake.py`): the status `claim` found
  the ticket in, after any `pre-backlog` step, set only on a claim.
