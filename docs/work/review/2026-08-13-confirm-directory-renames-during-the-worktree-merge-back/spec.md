# Confirm directory renames during the worktree merge-back

## Capability changes

Changed:

- `work/complete-a-work-item`

No new or removed capability. No taxonomy change: `complete` and the worktree
merge-back are already registered behavior, and this restores the documented
"merge back, then tear down" promise on a path where it currently does not hold.
`work/start-a-work-item` and `cli/run-from-a-git-worktree` were checked for
contradiction and are unaffected — neither describes merge behavior.

## Problem

`merge_worktree` (`tcw/store/fs.py:447-465`) runs `git merge --no-edit <branch>`
(`fs.py:458`) with no per-invocation configuration, so it inherits git's default
`merge.directoryRenames=conflict`. Under that value git detects a directory
rename, works out where a file added on the other side belongs, stages it at the
new path — and still exits non-zero, because `conflict` means "place it, but make
a human confirm the relocation". `merge_worktree` treats any non-zero exit as a
failure, aborts the merge (`fs.py:460-462`), and returns the fail-closed message
at `fs.py:463-464`. `_complete` then skips teardown and returns 1.

The result is that `tcw work complete` reports "merge of `work/<slug>` into the
primary checkout failed; branch left intact" for a merge git was willing to
finish unattended.

The function's own docstring records the assumption that no longer holds:

> Runs _before_ the active→completed rename so the merge sees the item docs still
> under `active/<slug>/` (no rename/modify overlap). — `fs.py:449-451`

That is true of the `active → completed` rename `complete` itself performs. It is
**not** true of the `active → review` rename that `tcw work submit` performed
earlier, on the primary checkout, while the branch kept committing under
`active/<slug>/`. By the time `complete` merges, the primary checkout has already
renamed the directory and the branch has not. Ordering the merge before
`complete`'s own rename does not help, because the straddling rename came from a
previous transition.

This is reachable from the documented flow with no unusual steps:
`start --worktree` → commit `outcome.md` on the branch (what the implement stage
produces) → `submit` → `complete`. It affects the default in-repository
`docs/work` layout; a configured `work.path` is not required.

Observed on a real branch, the same merge run twice:

```
$ git merge --no-commit --no-ff work/<slug>
CONFLICT (file location): docs/work/active/<slug>/outcome.md added in
work/<slug> inside a directory that was renamed in HEAD, suggesting it should
perhaps be moved to docs/work/review/<slug>/outcome.md.
Automatic merge failed; fix conflicts and then commit the result.

$ git -c merge.directoryRenames=true merge --no-commit --no-ff work/<slug>
Path updated: … moving it to docs/work/review/<slug>/outcome.md.
Automatic merge went well
```

Nothing masks this today because no test combines the three ingredients. The two
merge-back tests in `tests/test_recursion.py` both avoid it:
`test_worktree_edit_merges_back_clean` modifies an already-tracked file and never
submits, and `test_complete_merges_worktree_branch_before_teardown` adds
`feature.py` at the repository root — outside any renamed directory — and also
never submits. A scan of `tests/` found no test that runs `submit` on a
`--worktree` item and then completes it.

## Goals

- Let `tcw work complete` finish a `--worktree` item whose branch only added
  files, including files inside a directory the primary checkout has since
  renamed, without manual intervention.
- Keep the fail-closed contract for genuine conflicts exactly as it is: branch
  and worktree intact, item still `active`, half-merge aborted, non-zero exit,
  no silently dropped commits.
- Decide the merge's behavior from TCW's invocation rather than from whatever the
  user's Git configuration happens to say, so the outcome is the same on every
  machine.
- Close the coverage gap: a regression test that runs `--worktree` → artifact on
  the branch → `submit` → `complete`.

## Non-goals

- Reordering the lifecycle so transitions and branch artifacts never straddle a
  rename. The user scoped this item to the merge-back; if the ordering is the
  deeper problem it is a separate item.
- Rebasing, rewriting, or reordering the work branch during `complete`.
- Changing `remove_worktree`, `add_worktree`, branch deletion, or the
  `--already-integrated` path.
- Fixing the unrelated `_ERRORS` gap where `reconcile --commit` raises an uncaught
  `subprocess.CalledProcessError` (`tcw/work/cli.py:34`, `:160-172`).
- Reading, writing, or migrating the user's Git configuration.

## Design

Pass the setting on the invocation instead of inheriting it:

```
git -c merge.directoryRenames=true -C <node_root> merge --no-edit <branch>
```

`-c` applies for that one command only. It neither reads nor mutates the user's
config, so a repository or user that has explicitly set
`merge.directoryRenames=conflict` still completes — TCW's merge-back is TCW's
decision, not a place to honor an ambient preference. The `rev-parse` guard, the
`--abort` on failure, the error text, and the `None`-on-success contract all stay
as they are.

`true` is the correct value rather than `false`: `false` disables directory-rename
detection altogether, which would leave `outcome.md` stranded at the old
`active/<slug>/` path and silently resurrect a directory the transition removed —
a worse outcome than today's refusal.

**Sibling sweep.** The defect class is "a Git invocation whose result depends on
ambient configuration that can turn a benign outcome into a reported failure".
Swept repo-wide over every `git -C` call in `tcw/` (20 sites):
`merge_worktree` holds the only `git merge`, so it is the only instance. The
`git commit` sites (`fs.py:333`, `fs.py:400`) also inherit ambient config —
`commit.gpgsign`, `core.hooksPath` — but those produce genuine failures where the
commit really did not happen, which `git_commit_result` already reports
accurately. That is the opposite failure mode and is deliberately left alone.

Correct the stale premise in the `merge_worktree` docstring while changing the
function: the merge is ordered before `complete`'s own rename, but it can still
meet a rename left by an earlier transition, which is precisely why the flag is
needed.

## Acceptance criteria

1. A `--worktree` item that commits a new file under `docs/work/active/<slug>/`
   on its branch, is then `submit`ted from the primary checkout, and is then
   completed with `--resolution done --confirm`, exits 0.
2. After that completion the added file is present on the primary branch at
   `docs/work/completed/<slug>/<file>` and absent from `docs/work/active/` and
   `docs/work/review/`.
3. The branch's implementation commit is an ancestor of the primary branch HEAD
   after that completion, and any non-lifecycle file it added (e.g. a code file at
   the repository root) is present in the working tree.
4. After that completion the worktree directory is gone and `git branch --list
   work/<slug>` is empty.
5. `tests/test_recursion.py::test_complete_aborts_on_merge_conflict` passes
   **unmodified**: a diverging edit to the same tracked file on both sides still
   exits 1, leaves the branch and worktree present, leaves the item `active`, and
   leaves no `.git/MERGE_HEAD`.
6. Criterion 1 still holds in a repository whose own config sets
   `merge.directoryRenames=conflict`, and running the flow leaves that config
   value unchanged.
7. `merge_worktree` still returns `None` without invoking `git merge` when the
   branch does not exist.
8. `git merge` is the only invocation that gains a `-c` override: a scan of
   `git -C` call sites in `tcw/` shows no other command carrying one.
9. The `merge_worktree` docstring no longer claims the merge cannot meet a
   rename/modify overlap.
10. The full Python suite passes, and `tcw taxonomy check`, `tcw capabilities
    check`, and `tcw validate` all exit 0.
11. `work/complete-a-work-item`'s description, `docs/changelogs/upcoming.md`, and
    `docs/release-notes/upcoming.md` describe the merge-back completing across a
    directory rename; `skills/tcw-work/references/transitions.md` says the same
    under `complete`.

## Risks

- `merge.directoryRenames=true` applies to **every** directory rename in the
  merge, not only the lifecycle folder. A code directory renamed on the primary
  branch after the worktree was created will also silently absorb files the branch
  added under the old path. That is git's documented `true` semantics and is the
  behavior rebase and cherry-pick already use by default, but it is a real
  behavior change for code as well as for lifecycle files and belongs in the
  release notes rather than only the changelog.
- The regression test must add a **new** file inside the renamed directory. A test
  that only modifies an existing tracked file will pass against the unfixed code,
  because directory-rename confirmation is triggered by additions — which is
  exactly why the current suite misses this.
- `test_complete_aborts_on_merge_conflict` must be left byte-identical. Editing it
  to accommodate the fix would dissolve the only guard proving conflicts still
  fail closed.
- A user who has come to rely on the current stop as a review checkpoint loses it.
  Judged acceptable: TCW is reporting a failure that did not occur, and the merge
  is still recorded as an ordinary merge commit that can be inspected or reverted.

## Notes

- The problem was reproduced directly against the branch of
  `2026-08-12-honor-the-configured-work-path-at-every-work-store-call-site`, not
  from a bug report; both merge runs quoted above were real, and the second left
  zero unmerged paths.
- `git` defaults `merge.directoryRenames` to `conflict` for merge and to `true`
  for rebase and cherry-pick. That asymmetry is why rebasing the work branch
  appears to "fix" the problem, and why rebasing is not the design chosen here.
