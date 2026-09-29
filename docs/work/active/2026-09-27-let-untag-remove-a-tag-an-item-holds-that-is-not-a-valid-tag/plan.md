# Plan — Let --untag remove a tag an item holds that is not a valid tag

Worked in a `--worktree` branch from `bug-run`.

## Tasks

1. **Failing tests** — `tests/test_untag_invalid_tags.py`: criteria 1–4, driving
   `tcw.cli.main` against a node whose item's `state.yaml` is written with the
   raw tags. Proof: 1 and 2 red today; 3 and 4 green today and mutation-checked
   after task 2.
2. **Code** — `tcw/work/cli.py`: drop `type=_tags` from `--untag`; in `_edit`,
   resolve each value against `current.tags` first, then `_tag_list`.
   And `tcw/store/fs.py`: `_validate_tags(tags, held=…)`, called from
   `update_work` with the item's current tags (amended at implement; see the
   spec's Notes). Proof: task 1 green; `grep -rln untag tests/` files green.
3. **Full suite.**

## Documentation Sync

- `docs/changelogs/upcoming/<slug>.md` — fires.
- `docs/release-notes/upcoming/<slug>.md` — fires.
- `skills/work/SKILL.md` / references, `docs/guide/work.md` — evaluate where
  `--untag` is described (`grep -rn untag skills docs/guide README.md`); add
  that it removes a held tag as written.
- Others do not fire.

## Verification

Re-run the reproduction with the worktree's CLI.
