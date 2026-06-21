# Plan — Nested work items

TDD throughout: red test → implement → green. One commit per task.

## Task 1 — Model: the `parent` node relation

- `base.py`: add `WorkItem.parent: str = ""`; add `parent: str | None = None` to
  the abstract `WorkStore.create` signature.
- No behavior yet — compiles, existing tests green.

## Task 2 — FS discovery + status/parent derivation (depth-agnostic)

- `fs.py` `FsWorkStore`: add `_item_dirs()` (`rglob state.yaml`), `_status_of(d)`
  (first path component), `_parent_slug(d)` (nearest `state.yaml` ancestor).
- Rewrite `_find` to walk `_item_dirs()` matching `dir.name == slug` (keep the
  `MultipleMatch` guard). Factor `_item_from_dir(d)`; have `get` and `query` use
  it. `query` filters by derived status.
- Update `test_multiple_match_resolution_error` to drop a `state.yaml` in each
  dup dir (discovery is now `state.yaml`-keyed).
- Tests: depth-agnostic `get`/`query`/`find` for a hand-placed nested item;
  node-bounded query still holds (already covered).

## Task 3 — `create(parent=…)` + nesting carried through transitions

- `fs.py` `create`: when `parent` given, resolve its folder via `_find`
  (error if absent) and create the child inside it; else `backlog/{slug}`.
- Confirm `_effect_transition`/`_delete` need no change (they `git mv`/`rm` the
  resolved folder; parent carries children, child de-nests).
- Tests: child nests under parent; `child.parent`/`child.status` correct;
  starting a parent carries the child (still nested); starting a child de-nests
  it to top level with `parent == ""`; dropping a parent removes its children.

## Task 4 — CLI: `new --parent`, `list` nesting, `show` parent

- `cli.py`: `--parent` on `new` → `st.create(..., parent=args.parent)` (map the
  ValueError to a `tcw work new:` error).
- Rewrite `_list` to a DFS tree: build `by_parent` from `board()` order, emit
  roots (parent absent from the view) then recurse, indenting per depth.
- `_print_item`: add a `parent:` line when set.
- Tests: CLI `new --parent` nests; `list` shows indented children in board
  order; unknown parent errors non-zero.

## Task 5 — Capabilities gate (product-first)

- Add `Decompose a work item` capability to `docs/capabilities/work` as
  `Missing` now; flip to `Supported` at completion.

## Task 6 — Docs sync

- `skills/tcw-work/SKILL.md`: two guidance additions —
  - a **Decompose into child items** section: encourage agents to split a large
    item into `--parent` children when scope is big or the user asks, so no one
    item is too large.
  - flesh out **orchestrator-level work + sub-project coordination**: when to
    create an `--epic` at the orchestrator node and coordinate child-node tasks
    via `delegate` / `escalate` / `--initiative` / `reconcile` — and how that
    cross-node path contrasts with intra-node `--parent` children.
  - Update the quick reference and the `description` frontmatter.
- `README.md`: document `new --parent` and list nesting.
- `docs/release-notes/upcoming.md` + `docs/changelogs/upcoming.md`: entries.
- Run `documentation-sync` to confirm nothing else fires.
