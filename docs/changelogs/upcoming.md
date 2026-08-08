# Upcoming

Developer changelog for the next version. Technical and precise; grouped by
category.

## Added

- Configurable filesystem work-store roots, external-store init flags, physical
  root collision validation, and claimant/takeover metadata.

## Changed

- `FsWorkStore` now separates the owning node, work root, and work-store Git
  root; work reads, writes, validation, and transition commits use the configured
  store while hooks and code worktrees remain attached to the code node.
