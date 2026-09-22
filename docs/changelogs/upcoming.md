# Upcoming

Developer changelog for the next version. Technical and precise; grouped by
category.

### Changed

- `parse_tracker_config` (`tcw/store/base.py`) requires `exclusive-claim-transition`
  when `strict` is true, reported as the new module-level
  `STRICT_NEEDS_EXCLUSIVE_CLAIM` problem. Only an absent key triggers it: a key
  written as `null` or blank keeps its existing single `expected a non-empty
  string` problem. The problem names a key nobody wrote, so under inheritance it is
  attributed to the node being validated even when `strict` came from an ancestor.

### Internal

- Every strict test fixture now sets `exclusive-claim-transition`, so a fixture
  broken on purpose is broken only by what it breaks. `strict_node`
  (`tests/test_tracker_strict.py`) takes it as a required `claim_transition`
  argument with no default.
- Removed `test_strict_is_reported_as_unknown_because_c4_owns_it`
  (`tests/test_tracker_config.py`): `strict` has been an accepted key since strict
  mode shipped, and the test passed only because the word appeared in the
  missing-status problems.
