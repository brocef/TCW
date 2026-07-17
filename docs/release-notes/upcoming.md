# Upcoming

User-facing release notes for the next version. Plain language — no jargon or
internal module names.

## New

- **Tag work items for filtering.** Each project can now register a set of valid
  tags (like `bug` or `tech-debt`) and apply them to work items, then filter the
  board by tag. Register tags with `tcw work tags add|rm|list`, apply them with
  `--tag` on `tcw work new` / `tcw work edit` (and `--untag` to remove), and
  filter with `tcw work list --tag <tag>` (repeat to match any). Only registered
  tags can be applied; `tcw validate` flags any item still carrying a tag that
  was later removed from the registry. The web viewer shows an item's tags and
  lets you edit them against the registered set.
