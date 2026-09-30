## Changed

- Creation commits its own files, as transitions do, under
  `work.auto-commit-transitions`:
  - `tcw work new` commits the item's folder, after any tracker binding filing
    wrote;
  - `inbox accept` commits the item and the entry's removal. The removal is
    committed but never staged, so a file the removal left on disk is not
    recorded back into the inbox;
  - `tracker import` and `inbox accept` of a ticket commit the item and its
    binding, after the point where a failed binding rolls the item back;
  - `escalate` and `delegate` commit the request in the receiving store's
    repository, under that store's setting. Into a store that publishes to a
    remote, the request is left staged: that remote is updated by its own
    project's commands only;
  - the web app's `POST /api/work` commits too, and logs a refused commit
    rather than failing a creation that succeeded.
- A store that publishes is refreshed before a creation writes
  (`FsWorkStore.refresh_for_creation`), as a transition is. Committing on a
  stale copy diverged it from the remote, and every later transition then
  refused. If the refresh fails, the creation still succeeds and is left staged
  with a warning, so creating works offline.
- New `FsWorkStore.commit_writes(message, *paths, removed=(), publish=True)`:
  stage, then a scoped commit, then publish. A refused commit is a warning with
  exit 0 and the files left staged, not an error, because re-running a
  creation would duplicate it. `_inbox_write` now stages its file, so with the
  switch off every creation command leaves the same, staged state.
