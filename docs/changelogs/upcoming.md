# Upcoming

Developer changelog for the next version. Technical and precise; grouped by
category.

### Fixed

- `find_node` now answers "no node here" (`None`) only for
  `StoreLocationUnusable`, the ladder's own "no store at this location". Any other
  `ValueError` from opening a store — an `extends` naming an unreachable project,
  a store extending itself, a malformed `extends` list, an empty
  `<component>.path` — reaches the user as `tcw: <message>` instead of "no tcw
  <component> node here — run `tcw init`", which could scaffold a second, empty
  store beside the real one. One exit code changes with it: `tcw work procedure
  prompt` in a node whose `work.path` is empty or not a string now fails with
  that error (exit 1) instead of printing TCW's built-in text.
