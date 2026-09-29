## Fixes

- `tcw capabilities check` now checks the references in a local override of an
  inherited capability — a `Subject` or `Feature` naming a term that does not
  exist, a `Blocked by` naming a missing capability — as it already did for your
  own capabilities. A project whose overrides already hold such a reference will
  see `check` (and `tcw validate`) report it after upgrading.
- `tcw taxonomy rm` no longer removes a term that a local override still names.
