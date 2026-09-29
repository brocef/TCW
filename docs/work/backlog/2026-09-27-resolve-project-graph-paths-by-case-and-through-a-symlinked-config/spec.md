# Spec — Resolve project-graph paths regardless of letter case and through a symlinked config

## Capability changes

None.

## Reproduction

See `initial-request.md` (2026-09-29): a locator spelled `ROOT/kid` for a node
at `Root/kid` on macOS loads `root` twice; a node whose `tcw-config.yaml` is a
symlink to `store/tcw-config.yaml` looks for its child `kid` at `store/kid`.
Parts 3 and 4 follow `tests/test_worktree_sibling_nodes.py`'s submodule layout.

## Problem

`FsProjectRegistry` (`tcw/store/project.py`) keys nodes by resolved path text.

1. `Path.resolve()` keeps the spelling it was given, so on a case-insensitive
   disk one folder has several keys.
2. `.resolve()` of a config path follows a symlinked `tcw-config.yaml` to its
   target, and the registry then treats the target's folder as the node — so
   relative locators are read from there (`_locator_path`'s `source_dir`).
3. `_probe_worktree` recognizes a linked worktree only when the common git
   directory is named `.git`, and asks about the directory's own repository: a
   submodule inside a linked worktree is its own repository, whose main
   worktree is itself.
4. For a repository that is a submodule, the common git directory is
   `.git/modules/<name>`, so its linked worktrees are not recognized either.

**Sibling sweep** (`grep -n "resolve()" tcw/store/project.py`): the config-path
resolutions at `current`, `_config_for`, `_load_graph`, `_visit`,
`_target_path` (the provisioned-root candidate), `_locator_path` and
`_worktree_copy` — all go through the new helper.

## Goals

1. One folder spelled two ways loads once, under the first spelling met (the
   command's own node is visited first, so its spelling wins — the one every
   other module compares against).
2. A node's config is read as belonging to the folder it sits in, whether or
   not the file is a symlink.
3. `worktree_anchors` answers for a submodule node inside a linked worktree
   (the superproject's anchors).
4. `worktree_anchors` answers for a linked worktree of a repository that is
   itself a submodule.
5. Question 3 of the intake is answered in Notes; no code for it.

## Non-goals

- Case-folding path comparisons elsewhere in `tcw/` (only the registry keys
  nodes by path).
- A `TCW_PROJECT_<ID>` override (see Notes).

## Design

- `_config_file(path)`: `path.parent.resolve() / path.name` — the folder
  resolved, the file not followed. Replaces `.resolve()` on every config path
  in the registry.
- `FsProjectRegistry._canonical(config_path)`: the config path under the first
  spelling seen of its folder, keyed by the folder's `(st_dev, st_ino)`;
  unchanged when the folder cannot be read. Applied in `_visit`, to every
  `_target_path` answer, and to the current node's lookups.
- `_probe_worktree`: the main worktree from `git worktree list --porcelain`
  (its first entry; none for a bare repository) instead of assuming
  `<common>/..`. When the directory is not in a linked worktree of its own
  repository and `git rev-parse --show-superproject-working-tree` names a
  superproject, answer with the superproject's anchors.

## Abstraction litmus test

The project graph is filesystem-adapter code; `ProjectRegistry` exposes no
path operation. Nothing in the store interface changes.

## Acceptance criteria

1. On a case-insensitive disk (skipped elsewhere), a child locator spelled in
   other case than the node's folder: `tcw validate` from the root exits 0.
2. A node whose `tcw-config.yaml` is a symlink to a file elsewhere, with a
   child `kid` at `node/kid`: `tcw validate` exits 0 and `kid` is reachable.
3. The submodule layout of `tests/test_worktree_sibling_nodes.py`: `tcw
   validate` from `app-wt/lib` reports no duplicate.
4. `app` as a submodule of an outer repository, with a linked worktree
   `app-wt`: `tcw validate` from `app-wt/pkg-a` exits 0 with no duplicate.
5. The full test suite passes.

## Risks

- `git worktree list` is one more git call per registry probe; it is cached per
  directory like the current probe.
- Two spellings of one folder now print the first spelling in messages.

## Notes

- **Question 3 — redirect a `TCW_PROJECT_<ID>` override to the worktree copy?**
  Answered in this spec after consulting both advisors; see the Autonomous
  decisions in `outcome.md`.
