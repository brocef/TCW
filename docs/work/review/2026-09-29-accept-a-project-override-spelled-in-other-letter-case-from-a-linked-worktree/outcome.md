# Outcome — Accept a project override spelled in other letter case from a linked worktree

## What changed

- `tcw/store/project.py`: `_below(path, root)` answers "where is `path` under
  `root`?" by the text first and, failing that, by comparing the device and
  inode of `path` and each of its ancestors with `root`'s. So on a disk that
  ignores letter case, a path spelled differently is still found under the
  folder it is in. Rule 1 (`_locator_path`) and Rule 2 (`_worktree_copy`) of
  the worktree mapping use it.
- `tcw/store/fs.py`: `anchor_configured_path` and `worktree_node_root` use it
  too; `worktree_node_root` now returns `None` rather than raising when the
  node is not inside the worktree.

## Commits

- ddc364ff tests (failing cases `xfail(strict=True)`)
- f7202c0a `_below` and its four call sites
- b804a666 a guard test (an override naming the worktree's own copy)
- 900f1254 documentation
- 02d29611 review fixes: a test that really reaches Rule 1, corrected
  docstrings, spec and plan notes

## Evidence

- `tests/test_override_letter_case.py`: 7 tests, skipped on a disk that
  distinguishes letter case (ran here, on macOS). Criteria 1-5 each have one;
  the Rule 1 test names the worktree's own root through
  `TCW_PROJECT_APP_REPO` in upper case, so its parent locator `..` leaves the
  worktree and must be re-anchored — before the change the parent silently
  dropped out of the graph.
- Mutation checks: reverting `_below` to a text-only comparison turned the
  case tests red, including the Rule 1 test.
- Full suite (bare `pytest`, `venv3` first on PATH so subprocesses run this
  worktree's code): 4991 passed, 3 skipped at 02d29611 (23 minutes).
- Hands-on: in a scratch repository with a linked worktree, an override
  spelled in upper case validates cleanly from the worktree and shows the
  intended "points at the primary checkout" warning, with no duplicate or
  non-reciprocal errors.

## What the plan or spec got wrong

- The first two tests meant for Rule 1 never reached it: one went through the
  working directory, which macOS already normalises; the other overrode
  `pkg-b`, whose `..` stays inside the worktree. The reviewer supplied a
  scenario that does reach it (the worktree root as the override); the
  second test stays as a guard with a docstring saying what it guards.

## Autonomous decisions

- **Spec and plan.** No open question arose, so the advisors were not
  consulted: the fix (compare folders by identity where text fails) follows
  the rule the codebase already uses in `_same_folder` and `_store_key`.
- **Review, the Rule 1 test did not reach Rule 1.** Accepted; added the
  reviewer's scenario and confirmed its mutation goes red.
- **Review, docstrings describing the old comparison.** Accepted and corrected
  in the tests' docstrings and the spec and plan; the `worktree_node_root`
  docstring was missed and corrected at verify.
- **Review, bound `_below` to a single `stat` call for speed.** Rejected: it
  runs only when the text comparison fails, which on a case-sensitive disk or
  with consistent spelling is never, and the ancestor walk is at most the
  depth of the path.
