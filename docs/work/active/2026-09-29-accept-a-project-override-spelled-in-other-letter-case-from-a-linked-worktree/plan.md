# Plan — Accept a project override spelled in other letter case from a linked worktree

Worktree `.worktrees/<slug>`, scratch venv re-pointed at it. Independent of the
two blocker items (different files), but run after them in this batch.

## Task 1 — Failing tests

**Creates** `tests/test_override_letter_case.py`, reusing `git`, `validate`
and `workspace` from `tests/test_worktree_sibling_nodes.py` and `linked` from
`tests/test_override_in_linked_worktree.py`, as that file does. A module-level
skip when the disk is case-sensitive (probe: a temp folder found under its
swapped-case name). Tests for acceptance criteria 1-5; 1, 2, 4, 5 committed
`xfail(strict=True)`, 3 must pass today.

## Task 2 — `_below` and the four call sites

**Modifies** `tcw/store/project.py`, `tcw/store/fs.py`.

- `project.py`: `_below(path, root) -> Path | None` as the spec's Design
  describes; `_locator_path` Rule 1 and `_worktree_copy` Rule 2 rewritten over
  it. *(The `between` loop's `is_relative_to(top)` was left as text: `copy`
  is built as `top / under_main`, so its spelling is `top`'s and the text
  comparison is exact.)*
- `fs.py`: `anchor_configured_path` and `worktree_node_root` use it (imported
  from `tcw.store.project`, which `fs.py` already imports from).
- Remove the `xfail` marks. **Proves** criteria 1-5.

## Task 3 — Documentation Sync

- Changelog and release-note entries.
- `docs/guide/multi-repo.md` [Guide-Topic-Change]: the override section — one
  sentence that letter case does not matter on a disk that ignores it.
- The capability describing overrides (grep `TCW_PROJECT_` under
  `docs/capabilities/`), and the item's `capabilities.yaml`.
- `skills/configure/references/projects.md` [Configuration-Key-Change]: the
  `TCW_PROJECT_<ID>` section, same sentence — the variable's meaning is
  clarified, not changed.

## Task 4 — Full suite

Bare `pytest`. **Proves** criterion 6.

## Verification

- By hand: a scratch repository with a linked worktree, the override spelled in
  upper case, `tcw validate` and `tcw work nodes` from the worktree.
