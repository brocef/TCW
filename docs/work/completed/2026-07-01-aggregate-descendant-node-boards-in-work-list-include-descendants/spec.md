# Spec — `tcw work list --include-descendants`

## Capability changes

- **Changed:** `work#view-the-board` — `tcw work list` gains a `--include-descendants`
  flag that aggregates the current node's board with every descendant work node's
  board, grouped by node. Status stays `Supported`; body wording gains the flag at
  completion (back-pointer in `capabilities.yaml`). No new capability — this mirrors
  how `--status`/`--all` and priority-ordering already live inside `view-the-board`.
- No taxonomy Vocabulary/Feature change: "node", "board", "work item" already exist;
  `cli/host-multiple-projects-in-one-repo` already documents the multi-project model
  this feature serves.

## Problem

In the documented multi-project layout — several TCW projects as sentinel-marked
subfolders of one repo — there is no single command to see all their work at once.
You must `cd` into each project and run `tcw work list` separately. `tcw work nodes`
lists the node topology but not the items.

## Goal

`tcw work list --include-descendants` prints the current node's board followed by
each descendant work node's board, each group prefixed with a path header:

```
# .
<root node's board rows>

# ./Project-A
<Project-A's board rows>

# ./Project-B
<Project-B's board rows>
```

All other flags (`--status`, `--all`) apply uniformly to every group.

## Non-goals

- Aggregating `tcw taxonomy list` / `tcw capabilities list` (work-only for now; the
  discovery helper is generic and reusable if that is wanted later).
- Cross-*repo* federation beyond directory descent (that is cross-node-epic territory).
- A merged/interleaved single board — output stays grouped per node.
- De-duplicating slugs across nodes (slugs are node-scoped; the header disambiguates).

## Current-state findings

- `tcw/work/cli.py:184` `_list` — resolves one store via `_store()` and renders the
  board (a `by_parent` parent/child tree emitted via `emit()`). This rendering must be
  extracted so it can run per node.
- `tcw/work/cli.py:421` — the `list` subparser (`--status`, `--all`); `--include-descendants`
  is added here.
- `tcw/store/fs.py:64` `find_node_root` — the sentinel (`tcw-config.yaml`) definition of a
  node. `find_node("work", ...)` additionally requires `docs/work/`.
- `tcw/store/fs.py:102` `child_nodes` — **git-root-based** descendant discovery (a child
  must be its own git work-tree). This does **not** match the requested behavior: in the
  example, `Project-A/Project-B` are plain subdirs of one repo, so `child_nodes` would
  skip them. A new **sentinel-based** helper is needed. `child_nodes` stays as-is
  (cross-node epics depend on its git semantics).
- `tcw/store/fs.py:159` `WORKTREES_DIR = ".worktrees"` — a `--worktree` item's checkout
  carries a copy of `tcw-config.yaml`; discovery must skip it or it self-reports as a
  descendant.
- Test harness: `tests/test_work.py:10` `node()` builds a git repo + `init(["work"], root)`
  (writes sentinel + `docs/work/`); CLI tests call `main(["work", "list", ...])` under
  `monkeypatch.chdir` + `capsys`.

## Proposed behavior

### Discovery (FS adapter, `tcw/store/fs.py`)

New `descendant_nodes(root: Path) -> list[Path]`:

- Walk the directory tree under `root`, pruning `.git` and `.worktrees` by name.
- A directory is a descendant work node iff it has both a `tcw-config.yaml` file and a
  `docs/work/` dir (same test as `find_node("work")`).
- **Transitive**: keep descending past a found node so nested nodes are also returned
  (matches "descendants"). Returned depth-first, path-sorted (deterministic).
- FS-adapter-local, exactly like `child_nodes`/`find_node` (litmus test: "walk the tree
  for sentinels" has no abstract store analog).

### Rendering (CLI, `tcw/work/cli.py`)

- Extract the current per-store board rendering into a helper
  `render_board(st, status, show_all) -> None` (the existing `board()` filter + `stages()`
  + `by_parent`/`emit()` logic, unchanged).
- `_list`:
  - Without `--include-descendants`: unchanged — one `render_board` call, no header.
  - With `--include-descendants`: let `node = st.node_root`; roots = `[node, *descendant_nodes(node)]`.
    For each root, print `# <rel>` (`.` for the node itself, `./<relpath>` for descendants,
    relative to the node root), then `render_board(FsWorkStore.open(root), ...)`. Blank line
    between groups.

### Path header base

Relative to the resolved **node root** (`st.node_root`), not the literal CWD. When run
from the node root (the example) these coincide. Robust when run from a deeper subdir
(`.` unambiguously means the node the command resolved to).

### Empty nodes

A node with no matching items prints its `#` header with no rows (mirrors single-node
`list`, which prints nothing when empty). No `(no items)` sentinel line.

## Acceptance criteria

1. `tcw work list --include-descendants` from a root node with sentinel-marked subdir
   nodes `Project-A`, `Project-B` (plain subdirs of the same repo) prints three groups:
   `# .`, `# ./Project-A`, `# ./Project-B`, each with that node's own rows.
2. Descendant discovery is sentinel-based: same-repo subdir nodes are found (they are
   invisible to `child_nodes`).
3. `--status` / `--all` apply to every group identically.
4. A node's own `.worktrees/<slug>` checkout is never reported as a descendant.
5. Nested descendant nodes (a node under a node) appear as their own group.
6. Without the flag, output is byte-for-byte unchanged (no header, single board).
7. Groups are ordered root-first, then path-sorted; output is deterministic.

## Risks / dependencies

- **Whole-tree walk cost** — same known ceiling as `child_nodes` (walks `.venv`, etc.).
  Acceptable for a docs repo; prune later only if it bites. Marked with a `ponytail:` comment.
- **`.worktrees` skip is by-name** — a real project dir literally named `.worktrees`
  would be skipped. Acceptable ceiling; noted in the comment.
- **Symlink cycles** — guarded: the walk skips symlinked dirs (`not p.is_symlink()`),
  so a symlink loop cannot cause infinite recursion, and symlinked trees are not chased.
- **PermissionError on an unreadable subdir** — left unguarded on purpose. `child_nodes`
  has the identical exposure, and an unreadable dir inside your own work repo is a
  non-state; failing loudly is acceptable. Add a `try/except OSError` skip only if it
  ever bites in practice. (Surfaced by local review; deliberately deferred.)
- **Discovery→render TOCTOU** — a node deleted between discovery and `FsWorkStore.open`
  would raise mid-output. Sub-second window in an interactive single-user CLI; not
  guarded. (Surfaced by local review; deliberately deferred.)
- No dependency on other in-flight items.
