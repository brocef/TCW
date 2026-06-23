# Node sentinel (tcw-config.yaml) and sentinel-based node detection

Foundation (sub-project 1 of 3) for a shared documentation repo that holds
multiple TCW projects as subfolders. Full design in `spec.md`.

## Product changes

- A node is now declared by a `tcw-config.yaml` sentinel, not by being a git
  work-tree root. A single git repo can hold many nodes as subfolders.
- `tcw init` now scaffolds at the current directory (writing the sentinel),
  not at the git root — so `cd project-b && tcw init` makes `project-b/` a node.
  Re-running backfills a missing sentinel in an existing repo (the migration).
- Taxonomy `extends` inheritance now works between sibling subfolder projects in
  one repo (falls out of correct `node_root` resolution; no new code).

## Technical changes

- `tcw/store/fs.py`: new `find_node_root()` (walk up to nearest sentinel);
  `find_node()` rewired off it; `find_node` no longer calls `git_root`.
- `run_init()` scaffolds at cwd, writes/stages the sentinel, stays idempotent.
- Tests over tmp_path git repos, incl. a two-project monorepo integration test.

## Meta changes

- Migrate this repo: add its own `tcw-config.yaml` so `tcw work` keeps resolving.
- Docs sync: README, release-notes, changelog, `tcw-work` SKILL.md, AGENTS.md.
- Scope boundary: cross-node discovery (`child_nodes`/`parent_node`) stays on the
  git-repo path — that is sub-project 2.
