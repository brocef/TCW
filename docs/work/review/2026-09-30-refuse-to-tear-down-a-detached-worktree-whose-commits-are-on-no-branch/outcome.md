# Outcome: Refuse to tear down a detached worktree whose commits are on no branch

## What shipped

- **Tests** (`tests/test_detached_worktree_teardown.py`) and **code** — `9814be3c`:
  `unbranched_commits`, `unbranched_summary` and `unbranched_problem` beside
  `remove_worktree` in `tcw/store/fs.py`; `remove_worktree` keeps such a
  worktree (and its branch) and warns; `_complete` refuses a shipping completion
  before anything changes, `--force` included. A discard keeps the worktree.
- **Code-review fixes** — `325fb1bd`: the worktree's top is compared by folder
  identity (`_same_folder`), not text; a folder git cannot check gets its own
  advice instead of a branch command that would act on the primary checkout;
  the advice never names a work branch that is already gone.
- **Full-suite fix** — `d49c4fee`: the check steps aside when the primary
  checkout has no repository, so the merge-back's refusal (which names the
  branch at risk) is the one printed.
- **Docs** — `67afe234` (changelog, release notes), `5e1c491e` (README
  `complete` row, `skills/work/references/transitions.md`, `docs/guide/work.md`).

## Test result

- Full suite under bare `pytest` at `d6e98814`: **1 failed, 5219 passed, 3
  skipped** (25 min). The failure was
  `tests/test_non_git_writes.py::test_complete_refuses_when_the_merge_back_has_no_repository`,
  caused by this item and fixed in `d49c4fee`.
- After that fix: `tests/test_non_git_writes.py`,
  `tests/test_detached_worktree_teardown.py`,
  `tests/test_already_integrated_check.py`, `tests/test_override_letter_case.py`
  — 103 passed. The full suite was not re-run after `d49c4fee`.
- Mutation checks: removing the `_complete` refusal, the `remove_worktree` guard
  or the top-folder check each turns tests red.

## What the plan or spec got wrong

- **Spec Risks said a non-worktree folder makes git fail.** It does not: `git
  -C` on a plain folder under `.worktrees/` answers for the primary checkout.
  Found by the spec review; the helper checks the folder is its own top.
- **The top-folder check first compared paths as text**, which broke completion
  for a project reached through an override in other letter case
  (`tests/test_override_letter_case.py`, macOS only — Linux CI skips it). Found
  by the code review.
- **The plan did not foresee the primary checkout having no repository**; the
  full suite found it.
- Two advice texts were wrong (a branch command for a folder git cannot check;
  merging into a deleted branch). Found by the code review.

## Notes

- Stash is deliberately not counted as keeping a commit (spec amendment).
