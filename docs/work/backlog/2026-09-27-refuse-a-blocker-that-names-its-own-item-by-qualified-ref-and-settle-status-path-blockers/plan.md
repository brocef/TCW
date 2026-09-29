# Plan — Refuse a blocker that names its own item by qualified reference, and settle status-path blockers

## Tasks

1. **Failing tests** — `tests/test_local_qualified_blockers.py`, one per
   criterion 1–5, on a single node `pa` (`init(["work"], root, "pa")`) through
   `tcw.cli.main`. Proof: 1–4 red today; 5 green today and mutation-checked
   (make `_local_slug` answer every qualified ref → red).
2. **Code** — `tcw/store/base.py` (`_normalize_ref`, `_entry_for`,
   `_local_slug`); `tcw/store/fs.py` (`FsWorkStore._local_slug`).
3. **Full suite.**
4. File the cross-node cycle follow-up.

## Documentation Sync

- Changelog and release-note entry files — fire.
- `docs/guide/work.md` and `skills/work/references/commands.md` where
  `--blocked-by` values are described — evaluate; add the two accepted forms.
- Others do not fire.

## Verification

Re-run the reproduction with the worktree's CLI.
