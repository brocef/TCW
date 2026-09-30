# Refuse to tear down a detached worktree whose commits are on no branch

## What is wanted

`tcw work complete` must not silently lose commits when it removes an item's
worktree.

`remove_worktree` runs `git worktree remove`, which refuses a worktree with
uncommitted changes but removes a clean one whose `HEAD` is detached (not on any
branch). Commits made on that detached `HEAD` and never put on a branch are then
reachable only from git's reflog, and are gone from the user's view. Both the
ordinary merge-back route and `--already-integrated` reach this.

**Decided with the maintainer at triage:** when the worktree's `HEAD` is detached
at commits that no branch contains, `complete` **refuses** the teardown and
explains: it names the commits that would be lost and tells the user how to put
them on a branch. It does not create a rescue branch on the user's behalf.

## Notes

- Found by the adversarial review of
  `2026-09-29-let-complete-already-integrated-check-a-branch-worked-in-a-worktree-tcw-did-not-create`
  (#72); the defect is older than that change.
- Reference material: asked; none provided beyond the entry.
