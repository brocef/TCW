# Confirm directory renames during the worktree merge-back

## Product changes

`tcw work complete` refuses to finish a `--worktree` item, reporting a merge
failure, in a situation where nothing is actually in conflict. The user is told
"merge of `work/<slug>` into the primary checkout failed; branch left intact" and
has to resolve by hand — for a merge that git was willing to complete on its own
given one flag.

The trigger is the ordinary documented flow, not an unusual one:

1. `tcw work start <slug> --worktree` creates the branch from `HEAD` while the
   item is under `docs/work/active/<slug>/`.
2. Implementation commits a lifecycle artifact on the branch — `outcome.md` is
   the normal case, since the implement stage produces it.
3. `tcw work submit <slug>` runs on the primary checkout and renames
   `docs/work/active/<slug>/` → `docs/work/review/<slug>/`.
4. `tcw work complete <slug>` merges the branch back, and stops.

Git is not confused here. It detects the directory rename and knows the new file
belongs at `docs/work/review/<slug>/outcome.md`. It stops because
`merge.directoryRenames` defaults to `conflict` for merges, which means "place it,
but make a human confirm". TCW reads that as a conflict and fails closed.

What we want: a `--worktree` item that only *added* lifecycle artifacts on its
branch should complete without manual intervention, while a merge with genuine
content conflicts must keep failing closed exactly as it does today — the branch
and worktree left intact, the item still `active`, nothing silently dropped.

## Technical changes

`merge_worktree` (`tcw/store/fs.py:452-468`) is the only `git merge` TCW runs
(verified by scan). It shells out to a bare `git merge --no-edit <branch>` and
therefore inherits git's per-command defaults, including the `conflict` value for
`merge.directoryRenames`.

Observed on the live reproduction, same merge, twice:

```
$ git merge --no-commit --no-ff work/<slug>
CONFLICT (file location): docs/work/active/<slug>/outcome.md added in
work/<slug> inside a directory that was renamed in HEAD, suggesting it should
perhaps be moved to docs/work/review/<slug>/outcome.md.
Automatic merge failed; fix conflicts and then commit the result.

$ git -c merge.directoryRenames=true merge --no-commit --no-ff work/<slug>
Path updated: docs/work/active/<slug>/outcome.md added in work/<slug> inside a
directory that was renamed in HEAD; moving it to
docs/work/review/<slug>/outcome.md.
Automatic merge went well
```

Zero unmerged paths in the second run, and the file lands at the correct path.

Note for the spec stage: rebasing the work branch onto the primary branch also
avoids the stop, because rebase and cherry-pick default `merge.directoryRenames`
to `true` rather than `conflict`. That is a workaround a user could reach for, not
a design TCW should adopt — it rewrites the item's branch history to dodge a
confirmation prompt.

## Meta changes

None expected. This is a defect in one existing function's Git invocation, not a
change to the lifecycle model, the store interface, or the worktree ownership
split.

## Constraints

- **Fail closed on real conflicts.** Whatever changes, an unmergeable branch must
  still leave the branch and worktree intact, keep the item `active`, abort the
  half-merge, and report. `tests/test_recursion.py::test_complete_aborts_on_merge_conflict`
  is the standing guard on that and must keep passing unmodified.
- Do not change where transitions happen. Status moves stay on the primary
  checkout and edits ride the branch; that split is the documented model and is
  explicitly out of scope here (see below).
- Do not rewrite branch history as part of `complete`.

## Out of scope

- Reconsidering the lifecycle ordering that lets a transition on the primary
  checkout straddle artifacts committed on the branch. The user scoped this item
  to the merge-back itself; if the ordering is the deeper problem, that is a
  separate item.
- `tcw/work/cli.py`'s `_ERRORS` gap, where `reconcile --commit` raises an uncaught
  `subprocess.CalledProcessError` on a refused commit. A real but unrelated defect
  found in the same session; it needs its own item.

## References

- `2026-08-12-honor-the-configured-work-path-at-every-work-store-call-site` — the
  live reproduction. That item was driven through `--worktree`, its `outcome.md`
  was committed on the branch, and `submit` then moved it to `review/` on `main`;
  the two merge runs quoted above were both performed against its real branch.
  Its `outcome.md` records the conflict under "Notes".

## Notes

- Written from a reproduction observed directly in-session rather than from a bug
  report, so the trigger and the flag behaviour are verified rather than inferred.
- The blast radius is every `--worktree` user, not only users with an external
  `work.path`: the reproduction used the default in-repository `docs/work` layout.
