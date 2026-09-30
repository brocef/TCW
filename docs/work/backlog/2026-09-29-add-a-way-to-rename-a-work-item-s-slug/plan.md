# Plan — Add a way to rename a work item's slug

Worked in a worktree (`start --worktree`), with a scratch venv pinned to it.
It runs after #73 in this batch order if convenient. If it lands first, it
uses `_graveyard_lock`, and #73 renames that.

## Task 1 — Failing tests

**Creates** `tests/test_rename_work_item.py`, with one test per acceptance
criterion 1-8.

- Criterion 4 uses two projects, as in `tests/test_cross_node_blocker*.py`.
- Criterion 7 uses a child board, as in `tests/test_epic*.py`.

All are committed `xfail(strict=True)`.

## Task 2 — Store: record and lookup

**Modifies** `tcw/store/base.py`:

- `WorkStore.rename` (abstract), with shared validation: slug form, date
  prefix, same slug, open status, worktree or branch, owner.

**Modifies** `tcw/store/fs.py`:

- `renames.yaml` read and write helpers;
- `renamed(slug) -> str | None`, which follows chains and guards against
  loops;
- `_unique_slug` treats a renamed-away slug as taken;
- blocker evaluation follows a rename (local and `tcw://` references);
- `check` validates `renames.yaml`'s shape.

**Proves** criteria 4-5.

## Task 3 — Store: the rename

**Modifies** `tcw/store/fs.py`: `FsWorkStore.rename`, under the lock.

1. It refuses when `renames.yaml` or the item is dirty.
2. It writes the record.
3. It runs `git mv` on the folder.
4. It rewrites `blocked_by`, `parent` and `initiative` on this board, graveyard
   `initiative` entries, and `initiative` on the boards `initiative_children`
   reads.
5. It rewrites capability `Planning doc:` fields.
6. It makes one scoped commit, returning the list of files that still mention
   the old slug, for the CLI to print.

**Proves** criteria 1-2 and 6-8.

## Task 4 — CLI

**Modifies** `tcw/work/cli.py`:

- the `rename` parser and `_rename`;
- `_resolve` refuses a followed rename for mutating verbs, naming the new slug;
- `show` and `path` follow it with the note;
- the tracker-link warning.

**Proves** criterion 3.

## Task 5 — Documentation Sync

- `skills/work/references/commands.md` (a rename section), and the
  `skills/work/SKILL.md` command table if a row fits the 60-line budget.
  [Skill-Driven-Component]
- `docs/guide/work.md`: a rename section. [Guide-Topic-Change]
- `CLAUDE.md`'s manual-edit paragraph mentions renaming a folder by hand, so
  add "or `tcw work rename`".
- The new capability `work/rename-a-work-item` (`tcw capabilities new`), and
  the item's `capabilities.yaml`.
- The changelog, and release notes. [Public-API]

## Task 6 — Full suite

Bare `pytest`, with the venv first on PATH. **Proves** criterion 9.

## Verification

By hand in a scratch node, reproduce the issue's case: an item blocked by
another and with a child, renamed. Then read `git show --stat`, run
`tcw work show <old>`, `tcw work start <old>`, and `tcw validate`.
