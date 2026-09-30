# Let the worktree merge-back wait out a store commit's index.lock

Follow-up from #73 (one store lock).

Store commands now retry for up to 2 s while another process holds
`index.lock` (`_git_index`), so a store commit that meets `merge_worktree` waits
it out. The reverse is not covered: `merge_worktree` runs plain `git merge`,
which fails at once if a store commit in another session holds the index at
that moment. It cannot take the store lock (it can run long), but it could use
the same retry.

Also from review: three places repeat "write the item's fields, then commit
that folder" — `commit_claim`, `_start_locked`'s take-over, and the CLI's
`start --worktree` — and could share one store method.
