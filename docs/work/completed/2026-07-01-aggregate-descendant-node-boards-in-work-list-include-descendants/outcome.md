# Outcome — `tcw work list --include-descendants`

Work completed successfully. Implemented per `plan.md`; all tests green; docs synced.
Awaiting user verification before `tcw work complete`.

## What changed

- **`tcw/store/fs.py`** — new `descendant_nodes(root)`: sentinel-based (`tcw-config.yaml`
  + `docs/work/`), transitive, path-sorted, depth-first. Skips `.git`, `.worktrees`, and
  symlinked dirs (cycle-safe). Placed beside `child_nodes`/`parent_node`. This is the
  sentinel counterpart to git-root-based `child_nodes()` — it finds same-repo subdir
  nodes that `child_nodes()` cannot.
- **`tcw/work/cli.py`** — extracted the board rendering into `_render_board(st, status,
  show_all)` (logic verbatim); `_list` now loops `[node, *descendant_nodes(node)]` printing
  a `# <rel>` header per node (`# .` / `# ./<path>`, relative to the resolved node root)
  when `--include-descendants` is passed, and is byte-for-byte unchanged without it. Added
  the `--include-descendants` argparse flag and the `descendant_nodes` import.
- **Tests** — `tests/test_store_nodes.py`: `descendant_nodes` sentinel-vs-`child_nodes`,
  transitive+sorted, skips worktrees/.git, skips symlink cycle. `tests/test_work.py`:
  CLI grouping by node, skips own `.worktrees`, nested node as its own group, no headers
  without the flag. Added a `subnode()` helper.
- **Docs** — README (`tcw work list` example + board prose + multi-project section),
  `skills/tcw-work/SKILL.md` (quick-ref row), `docs/changelogs/upcoming.md` (Added, hash
  `a284df8`), `docs/release-notes/upcoming.md` (plain-language note).

## Verification performed

- `python -m pytest -q` → **228 passed** (was 220 before; +8 new tests).
- Manual multi-node smoke (temp repo, root + `Project-A` + `Project-B` sentinel subdirs +
  a non-node `plain-subdir`): output matched the requested format exactly —

  ```
  # .
  2026-07-01-root-thing | backlog | R | - | root thing

  # ./Project-A
  2026-07-01-a-feature | backlog | R | - | A feature

  # ./Project-B
  2026-07-01-b-feature | backlog | R | - | B feature
  ```

  `plain-subdir` correctly excluded.
- On this repo: `tcw work list --include-descendants` prints `# .` + the board (single
  node, no descendants); plain `tcw work list` unchanged.

## Deviations from plan

- Renamed the helper `descendant_work_nodes` → **`descendant_nodes`** (user feedback):
  pairs with `child_nodes`, and matches `child_nodes`'s convention of omitting "work".
- Placed the helper next to `parent_node` (not after `git_commit` as the plan hedged) —
  `WORKTREES_DIR` is referenced at call time, so its later definition is fine. Better cohesion.
- Left `child_nodes` untouched and did **not** create `ancestor_nodes()` — the user
  initially suggested renaming/inverting, but `child_nodes` already walks *down* and returns
  descendants (its name is accurate); a transitive-ancestors function has no consumer (YAGNI).

## Follow-up notes (not yet TCW items — closeout decision)

- **`child_nodes` clarity rename** — its name is accurate but the git-repo-boundary semantics
  can mislead; an honest rename would be `child_repo_nodes()` (touches `recursion.py` + `cli.py`).
  Offered as a possible backlog stub; not created.
- **Sibling backlog item already created:** `2026-07-01-accept-l-m-h-vh-shorthand-aliases-for-effort-complexity`
  (L/M/H/VH effort/complexity aliases), captured from the mid-session request; unplanned.
- **PermissionError / discovery→render TOCTOU** in `descendant_nodes` are deliberately
  unguarded (parity with `child_nodes`; non-states for a single-user repo) — see spec Risks.
- **Version bump** not yet cut — a `patch` fits (additive flag). Closeout decision.

## Commits

- `a284df8` — implementation + tests
- `6c95e00` — docs-sync
- (`ee092d7` — the `start` transition)
