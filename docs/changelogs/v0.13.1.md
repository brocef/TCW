# Upcoming

Developer changelog for the next version. Technical and precise; grouped by
category, with commit hash ranges so entries trace back to source.

## Fixed

<changes starting-hash="9ed021e" ending-hash="9ed021e">
- `tcw.work.recursion.delegate` now resolves the current node's registered
  project ID for inbox `from:` metadata instead of hard-coding `"."`.
- Updated delegation regression tests to enforce stable project IDs across
  direct and sibling-project fixtures.
</changes>
