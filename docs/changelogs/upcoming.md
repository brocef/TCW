# Upcoming

Developer changelog for the next version. Technical and precise; grouped by
category.

The `v2.5.0` tag was pushed but never published: the release workflow's test job
failed, so the PyPI upload never ran. `v2.5.1` is the first published release
carrying everything listed under `v2.5.0`.

### Fixed

- `tests/test_tracker_cli.py`'s `node` fixture sets `TCW_WORK_OWNER`.
  `test_an_owed_item_can_still_be_started` and
  `test_one_owed_item_does_not_break_lifecycle_moves_on_every_other_item` run
  `tcw work start`, which needs a claimant and otherwise falls back to the git
  identity. The CI runner has none, so both failed there and passed locally.
- `docs/release-notes/v2.5.0.md` linked #43 under the wrong repository.

### Added

- `work.tracker.pre-backlog`: tracker status → transition name to
  `statuses.backlog`, for statuses a workflow puts before its backlog.
  `TrackerConfig.pre_backlog`, parsed by `_parse_tracker_pre_backlog`, which
  fails closed on a non-mapping, blank names, a status listed twice (normalized),
  a status also mapped under `statuses`, and a missing `statuses.backlog`.
  `pre_backlog_entry` is the one lookup deciding whether a status is one of them.
- `intake.leave_pre_backlog`, called first by `intake.claim` (whose old body is
  now `_claim_from`). Applies the named transition only when the ticket's status is
  a `pre-backlog` key and the ticket is unassigned or the caller's; refuses before
  sending unless the transition is offered once and leads to `statuses.backlog`;
  re-reads the ticket and hands the claim that fresh read. New claim rows `0a`
  (refused before sending), `0b` (landed elsewhere), `0d` (the tracker refused it),
  `0f` (uncertain, not arrived) and `0-read` (sent, not read back).
- `ClaimOutcome.left_status`, and the same attribute on a `TrackerError` raised
  after the step, so every caller reports that the ticket left triage;
  `intake.moved_out` words it.
- `intake.pre_backlog_hint`: the sentence naming the key, for a ticket whose
  status is mapped nowhere.

### Changed

- Row `1f`'s refusal, `deliver`'s "claimed …, but it is in …" refusal (only when
  the claim applied no transition), and `tracker import` of a row-`1e` ticket (as a
  warning) name `work.tracker.pre-backlog` when the status is mapped nowhere.
- `deliver` records rows `0-read` and `0f` as `pending`.
- `_strict_claim`, `_tracker_import` and `deliver` print the moved-out sentence on
  success, refusal and a raised error; a strict refusal after the step says to run
  `start` again, since it writes no sync record. `tracker show`/`inbox show` add a
  note for a ticket in a `pre-backlog` status.

### Internal

- `tests/test_tracker_pre_backlog.py`: the setting, the step against the fake
  Jira, and every caller.
