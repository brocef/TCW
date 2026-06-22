# Upcoming

Developer changelog for the next version. Technical and precise; grouped by
category, with commit hash ranges so entries trace back to source.

## Added

- `tcw taxonomy extends add|rm` — write the federation `extends:` map via CLI
  instead of hand-editing `config.yaml`. New abstract `TaxonomyStore.extends_add`
  / `extends_remove` (opaque `ref`), realized by `FsTaxonomyStore` (writes
  `docs/taxonomy/config.yaml`, validates duplicate alias / unresolvable ref /
  self-reference); nested subparser in `tcw/taxonomy/cli.py` with `"extends"`
  added to `SUBCOMMANDS`. Tests in `tests/test_taxonomy.py`. (`1cbed1f`..HEAD)
- `tcw-taxonomy` skill (thin router) + per-component bootstrap sub-docs
  (`skills/{tcw-taxonomy,tcw-capabilities}/docs/init.md`) driving an agent-led
  deep-dive → draft → refine → write flow. (`1cbed1f`..HEAD)
- `/tcw-taxonomy-init` and `/tcw-capabilities-init` command routers. (`1cbed1f`..HEAD)

## Changed

- `tcw-capabilities` skill gains a gated bootstrap pointer to its `docs/init.md`.
  (`1cbed1f`..HEAD)
