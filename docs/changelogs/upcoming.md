# Upcoming

Developer changelog for the next version. Technical and precise; grouped by
category, with commit hash ranges so entries trace back to source.

## Nested work items (`7c73f1f..8b13ed5`)

### Added
- `tcw work new "<title>" --parent <slug>` creates a child work item nested
  inside the parent item's folder.
- `tcw work list` renders children indented (two spaces per depth) under their
  parent, preserving board order within each sibling group; `tcw work show`
  prints a `parent:` line.

### Changed
- `WorkItem` gains a `parent` field (the parent's slug; `""` == top-level) — an
  abstract node relation. `WorkStore.create` gains a `parent` parameter.
- `FsWorkStore` discovery is now `state.yaml`-keyed and depth-agnostic: `_find`
  and `query` walk the tree (`rglob state.yaml`) instead of assuming
  `root/{status}/{slug}` one level deep. Status is derived from the first path
  component under `docs/work/`; the parent slug is derived from directory
  nesting (the FS realization of the node relation). Transitions still `git mv`
  the item folder — a parent carries its nested children; a child transitioning
  on its own de-nests to top level.

### Internal
- New `FsWorkStore` helpers `_item_dirs`/`_status_of`/`_parent_slug` and a shared
  `_item_from_dir` builder used by both `get` and `query`.
- Tests that relied on empty status sub-folders being items now seed a
  `state.yaml` marker (discovery is `state.yaml`-keyed).
