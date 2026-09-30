## Changed

- `complete --resolution done` from `review` refuses without
  `refined-outcome.md` unless `--force`:
  - the store's `complete` checks it (so the web app is covered), and so does
    the CLI before a worktree item's merge-back, reading the branch's copy;
  - the message (`refined_outcome_missing`) names `tcw work path <slug>` and
    any stray folder holding files;
  - completing from `active`, discards and epics closed from `backlog` are
    unaffected.
- Folders printed after `new`, `start`, `submit`, `rework` and `complete` are
  relative to the current directory, or absolute outside it (`_shown`), so
  `start kid/<slug>` from a parent names a folder that exists.
- The `implement` and `verify` stage prompts, and the skill's copies of them,
  say to write in the item's folder wherever it currently lives
  (`tcw work path <slug>`).

## Fixed

- `tcw validate` reports one slug held by two item folders, naming both,
  instead of raising `MultipleMatch`; the web app's per-item validation after
  a write returns it as a problem, not "validation could not complete".
- `tcw validate` reports a stray folder: named like an item or tombstone, with
  no `state.yaml`, not the item's own folder, and holding a file other than
  `.DS_Store`. `complete` warns about its own slug's.

## Internal

- `FsWorkStore.stray_folders(slug=None)` and `duplicate_slugs()`, with
  defaults on `WorkStore` that report nothing; `check`'s per-item checks moved
  into `_item_problems`.
