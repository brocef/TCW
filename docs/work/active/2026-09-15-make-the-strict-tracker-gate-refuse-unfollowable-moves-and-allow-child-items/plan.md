# Plan: strict gate refuses unfollowable moves; import nests children

## Tasks

1. **Tests first** in `tests/test_tracker_strict_gate.py`: criteria 1-5 with the
   fake Jira workflows from `tests/tracker_fake.py`.
2. **Gate**: `authorize(…, move=, resolution=)` in `tcw/tracker/sync.py`;
   `_strict_refusal` passes them.
3. **Import**: `--parent`/`--initiative` on the `import` parser and in
   `_tracker_import`, validated before the claim.
4. **Docs**: the capability description; `skills/work/references/commands.md`
   (import's options, strict refusals); `docs/guide/jira.md` strict section;
   changelog and release notes.

## Verification

Hands-on with the fake Jira: a submit refused for a missing transition; an
import nested under a parent.
