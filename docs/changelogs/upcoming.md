# Upcoming

Developer changelog for the next version. Technical and precise; grouped by
category.

### Fixed

- `init` (`tcw work init`, `tcw init`) no longer writes back a `work.path` it read
  from `tcw-config.yaml` when no path was given: `./store` now stays `./store`
  instead of becoming `store`, and `~/store` is no longer expanded into an
  absolute home-directory path in a committed file. A `~name` naming no user (in
  `work.path` or `--path`) is reported as `tcw init: …` instead of a traceback.

### Fixed

- `tcw validate` finds the taxonomy and capabilities stores at their resolved
  roots (`_tree_roots`) instead of testing for `docs/<component>`: a store moved
  by `<c>.path` or declared by `<c>.repository` is now YAML-scanned, link-checked
  and component-checked. Presence is one rule, `tree_store_present` in
  `tcw/store/fs.py` (default folder, or `path`/`repository` set), shared with
  `FsCapabilitiesStore._taxonomy`, so capability Subject/Feature references are
  now checked — on write and in `check` — against a moved taxonomy.
- `tcw validate` no longer crashes when `taxonomy.path` points nowhere while
  `docs/capabilities` exists: `_run_check` reports a `ValueError` raised inside
  `check()` as a problem.
- Removed the stopgap that opened unchecked tree stores after the component
  checks; only its YAML-problem half remains, so a leftover pre-2.5.0 store
  config is still reported when a YAML problem skips the component checks.
