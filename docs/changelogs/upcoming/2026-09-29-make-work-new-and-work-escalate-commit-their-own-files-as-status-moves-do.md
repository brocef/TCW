## Changed

- Creation commits its own files, as transitions do, under
  `work.auto-commit-transitions`:
  - `tcw work new` commits the item's folder (after any tracker binding filing
    wrote);
  - `inbox accept` commits the item and the entry's removal;
  - `escalate` and `delegate` commit the request in the receiving store's
    repository, under that store's setting;
  - the web app's `POST /api/work` commits too.
  New `FsWorkStore.commit_writes(message, *paths)` (stage, then a scoped
  commit, then publish for a provisioned store) and `inbox_source(ref)`. A
  refused commit is a warning with exit 0 and the files left staged, not an
  error: re-running a creation would duplicate it. `_inbox_write` now stages its
  file, so with the switch off all four commands leave the same, staged state.
