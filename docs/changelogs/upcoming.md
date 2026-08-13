# Upcoming

Developer changelog for the next version. Technical and precise; grouped by
category.

## Fixed

- `_has_work_store` (`tcw/store/fs.py`) no longer short-circuits on a literal
  `<node>/docs/work` directory: discovery now answers "does `FsWorkStore.open`
  succeed", so a decoy default folder cannot shadow an invalid or relocated
  `work.path`. Consequently a structurally incomplete store (missing `inbox` or
  any `WORK_STATUSES` folder) is absent from `child_nodes` / `parent_node` /
  `descendant_nodes` rather than half-present; `tcw work init` repairs it.
- `tcw/work/recursion.py`: `_inbox_write` now takes the opened `FsWorkStore`
  instead of a composed path, and `delegate` / `escalate` resolve the target
  through `FsWorkStore.open`. The writer may restore a missing `inbox` leaf but
  raises `ValueError` rather than creating the store root or its ancestors, so a
  misrouted request surfaces as a non-zero CLI error instead of a phantom tree.
- `reconcile` stages and commits through `store.store_git_root` with a pathspec
  derived from `store.root`, instead of staging an external path through the code
  node's repository (which raised `CalledProcessError`). Idempotence and the
  auto-completion/capability gates are unchanged.
- `_shipped_but_missing` (`tcw/capabilities/cli.py`) opens the configured work
  store and degrades to an empty result only on `ValueError`, replacing the
  `docs/work` directory guard that produced false negatives for external stores.
- `tcw work start --worktree` (`tcw/work/cli.py`) splits persistence by owner:
  item state commits in `store_git_root` with a pathspec scoped to the started
  item's two status folders, `.gitignore` commits in the code node, and
  `add_worktree` runs only after both required commits succeed. A same-repository
  store keeps its single `tcw work: start <slug> (worktree)` commit carrying
  `.gitignore`; only split repositories produce the `(worktree metadata)` /
  `(worktree ignore)` pair.

## Changed

- `ensure_worktree_ignored` (`tcw/store/fs.py`) returns `bool` — whether
  `.gitignore` changed — so a caller committing in a different repository knows
  whether the code node still owes a commit. It still stages the file itself.

## Internal

- Two-repository regression fixtures: `mk_node(..., work_repo=)` in
  `tests/test_recursion.py`, `_split_repo_item` / `_register` in
  `tests/test_external_work_store.py`, and `_external_completed_planning_item` in
  `tests/test_capabilities.py`. New coverage for commit scoping (an unrelated
  staged file and a second staged work item both stay out of the start commit)
  and for both worktree-start failure boundaries.

### Worktree merge-back

- `merge_worktree` (`tcw/store/fs.py`) pins `merge.directoryRenames=true` with
  `-c` on its `git merge` invocation. Git defaults that setting to `conflict` for
  merges, which stages a file added under a renamed directory at the new path but
  still exits non-zero so a human confirms the relocation; `merge_worktree` could
  not tell that apart from a real conflict and failed closed. The trigger is the
  ordinary flow — `start --worktree`, commit a lifecycle artifact on the branch,
  `submit` (which renames `active/<slug>/` to `review/<slug>/` on the primary
  checkout), `complete` — and it affects the default in-repository layout, not
  only a configured `work.path`. Scoped with `-c` so the user's Git configuration
  is neither read nor written; a repository setting `merge.directoryRenames=conflict`
  still completes. `true` rather than `false`: `false` disables rename detection
  and would strand the file under the removed directory.
- The `merge_worktree` docstring no longer claims the merge cannot meet a
  rename/modify overlap. Ordering it before `complete`'s own `active→completed`
  rename avoids that one; it does not avoid a rename an earlier transition left.
- Note the widened effect: `directoryRenames=true` applies to every directory
  rename in the merge, so branch-added files follow renamed **code** directories
  too. Verified directly, not inferred.
- `tests/test_recursion.py`: `test_complete_merges_across_a_transition_rename` and
  `test_complete_merges_across_a_rename_despite_local_git_config`, sharing
  `_submit_then_complete_a_worktree_item`. No prior test combined `--worktree`,
  `submit`, and a file *added* inside the renamed directory — additions are what
  trigger the confirmation, so the two existing merge-back tests could not catch
  this. `test_complete_aborts_on_merge_conflict` is unchanged.
