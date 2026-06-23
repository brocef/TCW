# Upcoming

Developer changelog for the next version. Technical and precise; grouped by
category, with commit hash ranges so entries trace back to source.

## Added (a8cb467..a8c16d1)

- `find_node_root(start)` in `tcw/store/fs.py`: walks up from `start` (or cwd)
  to the nearest directory containing a `tcw-config.yaml` file; nearest-wins so
  nested nodes resolve to the innermost. Returns `Path | None`.
- `write_sentinel(node_root)`: creates `tcw-config.yaml` at the node root if
  absent (idempotent, create-don't-stage).
- `tcw-config.yaml` node marker: a YAML stub whose existence declares a folder a
  TCW node. Detection tests existence only (`is_file()`); content is loaded
  lazily. Reserved filename at any depth — never commit one except at a node
  root.
- Multi-project subfolder support: a single git repo can now hold multiple TCW
  projects as subfolders, each with its own sentinel, `docs/` tree, and
  `tcw work` board.

## Changed (a8cb467..a8c16d1)

- `find_node(component, start)`: rewired to call `find_node_root` instead of
  `git_root`; returns the node root iff the sentinel is present **and**
  `docs/<component>/` exists. Signature and call contract unchanged.
- `tcw init` (`run_init` in `tcw/cli.py`): now scaffolds the **current
  directory** (cwd) instead of the git work-tree root; writes the
  `tcw-config.yaml` sentinel at cwd (idempotent backfill). Still refuses outside
  a git repo. Single-repo workflows are unaffected (cwd == git root at a repo
  root).
- Node-guard messages on `tcw taxonomy`, `tcw capabilities`, and `tcw work`
  commands now read: "no tcw `<component>` node here — run `tcw init` (in the
  project folder) to create one."
