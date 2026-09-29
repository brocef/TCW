## Fixed

- `complete` refuses while an open item's `state.yaml` cannot be read, since
  `_safe_yaml` reads it as `{}` and the item loses its `parent:` and
  `initiative:`. The parent gate (`require_nothing_open_beneath`) checks this
  board and cannot be forced; `drop` makes the same check, and the damaged item
  itself is left to `_require_readable_state`. The epic gate
  (`require_readable_slices`) also checks descendant nodes, and `--force`
  overrides it only there. `tcw work complete` now runs both through the store
  before merging a worktree branch, instead of its own copy of the check. Before this fix, a slice that was not UTF-8 let its
  epic complete, and a child with malformed YAML let its parent complete.
- New `AbstractWorkStore.unreadable_open_items()` and
  `unreadable_slice_candidates()`, both returning `[]` by default.
  `FsWorkStore._state_damage` is extracted from `_require_readable_state`.
