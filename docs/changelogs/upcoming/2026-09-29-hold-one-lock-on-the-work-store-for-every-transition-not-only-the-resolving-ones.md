## Changed

- One store lock, `FsWorkStore._store_lock`, replaces `_graveyard_lock` and is
  taken by every writer:
  - every transition, not only resolving ones;
  - `start`'s claims, split into `start` and `_start_locked`;
  - `record_tombstone` and `delete_resolved`;
  - the commit step of `commit_writes`;
  - the new `commit_claim`, which replaces the commit in the CLI's
    `_own_locally`.
- **Where the lock lives:** `<git common dir>/tcw-store-<key>.lock`, keyed by
  the working tree's own git folder — the one holding the index every commit
  contends for — so every session and every store in one working tree share
  it, whatever `TMPDIR` is. Outside a repository it falls back to the temp
  folder, keyed by the store.
- A lock timeout is `FsWorkStore.LockTimeout`, a `ValueError`. `commit_writes`
  catches it and leaves the creation staged with a warning, since the item
  already exists.
- `reconcile --commit`, whose pathspec is the whole store, and the commits
  of `start --worktree` take the lock too.
- A failed git call's captured output is printed by the top-level handler and
  in the transition's error, so the stale `index.lock` advice reaches the
  terminal.
- **Reentrant per thread.** The holder writes its process id and command into
  the lock file, and a waiter that times out names it.
- `STORE_LOCK_TIMEOUT` (30 s); `GRAVEYARD_LOCK_TIMEOUT` remains as the old
  name, and the shorter of the two applies.
- **Nothing slow under the lock.** A transition's publish, a tombstone's
  publish and a removal's publish run after it is released, and
  `record_tombstone` refreshes before taking it.

## Added

- `_git_index`: `git add`, `mv`, `rm` and `commit` retry for up to
  `INDEX_LOCK_RETRY` (2 s) while another process's `index.lock` exists. The
  test is for the file, not git's message. A lock that outlives the wait is
  named in the error, with the advice to delete a stale one by hand.
- `WorkStore.commit_claim`, a default that only sets the owner.
