# Upcoming

Developer changelog for the next version. Technical and precise; grouped by
category.

### Changed

- `extends` moved from the per-store config files to the node's
  `tcw-config.yaml`, as `taxonomy.extends` and `capabilities.extends`, read from
  and written to the same section as that component's `path` and `repository`.
  Value shape, validation, transitivity, cycle detection and the legacy-map
  refusal are all unchanged.
- Inheritance is now a property of the **node**, not of the store directory. Two
  nodes whose `<component>.path` resolves to the same folder inherit
  independently; a shared folder carrying a mutual `extends` no longer trips the
  self-extend guard, and instead composes once locally and once under the
  sibling's namespace.
- `FsTreeStore` gained `_config_path`, `_config`, `_component_config`,
  `_write_node_config` and `_persist_extends`, hoisted from `FsWorkStore` so all
  three components share one node-config reader/writer. The write stages against
  the **node's** repository (`_write_staged(stage_root=…)`), which the tree
  stores now need for the same reason `work.tags` did.
- `FsTreeStore.__init__` reads its component's section of the node config rather
  than `root / CONFIG_NAME`, re-reading in the constructor because
  `tcw/validate.py` builds stores via `_open_at` without going through
  `resolve_store`. A non-mapping section normalizes to `{}`, matching
  `resolve_store`.
- All four `_extends_ids` refusals now name the key path
  (`…/tcw-config.yaml: taxonomy.extends`) instead of a file, including the
  project-id one, which previously raised without saying where the id came from.
- `tcw taxonomy extends add` no longer prints a hard-coded
  `docs/taxonomy/config.yaml`, which was already wrong whenever `taxonomy.path`
  pointed elsewhere.

### Removed

- `docs/taxonomy/config.yaml` and `docs/capabilities/.config.yaml` are no longer
  read, written or created. A leftover file is inert: not parsed, not reported
  by the component `check()`, not deleted. `tcw validate`'s YAML scan still
  reports one that is unparseable, which is independent of `OWNED_YAML_NAMES`.
- Both names dropped from `OWNED_YAML_NAMES`. `CONFIG_NAME` is renamed
  `LEGACY_CONFIG_NAME` and survives only to keep each store's former filename
  out of its own attachment listing.
- `_TAX_RESERVED` deleted — defined, never read.

### Fixed

- `FsWorkStore._write_tags`'s docstring claimed a node outside git "stages
  nothing rather than failing". Its own `_require_repository` makes that false
  for the default layout, and `tests/test_non_git_writes.py` pins the refusal.
  The `git_root(...) is None` fallback is reachable only when the store is in a
  repository and the node is not.

### Internal

- `tests/nodeconfig.py` — one helper for declaring `<component>.extends` in a
  fixture's node config, replacing 19 hand-written store-config writes across
  six test files.
