# Upcoming

Developer changelog for the next version. Technical and precise; grouped by
category, with commit hash ranges so entries trace back to source.

## Fixed

- `descendant_nodes()` (the `tcw work list --include-descendants` / `tcw serve`
  scan) no longer stat-walks gitignored build output. It now prunes each repo's
  own gitignored subtrees (`git ls-files -oi --directory`, one call per repo
  boundary) — Pods / `build/` / `.venv` / `target/` that can't hold a committed
  node. Pruning is deliberately **per-repo**: the orchestrator pattern gitignores
  its child *repos* from the parent, so a nested repo boundary is crossed (never
  pruned) and re-evaluated against its own ignores. On a 4-child orchestrator this
  roughly halved the scan; a naive top-level prune would have wrongly dropped every
  gitignored child node. New tests cover the ignored-tree and gitignored-child-repo
  cases. (`tcw/store/fs.py`, `tests/test_store_nodes.py`)
