# Plan — Tidy three tracker messages left by the binding hardening review

## Tasks

1. **Failing tests** — `tests/test_tracker_message_tidy.py`, one per criterion
   1–5, using the existing fake-tracker fixtures from `tests/test_tracker_cli.py`
   / `tests/test_tracker_strict.py` rather than new ones. Proof: each red before
   its fix; each fix mutation-checked.
2. **Code**, one commit per concern:
   - `tcw/work/cli.py` (merge-back hint) and `tcw/store/fs.py` (two `ls-tree`
     readers): `-z`, NUL split, `diff` from the repository top.
   - `tcw/tracker/jira.py` (`_payload`, `create_issue`, `_check_issue`,
     `_text`) and `tcw/tracker/create.py` (string key and id).
   - `tcw/work/cli.py` `_create_one`: a reason when binding fails.
   - `tcw/tracker/intake.py` (`binding_record`, `ever_bound`), `tcw/work/cli.py`
     `_drop`, `tcw/serve/__init__.py` drop gate.
3. **Full suite.**

## Documentation Sync

- `docs/guide/jira.md` [Tracker-Change]: the `tcw work drop` row — an unreadable
  `tracker.yaml` is refused too, and says so.
- `docs/changelogs/upcoming/<slug>.md` [Any-Code-Change]: all five.
- `docs/release-notes/upcoming/<slug>.md` [Public-API]: the user-visible ones
  (2, 3, 4, 5).
- Not firing: README, skills and configure references (no command, key or
  lifecycle change); `docs/guide/<topic>.md` (no file or key moves).

## Verification

Each criterion by its test; hands-on: criteria 4 and 5 through the real CLI in a
scratch node with a fake tracker where one exists, otherwise by the tests.
