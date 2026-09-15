# Plan — `tcw work list --include-descendants`

Small change. Two code touch points + tests + docs. Phases 1–2 are the code;
Phase 3 (docs-sync) can run in parallel with Phase 2's tests.

## Phase 1 — Discovery helper (FS adapter)

`tcw/store/fs.py` — add `descendant_nodes(root: Path) -> list[Path]` near
`child_nodes` (~line 126):

```python
def descendant_nodes(root: Path) -> list[Path]:
    """Descendant dirs that are TCW work nodes (tcw-config.yaml + docs/work/), at
    any depth below `root`. Sentinel-based (matches find_node_root), so it finds
    plain subdirs of one repo — unlike git-root-based child_nodes(). Transitive:
    descends past found nodes so nested nodes are returned too. Skips symlinked
    dirs (cycle-safe; we don't chase symlinked trees for node discovery).
    ponytail: walks the whole tree pruning .git/.worktrees by name — the only
    sentinel-bearing noise (a --worktree checkout copies the sentinel). Prune
    more (or a real dir named .worktrees) only if it ever bites.
    """
    root = root.resolve()
    found: list[Path] = []

    def walk(d: Path) -> None:
        for child in sorted(p for p in d.iterdir()
                            if p.is_dir() and not p.is_symlink()
                            and p.name not in (".git", WORKTREES_DIR)):
            if (child / SENTINEL).is_file() and (child / "docs" / "work").is_dir():
                found.append(child)
            walk(child)                       # transitive — nested nodes count
    walk(root)
    return found
```

> Review note (local LLM): `not p.is_symlink()` prevents the symlink-cycle
> infinite recursion both reviewers flagged. `PermissionError` on an unreadable
> subdir and the discovery→render TOCTOU window are left unguarded on purpose —
> `child_nodes()` has the same exposure, and both are non-states for a
> single-user work repo (see spec Risks). Revisit only if they bite.

- Placed after `WORKTREES_DIR` is defined? No — `WORKTREES_DIR` is at line 159, below
  `child_nodes` (126). Either move the def next to `SENTINEL`, or define
  `descendant_nodes` **below** line 159. Simplest: put the new helper right after
  `WORKTREES_DIR`/`git_commit` (after ~line 168) so both `SENTINEL` and `WORKTREES_DIR`
  are in scope. Verify no forward-reference.

## Phase 2 — CLI wiring + rendering extraction

`tcw/work/cli.py`:

1. Import: add `descendant_nodes` to the `from tcw.store.fs import (...)` block (line 10).
2. Refactor `_list` (line 184): extract the body (from `items = st.board(...)` through the
   root-emit loop) into a module-level helper:

   ```python
   def _render_board(st, status, show_all):
       items = st.board(status=status)
       if status is None and not show_all:
           items = [i for i in items if i.status != "completed"]
       # ... existing present/by_parent/stages/emit logic verbatim ...
   ```

   `stages()` closes over `st` — keep it nested inside `_render_board` (still has `st`).

3. New `_list`:

   ```python
   def _list(args):
       st = _store()
       if st is None:
           return 1
       if not args.include_descendants:
           _render_board(st, args.status, args.all)
           return 0
       node = st.node_root.resolve()          # resolve: descendant_nodes returns
       roots = [node, *descendant_nodes(node)]   # resolved paths → relative_to works
       for i, root in enumerate(roots):
           rel = "." if root == node else f"./{root.relative_to(node)}"
           if i:
               print()                         # blank line between groups
           print(f"# {rel}")
           _render_board(FsWorkStore.open(root), args.status, args.all)
       return 0
   ```

   (`st.node_root` is already used elsewhere in this file, e.g. `_start`.)

4. Subparser (line 421, `pl`): add
   `pl.add_argument("--include-descendants", action="store_true",
   help="also list every descendant work node's board, grouped by node")`.

## Phase 3 — Tests

`tests/test_work.py` — add a small cluster (reuse the `node()` helper; build children with
`init(["work"], root / "Project-A")` etc.):

- `test_list_include_descendants_groups_by_node` — root + two same-repo subdir nodes each
  with one item; assert headers `# .`, `# ./Project-A`, `# ./Project-B` appear in order and
  each node's slug shows under its own header. **Guards AC 1, 2, 7.**
- `test_list_include_descendants_skips_own_worktree` — create `<root>/.worktrees/x/` with a
  `tcw-config.yaml` + `docs/work/`; assert it is not reported. **Guards AC 4.**
- `test_list_include_descendants_nested` — a node under a node; assert the nested one is its
  own group. **Guards AC 5.**
- `test_list_without_flag_unchanged` — assert no `#` header when the flag is absent. **Guards AC 6.**
- (Optional) `test_descendant_nodes_sentinel_based` in `tests/test_store_nodes.py` — a
  same-repo subdir node is returned by `descendant_nodes` though absent from
  `child_nodes`. **Guards AC 2** at the unit level.
- `test_descendant_nodes_skips_symlink_cycle` in `tests/test_store_nodes.py` — a dir
  containing a symlink back to an ancestor terminates (no `RecursionError`) and the symlink
  is not followed. **Guards the `not p.is_symlink()` clause.**

Verification commands:

```
python -m pytest tests/test_work.py tests/test_store_nodes.py -q
python -m pytest -q          # full suite — nothing else should move
# manual smoke:
#   in a temp repo with Project-A/Project-B sentinel subdirs:
#   tcw work list --include-descendants
```

## Phase 4 — Documentation sync (parallel with Phase 3)

Run the `documentation-sync` skill; expected triggers:

- **`README.md`** [Public-API] — the `tcw work list` block (~line 295) gains
  `tcw work list --include-descendants`; the multi-project section (~line 176) references it.
- **`skills/tcw-work/SKILL.md`** [Skill-Driven-Component] — the `list` quick-reference row
  notes `--include-descendants` (aggregate descendant node boards).
- **`docs/capabilities/work.md`** `work#view-the-board` — at completion, append the flag to the
  body wording (via the `capabilities.yaml` `changed` back-pointer; status stays `Supported`).
- **`docs/changelogs/upcoming.md`** [Any-Code-Change] — Added: `--include-descendants`; new
  `descendant_nodes` FS helper. Include commit range at completion.
- **`docs/release-notes/upcoming.md`** [Public-API] — plain-language "see all your nested
  projects' work in one command" note.

## Lifecycle / commit notes

- `tcw work start <slug>` is the first implementation commit (commit the committed
  `spec.md`/`plan.md`/`capabilities.yaml` with the backlog→active move) before any code edit.
- At completion: reconcile `work#view-the-board` wording, evaluate doc-sync triggers, decide
  version bump (patch — additive flag), then `tcw work complete --resolution done --confirm`.

## Parallelization

- Phase 1 and the `--include-descendants` argparse line of Phase 2 are independent of each
  other but tiny; do sequentially.
- Phase 3 (tests) and Phase 4 (docs) are independent once Phases 1–2 land.
