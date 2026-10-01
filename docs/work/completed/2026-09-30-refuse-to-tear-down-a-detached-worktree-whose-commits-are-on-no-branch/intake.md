## Inbox manifest

- `2026-09-30-a-detached-worktree-s-unbranched-commits-are-lost-at-teardown.md`

## Inbox body

# A detached worktree's commits on no branch are lost when complete tears it down

Found by the adversarial review of
`2026-09-29-let-complete-already-integrated-check-a-branch-worked-in-a-worktree-tcw-did-not-create`
(#72); it predates that change.

`remove_worktree` runs `git worktree remove`, which refuses a dirty tree but
removes a clean one whose `HEAD` is detached. Commits made on that detached
`HEAD` and never put on a branch are then reachable only from the reflog, and
are gone from the user's view. Both the ordinary merge-back route and
`--already-integrated` reach it. Consider refusing teardown when the worktree's
`HEAD` is detached at a commit not contained in any branch.
