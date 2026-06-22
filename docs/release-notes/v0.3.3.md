# Upcoming

User-facing release notes for the next version. Plain language — no jargon or
internal module names.

## Fixed

- Finishing a worktree-isolated work item no longer risks losing your code.
  `tcw work complete` now merges the item's work branch back into your main
  checkout before removing the worktree — and if that merge hits a conflict it
  stops cleanly, leaving the branch and worktree in place to resolve and retry,
  instead of deleting the branch and reporting success while the committed work
  quietly vanished.
