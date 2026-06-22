# Plan

TDD. Tests first (they fail on current code), then the fix.

## 1. Regression tests — `tests/test_recursion.py` (worktree section)

- `test_complete_merges_worktree_branch_before_teardown`
  - new + `start --worktree`; in the worktree modify the tracked
    `active/<slug>/content.md` **and** add a new `feature.py`, `git add -A` +
    commit on `work/<slug>` → capture sha `I`.
  - from primary: `complete --resolution done --confirm` → exit 0.
  - assert `git merge-base --is-ancestor <I> HEAD` == 0 (I reachable on the
    integration branch), `feature.py` present in primary HEAD, worktree gone,
    branch gone, status completed. **Fails on current code** (I dangling).

- `test_complete_aborts_on_merge_conflict`
  - new + `start --worktree`; worktree rewrites `content.md` one way + commit.
  - primary `main` rewrites the same `content.md` another way + commit (diverge).
  - `complete --confirm` → exit 1, stderr mentions the branch left intact.
  - assert branch still exists, worktree still exists, status still `active`,
    and no merge in progress (`MERGE_HEAD` absent — abort ran).

## 2. Fix — `tcw/store/fs.py`

Add module-level `merge_worktree(node_root, branch) -> str | None`:
- if `refs/heads/<branch>` doesn't exist → return `None` (quiet no-op, re-run).
- `git merge --no-edit <branch>`; on non-zero → `git merge --abort` and return an
  error string. Else `None`.

`remove_worktree`: swallow the `"is not a working tree"` stderr (already absent)
instead of appending a warning.

## 3. Fix — `tcw/work/cli.py` `_complete`

After the `--confirm` gate and **before** `st.complete(...)`:
```
if has_worktree and branch:
    err = merge_worktree(st.node_root, branch)
    if err: print(..., file=sys.stderr); return 1
```
Import `merge_worktree`. Order is load-bearing: merge while docs are in
`active/`, then `st.complete()` renames, then `remove_worktree()`.

## 4. Verify

`pytest tests/test_recursion.py -q` then full `pytest -q`.

## 5. Documentation sync (run the skill)

- `docs/changelogs/upcoming.md` [Any-Code-Change] — Fixed entry, with hash range.
- `docs/release-notes/upcoming.md` [Public-API] — plain-language Fixed note.
- `skills/tcw-work/SKILL.md` [Skill-Driven-Component] — the `--worktree` line
  claims "merge back" already; verify it now matches reality, tighten if needed.
- `README.md` — only if it describes worktree completion (check; likely no edit).
