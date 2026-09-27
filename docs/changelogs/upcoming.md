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

- `tcw validate` finds the taxonomy and capabilities stores the way `find_node`
  does (`_tree_roots`): each is opened, reported if it will not open (a broken
  `extends` included), and checked at its resolved root when that is a
  directory. A store moved by `<c>.path` or declared by `<c>.repository` is now
  YAML-scanned, link-checked and component-checked; path mode matches resolved
  roots, falling back to `docs/<c>` for a store that will not open.
- `FsCapabilitiesStore._taxonomy` finds a moved taxonomy (`tree_store_present`:
  the default folder, or `taxonomy.path` / `taxonomy.repository` set), so
  Subject/Feature references are checked against it on write and in `check`. A
  configured taxonomy that will not open now refuses a capability write that
  needs it, and `check` reports "Subject and Feature not checked: …" once,
  beside its other problems, when a checked capability names a Subject or
  Feature — instead of skipping those references silently.
- `tcw validate` no longer crashes when `taxonomy.path` points nowhere while
  `docs/capabilities` exists: `_run_check` reports a `ValueError` raised inside
  `check()` as a problem.
- The stopgap pass after the component checks now runs only when a YAML problem
  skipped them; everything else it reported is reached by the component checks.
