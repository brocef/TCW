# Plan — Let complete --already-integrated check a branch worked in a worktree tcw did not create

Worked in a worktree (`start --worktree`), with a scratch venv pinned to it.

## Task 1 — Failing tests

**Creates** `tests/test_already_integrated_check.py`, with one test per
acceptance criterion 1-9. Each builds a scratch node with a git repository and
drives `tcw.cli.main` in-process, as `tests/test_work_autocommit.py` does.

- Branches are made either by `start --worktree` or by hand
  (`git branch`, `git worktree add`).
- The "merged" cases use `git merge` and `git merge --squash` plus a commit in
  the primary checkout.
- Criteria 1, 3, 4, 5, 6, 8 and 9 fail today and are committed
  `xfail(strict=True)`. Criteria 2 and 7 pass today and must keep passing.

## Task 2 — The check

**Modifies** `tcw/store/fs.py`: `branch_integration(node_root, branch) -> str
| None`, next to `merge_worktree`:

- refuses when there is no git repository (as `merge_worktree` does);
- refuses when `HEAD` is the branch itself (`symbolic-ref --short HEAD`);
- passes when `merge-base --is-ancestor refs/heads/<b> HEAD` succeeds;
- otherwise runs `merge-tree --write-tree HEAD refs/heads/<b>`, and passes
  when its output tree equals `rev-parse HEAD^{tree}`. A failing `merge-tree`
  (a conflict, or a git older than 2.38) is not proven.

The reason it returns names the branch, the short commit it was checked
against, and the remedy.

## Task 3 — `complete`

**Modifies** `tcw/work/cli.py`:

- adds `--branch` to the `complete` parser, with help text;
- `--branch` without `--already-integrated` gets `parser.error` style
  handling (exit 2);
- replaces the "applies to an item started with --worktree" refusal with:
  - the branch to check is the recorded one or `--branch`;
  - a mismatch with the recorded branch is refused;
  - with neither, refused, naming `--branch`;
  - a named branch that does not exist is refused;
  - a recorded branch that is gone is skipped;
  - only when shipping, `branch_integration` runs and a refusal returns 1
    before anything else changes.
- The teardown still receives the recorded branch only.

**Updates** the tests that pinned the old behavior:

- `tests/test_work_autocommit.py`:
  - `test_already_integrated_skips_the_merge_but_keeps_the_gates` merges the
    branch into main before completing, and still asserts the merge-back was
    skipped (by the file state);
  - check the tests around line 588 for the same.
- `tests/test_transition_hints.py` (~195) for the changed refusal text.

Then the `xfail` marks are removed. **Proves** criteria 1-10.

## Task 4 — Documentation Sync

- `docs/guide/work.md` (~308): the `--already-integrated` comment, and
  `--branch`. [Guide-Topic-Change]
- `docs/capabilities/work/complete-a-work-item/description.md` and the item's
  `capabilities.yaml` (`changed:`).
- `skills/work/references/transitions.md`, wherever `--already-integrated` is
  described. [Skill-Driven-Component]
- `tests/cli/scenarios/09-worktree-isolation-and-merge-back.md`, assertions
  8-9: state that the branch must really be merged.
- The changelog, and release notes that call out the behavior change.
  [Any-Code-Change, Public-API]
- README: not triggered unless it describes the flag (grep).

## Task 5 — Full suite

Bare `pytest`, with the venv first on PATH. **Proves** criterion 10.

## Verification

By hand in a scratch repository:

- a hand-made worktree, merged by squash, completed with
  `--already-integrated --branch`;
- an unmerged TCW worktree, refused, with the branch still present afterwards.
