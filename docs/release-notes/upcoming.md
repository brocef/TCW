# Upcoming

User-facing release notes for the next version. Plain language — no jargon or
internal module names.

## Added

- **Effort and complexity estimates on work items.** You can now tag a work item
  with an effort level and a complexity level — each one of `low`, `medium`,
  `high`, or `very-high`. Both are optional. Set them when you create an item
  (`tcw work new "…" --effort high --complexity low`) or later
  (`tcw work edit <slug> --effort medium`), and see them with `tcw work show`.
  They're estimation signals only and don't change how the board is ordered.
