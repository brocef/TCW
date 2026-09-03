Found by an adversarial review of the retention work, 2026-09-03. Reproduced.

1. **`tcw work delete` refuses the state it exists to finish.** `_delete`
   returns 1 when `st.get(bare) is None`, so an item whose folder is gone but
   whose tombstone lacks its `location` can never be completed — the CLI gate
   makes `delete_resolved`'s documented "safe to re-run" unreachable. The tree
   keeps an unstaged deletion forever.

2. **An auto-delete failure swallows the completion's own `post` result and
   skips worktree cleanup.** `_complete` returns from the auto-delete branch
   before `_post_result(post_err, …)`, so a `post` binding failure on the
   completion is discarded, the "completed …" line never prints, and the
   `if has_worktree:` block never runs — `merge_worktree` has already happened,
   so the worktree and branch are orphaned with nothing left to clean them.
   `tcw work delete` does no worktree cleanup either.

3. **A `PublicationError` after a successful deletion turns success into
   failure.** `delete_resolved` publishes; the error is caught by `_ERRORS` in
   `_complete`, so a completion and deletion that both landed exit 1.

4. **`tcw work show --json` on a resolved-and-deleted slug prints the human
   block and exits 0.** The tombstone branch sits before the `--json` branch. A
   caller piping to `jq` gets a parse error on a success exit code; before this
   change it got a clean exit 1.
