# Upcoming

Developer changelog for the next version. Technical and precise; grouped by
category.

The `v2.5.0` tag was pushed but never published: the release workflow's test job
failed, so the PyPI upload never ran. `v2.5.1` is the first published release
carrying everything listed under `v2.5.0`.

### Added

- `scripts/check_versions.sh`: compares the plugin manifest's version
  (`.claude-plugin/plugin.json`, else `.codex-plugin/plugin.json`) with
  `tcw --version` and, when they differ, prints both and the remedy for the side
  that is behind. Exits 0 on every path, is silent when it cannot tell, and
  abandons a `tcw --version` that has not answered within 3 seconds (a
  plain-bash deadline, killing the command's whole process group). Lives in the
  plugin rather than the CLI because a CLI-side check would be absent whenever
  the CLI is the older side.
- `scripts/session_bootstrap.sh` runs the check from an `EXIT` trap registered
  once the plugin root is known, so it runs after any install attempt and on
  every early exit, including for a plugin root with no `tcw/__init__.py`. It is
  invoked through `bash`, so it does not depend on the executable bit.
- Every `skills/*/SKILL.md` opens with a line asking agents under any harness
  other than Claude Code to run the check once per session.
- `tests/test_check_versions.py`, and version-check cases in
  `tests/test_session_bootstrap.py` for each install branch.

### Changed

- `skills/setup/references/install.md` points at the warning;
  `skills/extras-report`'s bug skeleton asks for the plugin version.
- `test_real_editable_checkout_is_left_alone` accepts the version warning as
  its only output, since a maintainer's editable CLI can differ from the
  checkout's manifest.

### Fixed

- `tests/test_tracker_cli.py`'s `node` fixture sets `TCW_WORK_OWNER`.
  `test_an_owed_item_can_still_be_started` and
  `test_one_owed_item_does_not_break_lifecycle_moves_on_every_other_item` run
  `tcw work start`, which needs a claimant and otherwise falls back to the git
  identity. The CI runner has none, so both failed there and passed locally.
- `docs/release-notes/v2.5.0.md` linked #43 under the wrong repository.
