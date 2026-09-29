# Plan — Close two strict-mode gaps left by the unfollowable-move gate

## Tasks

1. **Failing tests** — in `tests/test_tracker_strict_gate.py` beside the
   existing catch-up tests; `test_a_catch_up_binding_is_walked_not_refused`
   is replaced by criterion 3's test (its expectation is what this item
   changes). Criteria 1–2 red today; 4 green today and mutation-checked.
2. **Code** — `tcw/tracker/sync.py` (`needs_claim`, `deliver`'s `resolving`,
   `authorize`).
3. **Full suite.**

## Documentation Sync

- `docs/guide/jira.md` [Tracker-Change]: strict mode's `complete` row — a
  legacy catch-up binding is moved one step at a time.
- `docs/changelogs/upcoming/<slug>.md`, `docs/release-notes/upcoming/<slug>.md`.
- Not firing: README, skills, configure references.

## Verification

Each criterion by its test (the tracker is a fake; no live Jira in this run).
