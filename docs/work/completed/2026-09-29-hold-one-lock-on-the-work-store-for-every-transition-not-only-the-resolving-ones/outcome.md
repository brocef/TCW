# Outcome

Every writer of a work store now holds one lock, `FsWorkStore._store_lock`,
from its check through its commit:
- every transition;
- `start`'s claims;
- the tombstone writers;
- the commit step of creation;
- tracker claims;
- `reconcile --commit`;
- `start --worktree`'s commits.

**Where the lock lives:** in the repository's git folder, keyed by the working
tree's own git folder, so every session and every store sharing that index
shares it, whatever `TMPDIR` is.

**How it behaves:**
- It is reentrant within a thread.
- The holder writes its process id and command into the lock file, and a
  waiter that times out names it.
- Fetch and push run outside the lock.
- Git index commands retry for up to 2 s while another process's
  `index.lock` exists, and name a lock that outlives the wait.

## What shipped

| Task | Commit |
| --- | --- |
| The lock, every writer, publishing after release, `commit_claim`, the index retry | `0e7e8f02` |
| `tests/test_store_lock.py` | `c248c4fc` |
| Documentation: capability `work/share-a-work-store-between-sessions`, guide, skill, changelog, release notes | `c0bb882d` |
| Review fixes | `b1ae7b24` |
| Merge of main (#70's rename moved onto `_store_lock`, the alias removed) | `0af5011a` |

## Tests

- **`tests/test_store_lock.py`: 12 tests.** Each was mutation-checked, and
  both race tests fail when the lock is replaced by no lock.
  - Criterion 1: 20 rounds of two processes, for `start` and for `submit`.
  - Criteria 2 and 3: where the lock lives, `TMPDIR`, and the holder named on
    timeout, with nothing changed.
  - Criterion 4: reentrancy, and another thread waiting.
  - Criterion 5: the push outside the lock.
  - Criterion 6: a brief foreign `index.lock` waited out, and a stale one named
    on the terminal.
  - From review: a creation kept waiting is left staged; stores sharing a git
    folder share the lock; `commit_claim` is not abstract.
- **Full suite:** see `refined-outcome.md`. It is the combined run of all eight
  items in this batch, since this branch merged main after the other seven.

## What the plan or spec got wrong

- **The failing tests were not committed first.** Plan Task 1 said to commit
  them marked as expected failures; they came after the implementation. The
  race tests were then checked against the unlocked code by mutation, which
  shows they detect the original bug.
- **Criterion 5 named a slow `pre-receive` hook.** The test replaces `publish`
  with a stand-in that tries the lock from another thread, which tests the
  property directly and quickly.
- **The spec said "no method" on the base class.** `commit_claim` was added,
  with a default, because the CLI's tracker claim now calls it.
- **The spec said the index retry covers the merge-back's collisions.** It
  covers only a store command meeting the merge-back's `index.lock`. Recorded
  in the spec's Notes and as a follow-up.
- **The spec keyed the lock by store root.** It is keyed by the working tree's
  git folder, because two stores in one repository share an index.

## Autonomous decisions

- **Review verdict "NOT DONE"** (`adversarial-code-reviewer`). Accepted and
  fixed:
  1. A lock timeout during a creation said "Nothing was changed" after the
     item was written. Now `LockTimeout` is caught and the creation is left
     staged with a warning.
  2. `@abstractmethod` sat on `commit_claim`. It was moved back to
     `artifacts`, where #66 had displaced it from; this was also corrected in
     #58's merge.
  3. git's captured error output was lost. It is printed by the top-level
     handler and in the transition errors.
  4. `reconcile --commit`, whose pathspec is the whole store, is locked.
  5. `start --worktree`'s commits are locked.
  6. The lock is keyed by the working tree's git folder. The reviewer asked
     whether several stores in one repository are in scope; I decided yes,
     since parent and child nodes in one checkout are an existing layout and
     the change costs nothing.

  Also fixed: the weak `submit` race assertion (it now matches `<slug> →
  review` exactly), stale comments, and the documentation claims about
  creation.
- **Moved to a separate change**, agreed with the reviewer and filed:
  - merge-back's own `git merge` using the index retry;
  - one shared "commit this item's folder" method for the three places that
    repeat it.
- **Judged harmless and left:** the holder line can be momentarily empty or
  stale in a timeout message.
- **Moving the fetch out of the lock in `record_tombstone`** was reviewed and
  judged acceptable: the dirty-graveyard check still runs under the lock, so
  the worst case is a spurious refusal.
- **No advisors were consulted at implementation.** The design (a per-thread
  reentrant lock, the git folder, publishing outside, an index retry keyed on
  the lock file) was settled with advisors at the spec stage.
