# Upcoming

Developer changelog for the next version. Technical and precise; grouped by
category.

### Fixed

- `find_node` now answers "no node here" (`None`) only for
  `StoreLocationUnusable`, the ladder's own "no store at this location". Any other
  `ValueError` from opening a store — an `extends` naming an unreachable project,
  a store extending itself, an empty `<component>.path`, a malformed config —
  reaches the user as `tcw: <message>` instead of "no tcw <component> node here —
  run `tcw init`", which could scaffold a second, empty store beside the real one.
