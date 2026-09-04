Found by an adversarial review of the retention work, 2026-09-04. All three
reproduced.

1. **A failed removal commit reports `removed=False` while the folder is gone,
   and `tcw work delete` then exits 0 on the unfinished removal.**
   `delete_resolved` does `rmtree` → `_write_tombstone(location=…)` →
   `git_commit_result`, raising `TransitionCommitError` if the commit fails.
   `_auto_delete` catches that in `except _ERRORS` and returns `(1, False)` —
   which is exactly the wrong answer the `PublicationError` branch immediately
   above it was added to prevent, and whose own docstring names the consequence:
   *"a caller that read the exit code as 'still there' would print a location for
   a folder that no longer exists."* So `_complete` prints
   `completed <slug> (done) → docs/work/completed/<slug>` for a path that does
   not exist.

   Worse, `_delete` short-circuits on `grave.location` alone — written *before*
   the failed commit — so the recovery verb prints "already removed" and exits 0
   while `git status` still shows an unstaged deletion. That is the one state the
   command exists to finish. Any commit failure reproduces it: a `commit-msg`
   hook, `index.lock`, a missing `user.email`, a signing failure.

   The same early return means a `PublicationError` is never retried by
   `tcw work delete`, though `delete_resolved`'s own comment says a remote left
   holding a deleted item is the divergence publication exists to prevent.

2. **The tombstone can record a commit that never held the item, and the check
   that is supposed to catch it is inert.** `_retained_location` falls back to
   `rev-parse HEAD` when `committed is None`, and `_require_retrievable` — the
   guard that would catch it — is deliberately skipped when the folder is already
   absent. Meanwhile `describe_location` runs
   `git ls-tree <location> -- <self.root.name>`: `self.root.name` is `work`, but
   the pathspec resolves relative to `store_git_root` where the store lives at
   `docs/work`, so it never matches — and it does not matter, because
   `git ls-tree <sha> -- <anything>` exits 0 with empty output regardless. The
   check therefore detects only a *missing* commit object, never one that does
   not contain the item, which is precisely what `Tombstone`'s docstring says
   must not fail silently. Reproduced with the shipped ignore rules, where the
   resolved item is untracked and no commit ever held it: the recorded handle is
   the scaffold commit.

   `test_show_says_when_a_recorded_commit_is_gone` writes `"0"*40`, the one case
   `returncode == 0` does catch, so it cannot detect this.

3. **`delete_resolved` discards the item's real resolution and date when no
   tombstone exists.** It reads `existing.resolution`/`existing.resolved` from
   the graveyard and defaults both to empty when there is no entry, while `item`
   is in scope carrying both. On a board adopting retention before backfilling —
   the migration the README describes — the record lands with an empty
   resolution and today's date. `record_tombstone`'s docstring calls out this
   exact overwrite as worth a dedicated refusal.

Also, cosmetic but in the same line: `_delete`'s already-removed message
interpolates `describe_location` into a preposition, producing
`… remain in last present in commit abc123`.
