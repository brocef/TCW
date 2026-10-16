# Let the worktree merge-back wait out a store commit's index.lock

## What is wanted

Two sessions working at once should not make a worktree merge-back fail merely
because the other session is in the middle of a store commit.

Since #73, store commands retry for up to 2 seconds while another process holds
git's `index.lock` (`_git_index`), so a store commit that meets a merge-back
waits it out. The reverse is not covered: `merge_worktree` runs a plain
`git merge`, which fails at once if a store commit in another session holds the
index at that moment. The merge-back cannot take the store lock, because it can
run for a long time, but it could retry the same way.

**Decided with the maintainer at triage:** also in this item, the tidy-up the
#73 review found. Three places repeat "write the item's fields, then commit that
folder" (`commit_claim`, `_start_locked`'s take-over, and the CLI's
`start --worktree`) and should share one store method.

## Notes

- Follow-up from #73 (one store lock).
- Reference material: asked; none provided beyond the entry.
