# Spec — Descendant epic display and tag workflows

## Capability changes

- `work/view-the-board`: descendant aggregation presents initiative ownership as
  a hierarchy and accepts shorter aliases for the aggregation flag.
- `work/tag-a-work-item`: agent planning and backlog-audit workflows actively
  maintain the project's registered tag vocabulary and item classifications.

## Current state

`tcw work list --include-descendants` renders each registered node independently.
The local renderer only nests literal `parent` children, so an item carrying
`initiative: <epic-slug>` remains a root row even when its epic is visible in the
aggregate board.

The CLI already implements the complete tag-management surface:
`tcw work tags add|rm|list`, `new --tag`, and `edit --tag|--untag`. The missing
work is agent guidance, not another command.

## Behavior

### Aggregate epic hierarchy

Build the descendant board from all visible items before rendering node groups.
For each item, choose its visible owner in this order:

1. its local nested `parent`, when that parent is visible;
2. its `initiative` epic, resolved first locally and then through registered
   ancestors, when that epic is visible.

Render an owned item recursively beneath its owner with two-space indentation.
A descendant-owned row keeps its canonical `<project-id>/` prefix. Emit each
item once: an initiative child shown under an ancestor epic is not repeated as a
root in its own node group. Preserve current node header order, board ordering,
status/tag filters, and local-list behavior.

### Flag aliases

The `list` parser accepts `-i`, `--incl-desc`, and `--include-descendants` as
equivalent spellings of the same boolean option.

### Tag guidance

- The planning prompt inventories registered tags, chooses applicable tags,
  registers a genuinely useful missing tag with `tcw work tags add`, and applies
  tags at `new` time or via `edit` for an existing item.
- The backlog audit evaluates tag relevance alongside other item hygiene. Its
  report includes exact `tags add`, `edit --tag`, and `edit --untag` commands;
  mutations still require user approval under the audit's existing safety rule.
- The `tcw-work` skill explains tags as a project-scoped, registered vocabulary
  for classification/filtering and documents registration, application,
  removal, filtering, and validation behavior.

## Documentation Sync

This changes public CLI behavior and code. Update `README.md`, user release notes,
developer changelog, the `work/view-the-board` and `work/tag-a-work-item`
capability descriptions, and the driving `tcw-work` skill.

## Acceptance criteria

- Aggregate list tests cover same-node and descendant initiative children,
  qualified indentation, non-duplication, and all flag spellings.
- Existing local nested-parent rendering and descendant filters remain green.
- Prompt-command tests or deterministic text assertions cover the new tag duties.
- Full tests, `tcw capabilities check`, `tcw validate`, and `git diff --check`
  pass before the patch release is cut.
