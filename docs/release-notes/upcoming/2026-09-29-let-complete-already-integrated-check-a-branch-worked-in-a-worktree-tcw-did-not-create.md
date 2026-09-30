## Fixes

- **`tcw work complete --already-integrated` now checks that the branch was
  really merged.** It used to take your word for it and then delete the
  branch, so a branch that had never been merged was lost along with its
  work. Now it looks for the merge in your checkout, including a squashed pull
  request, and refuses if it cannot find one, leaving the item and the branch
  as they were.

## Improvements

- **Worked in a worktree you made yourself?** `tcw work complete <slug>
  --resolution done --confirm --already-integrated --branch <name>` completes
  it once that branch is merged, with the same check. TCW never deletes a
  branch it did not create.
