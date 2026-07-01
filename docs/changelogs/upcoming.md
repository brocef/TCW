# Upcoming

Developer changelog for the next version. Technical and precise; grouped by
category, with commit hash ranges so entries trace back to source.

## Added

<changes starting-hash="a284df8" ending-hash="a284df8">

- Added `--include-descendants` to `tcw work list`: prints the current node's
  board plus every descendant work node's board, each grouped under a `# <rel>`
  header (`# .` for the node itself, `# ./<path>` for descendants), reusing
  `--status`/`--all` per node. New FS-adapter helper
  `descendant_nodes(root)` walks the tree for `tcw-config.yaml` sentinels
  (transitive, path-sorted, skips `.git`/`.worktrees` and symlinked dirs) — a
  sentinel-based counterpart to git-root-based `child_nodes()`, so it finds
  same-repo subdir nodes that `child_nodes()` does not. `_list`'s board
  rendering was extracted into `_render_board(st, status, show_all)`; output is
  byte-for-byte unchanged when the flag is absent.

</changes>
