# Spec — Accept a project override spelled in other letter case from a linked worktree

## Capability changes

- **changed:** the capability covering `TCW_PROJECT_<ID>` overrides in a linked
  worktree (found in Task 3 of the plan by grep for `TCW_PROJECT_` under
  `docs/capabilities/`) — a spelling differing only in letter case is the same
  folder.

## Problem

In a linked worktree, `FsProjectRegistry` maps paths that point into the
primary checkout onto the worktree's own copy, with two rules in
`tcw/store/project.py`:

- **Rule 1** (`_locator_path`, lines 731-753): a relative locator that escapes
  the worktree is re-anchored under the main checkout. It decides with
  `source_dir.is_relative_to(top)`, `resolved.parent.is_relative_to(top)` and
  `source_dir.relative_to(top)`.
- **Rule 2** (`_worktree_copy`, lines 755-784): a config path under the main
  checkout becomes this worktree's copy. It decides with
  `resolved.is_relative_to(main)`, `resolved.is_relative_to(top)` and
  `resolved.relative_to(main)`.

`top` and `main` come from git (`_probe_worktree`, lines 114-130) in git's
spelling. All six calls compare **text**. On a case-insensitive disk an
override spelled `.../APP/pkg-b` names the folder git calls `.../app/pkg-b`, but
`Path.resolve()` keeps the given spelling, so neither rule recognises it: the
overridden node's `..` locators land on `APP/…`, are not mapped into the
worktree, and the graph holds each primary-checkout node a second time —
duplicate ids and reciprocity failures. `_canonical` (lines 786-797) already
compares folders by `(st_dev, st_ino)` for the graph's keys; these two rules do
not.

Sweep (every `is_relative_to` / `relative_to` in `project.py` and `fs.py`):
two more compare a path against git's spelling of a worktree root, and share
the defect when the *working directory* is typed in other letter case:

- `anchor_configured_path` (`fs.py:1775-1809`) re-anchors a component store's
  configured path that escapes a linked worktree, with
  `node_root.is_relative_to(top)`, `resolved.is_relative_to(top)` and
  `node_root.relative_to(top)`; a case-variant `node_root` is left
  un-anchored, silently pointing the store at the wrong place.
- `worktree_node_root` (`fs.py:956-974`) computes where a node sits inside an
  item's worktree with `node_root.resolve().relative_to(top.resolve())`, which
  raises `ValueError` for a case-variant `node_root`.

`_same_repository` (`project.py:174`) compares two paths that both come from
git, so their spellings agree; left alone. The remaining hits compare paths
TCW built from the same root, and are not affected.

## Goals

1. From a linked worktree, an override naming the primary checkout's copy of a
   project in any letter case behaves exactly as the same override in git's
   spelling: `tcw validate` exits 0 and prints the same warning the previous
   item added, naming the worktree's copy.
2. Rule 1 and Rule 2, `anchor_configured_path` and `worktree_node_root`
   decide "inside this folder" and "the part below it" by folder identity, not
   text.

## Non-goals

- Case-sensitive disks: two spellings there are two folders, and nothing
  changes.
- Normalising the spelling TCW prints; messages keep the path they were given.

## Design

One private helper in `project.py`, `_below(path, root) -> Path | None`: the
part of `path` below `root` when `path` is `root` or inside it, else `None`.
Text first (`path.relative_to(root)` when `path.is_relative_to(root)`); failing
that, it walks `path` and its parents comparing each folder's
`(st_dev, st_ino)` with `root`'s, and returns the remainder below the one that
matches. A folder that cannot be read is skipped; a filesystem that reports no
inode numbers falls back to the text answer, as `_canonical` does. Rules 1 and 2
use it for all six comparisons, and `fs.py` imports it for
`anchor_configured_path` and `worktree_node_root`.

Filesystem-adapter private, as the rest of worktree handling is (the module
already says so): the registry interface is unchanged. Litmus: not an
operation — nothing for the model.

## Acceptance criteria

The workspace of `tests/test_worktree_sibling_nodes.py` (`app` with `pkg-a`,
`pkg-b`), a linked worktree `app/.worktrees/feature`. Case tests run only where
the disk ignores letter case (skipped otherwise).

1. `TCW_PROJECT_PKG_B` set to the primary checkout's `pkg-b` spelled with
   `app` as `APP`: `tcw validate` in the worktree's `pkg-a` exits 0, with no
   `duplicate` and no `nonreciprocal` in its output, and the same warning line
   as for the git spelling.
2. The same with the whole path upper-cased.
3. From the primary checkout, the case-variant override behaves as the git
   spelling does (exit 0, no warning).
4. `anchor_configured_path(node_root, value)`, with `node_root` the worktree's
   `pkg-a` spelled with `APP` and `value` escaping the worktree, returns the
   same folder as with git's spelling.
5. `worktree_node_root(node_root, ".worktrees/x")` with a case-variant
   `node_root` returns a path, not a `ValueError`, naming the same folder as
   with git's spelling.
6. The existing tests in `tests/test_override_in_linked_worktree.py`,
   `tests/test_worktree_sibling_nodes.py` and `tests/test_project_graph_paths.py`
   pass unchanged; the full suite passes as CI runs it.

## Risks

- **Cost.** The identity walk runs only when the text comparison fails, and
  stats at most one folder per path component.
- **Symlinks.** `stat` follows them, so a symlink to the main checkout compares
  equal to it. Paths here are already `.resolve()`d, which resolves symlinks,
  so this adds nothing new.
