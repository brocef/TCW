## Fixed

- `init` reads `<component>.path` back from `tcw-config.yaml` for every
  component it scaffolds, not only `work`, and never writes it back. A tree store
  (taxonomy, capabilities) is built at `_local_root(root, path)` — where
  `resolve_store` looks, including the re-anchoring of a path that leaves a
  linked worktree. Before, `tcw taxonomy init` under a configured
  `taxonomy.path` built `docs/taxonomy`, and the "run `tcw init`" advice never
  came true.
- `init` refuses to scaffold a taxonomy or capabilities store whose
  `repository` is declared while it is absent locally, naming `tcw provision`: a
  local tree always wins in `resolve_store`, so an empty one would hide the
  declared store.
