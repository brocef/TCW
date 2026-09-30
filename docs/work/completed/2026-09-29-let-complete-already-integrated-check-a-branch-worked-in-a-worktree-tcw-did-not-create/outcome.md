# Outcome

`tcw work complete --already-integrated` used to check nothing. It skipped the
merge-back on the caller's word, and the teardown then ran `git branch -D`, so
a branch that had never been merged was force-deleted along with its work. Now
it checks, before anything changes, that the branch reached the node
repository's `HEAD`:

- its tip is an ancestor of `HEAD` (a merge or fast-forward); or
- `git merge-tree --write-tree HEAD <branch>` gives `HEAD`'s own tree (a squash
  or rebase).

Otherwise it refuses. `--branch <name>` lets an item started without
`--worktree` be completed the same way. That branch is never deleted.

## What shipped, task by task

| Task | What | Commit |
| ---- | ---- | ------ |
| 1 | failing tests (8 xfail, 3 guarding kept behaviour) | `22990193` |
| 2 | `branch_integration` and `branch_exists` in `tcw/store/fs.py` | `e1cac6ec` |
| 3 | `complete`: the check, `--branch`, the refusals; three old tests updated | `e1cac6ec` |
| 4 | guide, skill references, capability, scenario 09, changelog, release notes | `c6aa4c57` |
| 5 | review fixes | `0f5a51dd` |

## What the plan and spec got wrong

- **Goal 6 ("not from inside the branch") was specified as "`HEAD` is the
  branch".** It missed two routes to the same false pass:
  - a detached `HEAD` at the branch's tip, the natural state inside a
    hand-made worktree;
  - a tag with the branch's name, which makes `symbolic-ref --short` print
    `heads/<b>`.
  Both are now refused or caught, and tested.
- **Goal 7 ("discards unchanged") was quietly broken by the first version.**
  The old refusal of `--already-integrated` on an item without a worktree
  applied to discards too. It was restored for discards, and `--branch` on a
  discard is a usage error.
- **The plan's usage error expected `SystemExit`.** This CLI's usage errors
  print and return 2, so the test asserts the return code.
- **The updated "skips the merge" test** used to prove the skip by a file
  missing from main. That no longer works once the flag needs a merge. It now
  squashes first and proves no merge commit was made.

## Review

The adversarial review returned "merge after the fixes below". Accepted:

1. **Detached `HEAD` and the `--short` tag case** (above), reproduced by the
   reviewer end to end.
2. **One message for three failures.** A conflict (exit 1) and git failing to
   answer (older than 2.38, unrelated histories) now read differently. The
   refusal names the way out when the work landed some other way:
   - for a recorded branch, delete it and re-run;
   - for a named branch, complete without the flag.
   Tested with a squash followed by a trunk edit to the same file.
3. **Discards with the flags** (above).
4. **Notes A-C:** the command table shows `[--branch <b>]`, the README's
   refusal column names the new refusal, and the changelog's "asks instead of
   refusing" is corrected.
5. **commands.md** now says the check happens "whenever the branch still
   exists", since a recorded branch that is gone passes.

Left for a separate change, and recorded as follow-ups:

- A clean, detached worktree holding commits on no branch is removed at
  teardown, and those commits are lost. This happened before this change too,
  and is also taken by the ordinary merge-back route.
- Whether a custom `.gitattributes` merge driver (`merge=ours`) can make
  `merge-tree` hide a branch's edits.

## Checks

- 16 tests in `tests/test_already_integrated_check.py`, and 233 with the
  related files, pass.
- Mutations of the ancestor rule, the tree comparison, the self-check, the
  detached check and the full-ref comparison each turn a test red.
- `tcw validate` and `tcw capabilities check` pass.
- Full suite: see `refined-outcome.md`.

## Autonomous decisions

- **Check against `HEAD` or `work.trunk-branch`?**
  - Opus: `HEAD`. Sonnet: the trunk branch if set.
  - Took `HEAD`: it is where TCW's own merge-back would have merged.
- **How to detect a squash?**
  - Sonnet: `git cherry`, which both agreed misses squashes.
  - Opus: `merge-tree` equality.
  - Took `merge-tree`. It fails closed on an old git.
- **An override flag?**
  - Sonnet: yes. Opus: no.
  - Took none. The way out is to merge, or delete the branch deliberately,
    and the refusal now says so.
- **Review finding 1: refuse every linked worktree, or only a detached
  `HEAD`?**
  - The reviewer asked whether any legitimate flow completes from a linked
    worktree.
  - Refused only a detached `HEAD` (plus the self-check). Some people work
    permanently in linked worktrees, and "checked against `HEAD`" is the
    spec's chosen meaning.
- **Rejected: none.**
