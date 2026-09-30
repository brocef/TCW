# Plan — See a blocker cycle that runs through an item whose state.yaml cannot be read

Starts after `2026-09-29-detect-a-blocker-cycle-that-runs-across-nodes` is
merged to `main`. Worktree `.worktrees/<slug>`, scratch venv re-pointed at it.

## Task 1 — Failing tests

**Creates** `tests/test_blocker_cycles_through_unreadable_items.py`, with the
`node()`/graph helpers of `tests/test_cross_node_blocker_cycles.py` copied.
One test per acceptance criterion 1-7 (criterion 7 parametrised over its five
cases). Damage is `state.yaml` overwritten with `key: [unclosed`; the ambiguous
slug is the item's folder copied from `backlog/` into `active/`; the
interrupted claim as in the previous item's tests. Cases expected to fail today
(1-6) are committed `xfail(strict=True)`; criterion 7's must pass now.

## Task 2 — The hooks

**Modifies** `tcw/store/base.py`, `tcw/store/fs.py`.

- `WorkStore.unreadable_reason(slug)` → `None`;
  `FsWorkStore.unreadable_reason`: `_find(slug)` (catching `MultipleMatch` →
  "more than one folder holds this slug"; any other exception or no folder →
  `None`), then `_state_damage(folder / "state.yaml")`.
- `FsWorkStore.unreadable_open_items` rewritten over `unreadable_reason`,
  unchanged in output (its existing tests prove it).
- `WorkStore._item_label(store, slug)` → `slug`; `FsWorkStore._item_label`:
  `slug` when `store` has this store's key, else
  `f"{registered_project_id(self.node_root, store.node_root)}/{slug}"`, falling
  back to the slug if that raises.

## Task 3 — The walk and the one decision

**Modifies** `tcw/store/base.py`, the new test file.

- `_reaches(start, target, *, settled, unreadable: list | None = None)`: on
  `MultipleMatch` from `get`, append `(label, reason)` and continue; after a
  successful `get`, if `item.blocked_by == []` and
  `store.unreadable_reason(slug)` is set, append. Other exceptions: continue,
  as now. Never raises.
- `_refuse_blocker_walks(ref, slug, starts, settled)`: runs `_reaches` for
  each start with one shared list; any `True` → the cycle error; else a
  non-empty list → the unreadable error; else return.
- `_check_new_blocker` and the `--blocks` loop of `check_blocker_edits` call
  it. `_unreadable_refusal` gains `noun="open items"`; this caller passes
  `"items"` and `what="part of a blocking cycle with this edit"`, with the
  verb `f"add {ref} as a blocker of"`.
- Remove the `xfail` marks. **Proves** criteria 1-7.

## Task 4 — Documentation Sync

- Changelog and release-note entries [Any-Code-Change, Public-API].
- `docs/guide/work.md` [Guide-Topic-Change]: the `--blocked-by` comment block
  gains "refused while an item on the path cannot be read".
- `docs/capabilities/work/manage-blocking-relations/description.md`; the
  item's `capabilities.yaml` (`changed:`).
- Skills, README, configure references, jira guide: not triggered (checked by
  grep for "cycle" in the previous item; re-checked).

## Task 5 — Full suite

Bare `pytest`. **Proves** criterion 8.

## Verification

- By hand in a scratch graph: criterion 1's and 2's messages as a user reads
  them; `tcw validate` lists the damaged file the message points at; after
  fixing the file, the same edit is refused as a cycle (1) or accepted.
- `tcw serve`: the `PATCH` of criterion 1 answers 422 with the message.
