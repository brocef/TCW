# Plan — Make tcw init honor a configured taxonomy or capabilities path

## Tasks

1. **Failing tests** — `tests/test_init_configured_tree_path.py`, criteria 1–5,
   through `tcw.cli.main` on a git-initialized scratch node; the repository
   declaration shape copied from `tests/test_store_provisioning.py`. Proof: 1–5
   red today.
2. **Code** — `tcw/store/fs.py` `init`: generalized read-back; tree bases via
   `_local_root`; the repository guard before any write.
3. **Full suite** — the provisioning, config-writer and multi-project tests are
   the ones most likely to meet the new guard.

## Documentation Sync

- Changelog and release-note entry files — fire.
- `skills/configure/references/stores.md` (where `<component>.path` and
  `repository` are described) — evaluate; say `init` scaffolds at a configured
  path and refuses a declared repository.
- `docs/guide/` page that describes `<component>.path` — evaluate.

## Verification

Re-run the reproduction with the worktree's CLI.
