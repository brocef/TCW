# Plan — Warn when a project override names the primary checkout's copy from a linked worktree

## Tasks

1. **Tests first.** Add `tests/test_override_in_linked_worktree.py`, with
   criteria 1 to 3. Criterion 1 should fail against the current code;
   criteria 2 and 3 should pass both before and after.
2. **Code.**
   - `ProjectOverride.warning` in `tcw/store/base.py`.
   - Filling it in, in `_reconcile_overrides` in `tcw/store/project.py`.
   - Printing it in `tcw validate` in `tcw/cli.py`.
3. **Mutation check.** Drop the id comparison and confirm criterion 3 or a
   different-id case goes red. Drop the warning and confirm criterion 1 goes
   red.
4. **Full suite.**

## Documentation Sync

- `docs/guide/multi-repo.md`: the override sentence (around line 172) says
  `validate` warns in this case.
- `docs/changelogs/upcoming/<slug>.md` and `docs/release-notes/upcoming/<slug>.md`.
- `skills/configure/references/` (Configuration-Key-Change): not triggered.
  The variable's meaning is unchanged. Checked below.

## Verification

- A hands-on run of `tcw validate` on a scratch worktree layout, with the
  override set.
