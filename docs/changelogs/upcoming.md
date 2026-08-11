# Upcoming

Developer changelog for the next version. Technical and precise; grouped by
category.

## Added

- Configurable filesystem work-store roots, external-store init flags, physical
  root collision validation, and claimant/takeover metadata.
- Added `tcw taxonomy path`, `tcw capabilities path`, no-argument
  `tcw work path`, and `tcw work inbox path`, each printing its filesystem
  adapter's absolute resolved root with exact path-only stdout.

## Changed

- `FsWorkStore` now separates the owning node, work root, and work-store Git
  root; work reads, writes, validation, and transition commits use the configured
  store while hooks and code worktrees remain attached to the code node.
- `tcw work path [<slug>]` now makes the slug optional while preserving existing
  item resolution; `path` is reserved in taxonomy and capabilities command
  dispatch, with explicit `show path` retained for same-named objects.
