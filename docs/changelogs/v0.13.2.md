# Upcoming

Developer changelog for the next version. Technical and precise; grouped by
category, with commit hash ranges so entries trace back to source.

## Changed

<changes starting-hash="7db1528" ending-hash="7db1528">
- Refactored `tcw.work.cli` aggregate board rendering into a registered-node
  ownership forest that nests local-parent and initiative relations, preserves
  qualified descendant slugs, and emits each item once.
- Added `-i` and `--incl-desc` aliases for `work list --include-descendants`,
  with same-node/cross-node hierarchy and alias regression tests.
</changes>

## Documentation

- Expanded the work-planning, backlog-audit, and `tcw-work` skill guidance to
  select, register, apply, remove, filter, and validate project-scoped tags.
