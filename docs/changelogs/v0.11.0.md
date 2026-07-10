# Upcoming

Developer changelog for the next version. Technical and precise; grouped by
category, with commit hash ranges so entries trace back to source.

## Unify T/C/W folder substrate + capability federation (`1977393..3f3bb7d`)

### Added
- **Capability federation** — `CapabilitiesStore.extends_add/extends_remove` and
  a `tcw capabilities extends <alias> <ref>` CLI subcommand (mirrors taxonomy),
  with a `_seen` cycle guard and `origin`/`qualified` on `Capability`. Inherited
  capabilities resolve on read through nested `FsCapabilitiesStore`s.
- **Override + body composition** — a local folder with `overrides: <id>` (bare
  or `<alias>/<id>`) is a delta merged onto an inherited capability by upstream
  id: fields partial-merge (YAML `null` clears), body =
  `prependedDocs` + (local `description.md` else upstream raw) + `appendedDocs`.
  `check` validates override targets (dangling / ambiguous / must-be-inherited),
  attachment lists, and federation cycles.
- **Stable capability ids** — every capability carries an opaque immutable `id`
  (`get_by_id`); the durable override key and future `tcw://` target.
- **Work path-input locator** — `resolve_qualified_work_ref` accepts
  `<status>/…/<slug>` (status segment validated against the item's real status;
  intermediate segments ignored; slug stays the identity).
- Migration `scripts/migrate_capabilities_to_folders.py` (dry-run default,
  `--apply`, hashlib.sha1 reproducible ids, single-heading collapse,
  equality-gated delete).

### Changed
- **Capabilities are path-addressed folders** (`meta.yaml` + `description.md`),
  matching taxonomy/work. `Capability` gains `path`/`id`/`origin`/`qualified` and
  loses `file_id`/`heading_slug`/`ref`. `Subject` is multi-valued.
- Shared folder read/write extracted into `FsTreeStore._load_node`/`_write_node`;
  `FsTaxonomyStore` rewired onto it (no behaviour change).
- `tcw capabilities add/show/list/set/check` are path-addressed; `list` shows
  origin + effective status and gains `--local-only`. Serve capability create
  route + SPA use `path`/`id`/`origin`; the create form takes a path.
- `docs/capabilities/` migrated to the folder model (38 capabilities).

### Removed
- The file+heading capability model: `CapabilityFile`, `add_entry`,
  `--folder`, `#heading`/`[state]` addressing, state-variant files
  (`with-`/`without-`), and the `errors.md`/`states.md` sidecars (all unused).

### Internal
- Capability tests migrated to the folder model; new federation test suite.
  Full suite green (497).
