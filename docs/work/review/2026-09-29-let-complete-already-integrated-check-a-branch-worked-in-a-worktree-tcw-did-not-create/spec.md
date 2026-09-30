# Spec — Let complete --already-integrated check a branch worked in a worktree tcw did not create

## Capability changes

- **changed:** `work/complete-a-work-item` — `--already-integrated` checks
  that the branch really was merged, and `--branch` names the branch of an
  item worked in a worktree TCW did not make.

## Problem

`tcw work complete --already-integrated` is meant for a work branch merged
outside TCW, typically through a merged pull request. Today it has two
problems:

- **It checks nothing.** It only skips the merge-back (`_complete`,
  `tcw/work/cli.py`). The teardown then runs `remove_worktree`
  (`tcw/store/fs.py`), which deletes the branch with `git branch -D`, the
  force delete. So completing an item whose branch was never merged
  **throws away its commits**, leaving them only in git's reflog. An existing
  test (`test_already_integrated_skips_the_merge_but_keeps_the_gates`)
  completes exactly such an unmerged branch and passes.
- **It is refused for an item without a TCW worktree.** Agents who make their
  own worktrees (`git worktree add`) get "applies to an item started with
  --worktree; <slug> has none". They then complete without the flag, which is
  the same as an unchecked completion.

## Goals

1. **A real check.** With `--already-integrated`, a shipping completion
   (`--resolution done`) goes ahead only if the branch is integrated into the
   primary checkout's current commit (`HEAD`, in the item's node's
   repository). That is where TCW's own merge-back would have merged it.
   Integrated means either:
   - the branch tip is an ancestor of `HEAD`
     (`git merge-base --is-ancestor`), which covers a merge commit or a
     fast-forward; or
   - merging the branch into `HEAD` would change nothing: the tree
     `git merge-tree --write-tree HEAD <branch>` produces equals `HEAD`'s
     tree. That covers a squash or rebase merge of a pull request.
2. **A refusal that says what to do.** Otherwise the command refuses before
   anything is touched: before the merge-back, the `pre` hook and the store
   move. The refusal names the branch, the commit it was checked against, and
   the remedy: pull the merge into this checkout, or merge the branch.
3. **`--branch <name>`** on `complete`, allowed only with
   `--already-integrated`, names the branch of an item with no recorded
   branch. The same check applies. It is refused if the item already records a
   different branch, and refused if `refs/heads/<name>` does not exist.
   Remote-only names are not looked up.
4. **TCW deletes only what it made.** A branch named with `--branch` is never
   deleted, and no worktree is removed for it. A recorded branch that passed
   the check is deleted as today.
5. **A recorded branch that no longer exists passes**, as today
   (`test_already_integrated_tolerates_a_worktree_removed_externally`).
   There is nothing left to lose. A branch named with `--branch` must exist.
6. **Not from inside the branch.** If `HEAD` in the node's repository is the
   branch being checked, as when the command is run from inside the
   hand-made worktree, it refuses. Checking a branch against itself always
   passes.
7. Discards (`--resolution` other than `done`) are unchanged. They merge
   nothing and keep the branch.

## Non-goals

- **No `tcw work start --branch`.** It would record a branch with no worktree
  and break the assumption, in several places in `_complete`, that the two go
  together. `--branch` at completion solves the issue on its own.
- **No override flag.** `--force` already means "despite blockers and the
  capability gate", and overloading it would hide this check. A branch that
  cannot be shown to be merged is refused. The way forward is to merge it, or
  to delete the branch deliberately.
- **Not the configured trunk branch.** `work.trunk-branch` is advisory, and
  `HEAD` is what the completion reads the item from.

## Design

- One helper, `branch_integration(node_root, branch) -> str | None`, in
  `tcw/store/fs.py` next to `merge_worktree`. It returns `None` when
  integrated, and otherwise the reason. All git calls run with
  `-C node_root`, never the store's repository. A `git` without
  `merge-tree --write-tree` (older than 2.38) counts as not proven.
- `_complete` calls it where today's refusal is. For a recorded branch that
  is gone it skips the check. The existing refusal "applies to an item started
  with --worktree" goes; `--branch` takes its place for such an item.
- The teardown passes a branch to `remove_worktree` only when it was recorded
  by `start --worktree`.

Litmus: a branch belongs to the code repository, not the store. The check is
the filesystem adapter's CLI concern, like `merge_worktree`. A tracker-backed
store has no worktree fields and never reaches it.

## Acceptance criteria

1. A TCW worktree item whose branch has an unmerged commit:
   `complete --already-integrated` exits 1, the item is still in `review`,
   and the branch still exists.
2. The same after `git merge` of the branch in the primary checkout: it
   completes, and the branch is deleted.
3. After a squash merge (`git merge --squash` and commit): it completes.
4. An item without a worktree, whose branch was made by hand and merged:
   `complete --already-integrated --branch <b>` completes, and the branch
   still exists.
5. The same with the branch unmerged: refused, nothing changed.
6. `--branch` without `--already-integrated`: a usage error. `--branch nosuch`:
   refused, naming it. `--branch` different from the recorded branch: refused.
7. A recorded branch deleted outside TCW: completes, as today.
8. Run with `HEAD` on the branch itself: refused.
9. `--already-integrated` without `--branch` on an item with no recorded
   branch: refused, naming `--branch`.
10. The existing tests pass, updated where they pinned the old behavior: the
    unmerged-branch test is now merged first, and the text of the refusal
    tests changes. The full suite passes as CI runs it.

## Risks

- **A behavior change for scripts** that used the flag on an unmerged branch.
  Intended: those runs were silently losing commits. The release notes say so.

## Notes

- Advisors: Opus, and Sonnet in place of Codex (at its usage limit until
  2026-10-03). Both confirmed the flag checks nothing and chose `--branch` on
  `complete` over `start --branch`. Their splits:
  - **What to check against.** Opus: `HEAD`. Sonnet: `work.trunk-branch` if
    set. Took `HEAD`: it is where the merge-back goes.
  - **Squash merges.** Sonnet: `git cherry`, which both agreed misses
    squashes. Opus: `merge-tree` equality. Took `merge-tree`.
  - **An override.** Sonnet: a dedicated flag. Opus: none. Took none, as the
    safer default.
  - Sonnet's traps are in goals 6 and 3: from inside the branch, and
    remote-only names.
