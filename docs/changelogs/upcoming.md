# Upcoming

Developer changelog for the next version. Technical and precise; grouped by
category.

## Added

- `WorkStore.locate(slug) -> str | None` (`tcw/store/base.py`) — abstract
  locator for an item's current home, mirroring `artifact_locator`. Adapters
  realize it however fits their backing store (a filesystem: the repo-relative
  folder; a remote tracker: an issue URL or status label); it is presentation
  only and must not be parsed. `FsWorkStore.locate` (`tcw/store/fs.py`) returns
  `path(slug)` relative to `node_root`, `None` for a missing item, and the
  absolute path — rather than raising `ValueError` — for an item outside
  `node_root`.

## Changed

- `tcw work start`, `complete`, `inbox accept`, and `new` (`tcw/work/cli.py`)
  now name the item's new location, resolved through `st.locate()`; the CLI
  holds no `node_root`/`relative_to` knowledge for this. `start` prints
  `started <slug> → docs/work/active/<slug>` (worktree variant:
  `started <slug> → <loc> (worktree <wt>)`), and `complete` appends
  ` → <loc>` — a discard likewise reports its `discarded/` home. `inbox accept`
  and `new` keep their bare-slug stdout and carry the location on stderr
  (`→ now at <loc>` / `→ created at <loc>`). The suffix is omitted when
  `locate` returns `None`; exit codes and gate behavior are unchanged.
