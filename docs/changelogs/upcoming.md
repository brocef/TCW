# Upcoming

Developer changelog for the next version. Technical and precise; grouped by
category.

## Added

- `tcw work edit <slug> --title "<title>"` — retitle an existing work item.
  `update_work` already accepted `title` and `tcw serve` already drove it that
  way; `_edit` now passes it through, so the CLI is no longer the one surface
  that cannot rename an item. The slug is not recomputed, so existing references
  keep resolving.
- `_nonempty` argparse validator in `tcw/work/cli.py`. `--title ""` (or
  whitespace) is rejected at the parser with exit 2. Without it, `_provided`
  passes the empty string to `update_work`, which writes `state["title"] = ""` —
  a titleless item, which `create_work` explicitly refuses to create.

## Changed

- The `tcw work edit` subcommand help now reads "change an item's title,
  estimates, tags, or blocking links". It previously claimed the command changes
  blocking links, which had been incomplete since `--priority`, `--effort`,
  `--complexity`, `--initiative`, and `--tag` were added.

## Internal

- New capability `work/retitle-a-work-item`.
- Backlog maintenance: findings from the 2026-07-28 audit trial folded into
  `2026-07-03-transactional-multi-file-writes-in-the-fs-store`,
  `2026-06-22-concurrency-safe-work-claims-…`, and
  `2026-07-01-transitive-taxonomy-inheritance`. The concurrency item's assumption
  that an external work root is "the only new branching" is corrected in place —
  `FsTreeStore` derives `node_root` from `root`, and `node_root` is what git
  operations, the sentinel reader, and hook cwd key off.
