# Aggregate descendant node boards in work list (--include-descendants)

## Requested outcome

Add a `--include-descendants` flag to `tcw work list`. When passed, in addition to
the current node's board, it renders the board of every **descendant TCW work
node** (a subdirectory that is itself a TCW work root), reusing whatever other
flags were given (e.g. `--all`, `--status`) for each node's listing.

Output is grouped by node, each group prefixed with a `#` header showing the
node's path relative to the current node root (`.` for the root itself):

```
# .
<root node's board rows>

# ./Project-A
<Project-A's board rows>

# ./Project-B
<Project-B's board rows>
```

Example layout that produces the above (run from `Root-Project/`):

- `Root-Project/tcw-config.yaml`
- `Root-Project/Project-A/tcw-config.yaml`
- `Root-Project/Project-B/tcw-config.yaml`

## Product changes

- New user-facing option on `tcw work list`. Extends the existing
  `work#view-the-board` capability; pairs with `cli/host-multiple-projects-in-one-repo`.

## Technical changes

- A descendant-node discovery helper in the FS adapter (sentinel-based, unlike the
  existing git-root-based `child_nodes()`), plus grouped rendering in `tcw work list`.

## Meta changes

- None.

## Constraints & non-goals

- **Discovery is sentinel-based**, keyed on the `tcw-config.yaml` marker, so it finds
  plain subdirectories of a single git repo (the documented multi-project model) —
  not only descendants that are separate git repos. The existing `child_nodes()`
  (git-root-based, used by cross-node epics) does **not** fit and is left untouched.
- Only descendants that are **work** nodes (`tcw-config.yaml` + `docs/work/`) are listed.
- **Non-goal:** aggregating taxonomy/capabilities lists. Work-only for now; the
  discovery helper is generic enough to reuse later if wanted.
- **Non-goal:** cross-*repo* aggregation beyond simple directory descent (that is the
  cross-node-epic / `nodes` territory).
- Must not treat a node's own `.worktrees/<slug>` checkout as a descendant (it carries
  a copy of `tcw-config.yaml`).

## Decisions already made

- Flag name: `--include-descendants` (boolean).
- Header format: `# .` for the root node, `# ./<relpath>` for each descendant.
- Other flags (`--status`, `--all`) apply uniformly to every node's board.

## Open questions for spec

- Path base for headers: relative to the resolved **node root** vs the literal CWD
  (they coincide when run from the node root, as in the example). Leaning node-root.
- Descend transitively into already-found nodes (nested nodes shown too) vs stop at
  the first node found on each branch. Leaning transitive (matches "descendants").
- Empty-node presentation: header with no rows, or a `(no items)` note.
