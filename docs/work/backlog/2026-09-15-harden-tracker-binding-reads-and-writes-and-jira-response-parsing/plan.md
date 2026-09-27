# Plan: harden tracker binding reads and Jira response parsing

## Tasks

1. **Tests first** in `tests/test_tracker_hardening.py`: criteria 1-4, using the
   existing fake Jira (`tests/test_tracker_strict.py`'s `FakeJira` pattern) for
   the commands and a stub `_request` for the client shapes.
2. **Store**: `read_sidecar` in `tcw/store/fs.py`; docstring in `base.py`.
3. **Binding**: `binding_of` in `tcw/tracker/intake.py`.
4. **Client**: `_json` and per-operation checks in `tcw/tracker/jira.py`.
5. **Commands**: the deletion guard in `_tracker_link`/`_tracker_create`; the
   merge-back hint in `_complete`; drop the dead claim fields.

## Documentation Sync

- Changelog and release notes.
- `skills/work/references/commands.md` and `docs/guide/jira.md`: check what
  they say about an unreadable binding and a failed merge-back.

## Verification

Hands-on with the fake Jira from the tests: a folder `tracker.yaml` through
`link`/`unlink`/`drop`; a merge-back blocked by another item's staged file.
