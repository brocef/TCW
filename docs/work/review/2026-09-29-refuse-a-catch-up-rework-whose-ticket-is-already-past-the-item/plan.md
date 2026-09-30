# Plan — Refuse a catch-up rework whose ticket is already past the item

Worktree `.worktrees/<slug>`, scratch venv re-pointed at it.

## Task 1 — Failing tests

**Modifies** `tests/test_tracker_strict_gate.py` and `tests/test_tracker_sync.py`
(beside their existing catch-up tests), reusing `catch_up`, `legacy_catch_up`,
`bound_item`, `claimed_ticket`, `started`, `cli`, `record`, `deliver_now` and
`FakeJira`. Criteria 1-4 committed `xfail(strict=True)`; criterion 5's cases
must pass today.

## Task 2 — `catch_up_declines` and `deliver`

**Modifies** `tcw/tracker/sync.py`, the two test files.

- `catch_up_declines(statuses, ticket_status, local, expected, syncing)` beside
  `needs_claim`: the rung comparison, true only when `syncing and not expected`.
- `deliver`'s catch-up branch: if the ticket's rung is above the item's and
  `catch_up_declines` says no, skip the branch (no walk) and fall through;
  otherwise as today.
- Table test (criterion 6) over `MOVE_STATUS` and the statuses `authorize`
  allows for each move, in `tests/test_tracker_sync.py`.
- Remove the `xfail` marks. **Proves** 1-6.

## Task 3 — Documentation Sync

- Changelog and release-note entries.
- `docs/guide/jira.md` [Tracker-Change]: the passage on legacy `catch-up`
  bindings (grep `catch-up`), one sentence that lifecycle moves on them behave
  as on any binding when the ticket is where the move expects.
- The capability from the spec, and `capabilities.yaml`.
- `skills/work/references/commands.md` "Lifecycle synchronization": checked;
  updated only if it states the old behavior.

## Task 4 — Full suite

Bare `pytest`. **Proves** 7.

## Verification

The fake tracker is the only tracker available without spending on a real
site; the tests drive the real CLI against it. By hand: the rework case of
criterion 1 through the CLI in a scratch node with the fake client, reading the
output as a user would.

## Notes from implementation

- The tests went into a new file, `tests/test_tracker_catch_up_moves.py`,
  importing the helpers of `test_tracker_strict_gate.py` and
  `test_tracker_sync.py`, rather than into those files.
- Review found goal 4 held only for a rework record: a start record (from the
  old behavior, or an outage) was re-declined by every `sync`, since a
  replayed start has no window. Fixed in this item: such a `sync`, with the
  ticket held by this account above an active item and not done, ends held
  and drops the record, as the live start does.
