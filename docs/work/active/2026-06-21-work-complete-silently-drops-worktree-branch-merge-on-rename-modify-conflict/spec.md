# Spec — `work complete` must merge the worktree branch before teardown

## Problem (ground truth, narrower than the report)

The bug report hypothesizes a *rename/modify merge conflict*. The actual code is
worse and simpler: **`tcw work complete` never merges the work branch at all.**
`git grep merge tcw/` is empty. `_complete` (tcw/work/cli.py) does:

1. `st.complete(...)` — stage the `active/<slug>/ → completed/<slug>/` rename and
   the resolution/dod field edits in the **primary** checkout's index.
2. `remove_worktree(...)` — `git worktree remove` then `git branch -D`.

Step 2 deletes `work/<slug>` while its commits are still only on that branch.
Any commit made in the worktree (the implementation commit `I`) becomes
dangling. No error; output prints `completed … (done)`.

The design intent (docs/plan/phase-6-beyond.md): *"transitions on the primary
checkout/trunk, in-flight edits on the work branch, **merge-back on complete**."*
The merge-back was specified but never implemented. The existing
`test_complete_tears_down_worktree` masked it by completing an item with **zero**
commits on the branch (nothing to lose); `test_worktree_edit_merges_back_clean`
merges **manually** in the test, confirming the convention but not the
automation.

## Expected behavior

On `tcw work complete <slug>` for an item with a `branch`:

1. **Merge the work branch into the primary checkout first**, while the item
   docs are still under `active/<slug>/` (so there is no rename/modify overlap).
2. **Fail closed.** Any merge failure (conflict, dirty-tree refusal) → abort the
   half-merge, leave the branch and worktree intact, do **not** move the folder,
   print a clear error, exit non-zero. `--force` does **not** override a merge
   failure (it only overrides blockers).
3. Only after a successful merge: perform the `active→completed` rename
   (staged, per the split-ownership model the user commits it) and tear down the
   worktree + branch.
4. Idempotent on re-run: if the branch is already gone (manual recovery), the
   merge step is a quiet no-op rather than an error.

Invariant: **never delete the branch while its commits are unmerged; never print
`completed` when the code did not integrate.**

## Secondary (in scope, cheap)

- `worktree remove` for an already-absent worktree (`"is not a working tree"`)
  is tolerated quietly instead of printed as a failure line.

## Out of scope (won't fix here)

- `state.yaml` not matching a consumer repo's `prettier --check`. tcw emits YAML
  via `yaml.safe_dump`; matching an arbitrary downstream prettier config is
  brittle and not tcw's job. Noted, deferred.

## Abstraction litmus

Merging a git branch has no abstract-store analog (a Jira store has no
worktrees/branches). It stays a **filesystem-adapter local detail** — a
module-level `merge_worktree` in `tcw/store/fs.py` called from the CLI, exactly
where `add_worktree`/`remove_worktree` already live. The abstract
`WorkStore.complete()` is untouched.
