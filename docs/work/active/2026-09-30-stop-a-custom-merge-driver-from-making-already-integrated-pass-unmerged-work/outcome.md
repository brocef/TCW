# Outcome: Stop a custom merge driver from making --already-integrated pass unmerged work

## What shipped

- **Code and tests** — `79ba0f03`: `branch_integration` runs the trial merge with
  every configured `merge.<name>.driver` overridden to `false` via `-c`; new
  `_merge_drivers` lists them and fails closed on a name holding `=` or on `git
  config` failing; the refusal names the drivers; six tests in
  `tests/test_already_integrated_check.py`.
- **Code-review fixes** — `325fb1bd`: git's built-in `union` is overridden too;
  a worktree item's way out says to remove the worktree before deleting the
  branch.
- **Docs** — `8b82c039`, `d6e98814` (changelog, release notes), `5e1c491e`
  (`transitions.md`, `docs/guide/work.md`).

## Test result

- Full suite under bare `pytest` at `d6e98814`: 1 failed, 5219 passed, 3
  skipped; the one failure belongs to the detached-worktree item.
- `tests/test_already_integrated_check.py`: all pass; the five new hole tests fail
  against the unfixed code.

## What the plan or spec got wrong

- **The spec's first mechanism (environment variables) loses to an inherited
  `GIT_CONFIG_PARAMETERS`**; the spec review found it and `-c` is used.
- **The spec said built-in drivers cannot hide a change.** `union` can hide a
  deletion; the code review found it.
- **My first squash test put the two sides' changes on adjacent lines**, which
  git's own merge cannot resolve, so the test was wrong, not the code; the
  fixture now separates them.
- The plan's advice "delete the branch yourself" does not work for a worktree
  item (git refuses while the worktree has it checked out); found by the code
  review, which reproduced a loop with the detached-worktree check.
