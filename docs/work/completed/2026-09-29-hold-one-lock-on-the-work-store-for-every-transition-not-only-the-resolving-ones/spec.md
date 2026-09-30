# Spec — Hold one lock on the work store for every transition, not only the resolving ones

## Capability changes

- **added:** `work/share-a-work-store-between-sessions` — several sessions
  (agents or people) on one machine can change one work store at once. Each
  state-changing command waits its turn, briefly, and commits only its own
  files.

## Problem

Several agent sessions sharing one work store collide. On tcw 2.6.4 a run of
three concurrent sessions hit `.git/index.lock` failures, and one session's
staged files were swept into another's commit. Only an external `mkdir` lock
script, wrapped around every state-changing command, stopped it, and every new
agent had to be told about that script.

Today (fs.py):

- Transitions already commit only the paths they touched.
- A lock, `_graveyard_lock`, exists. It is an `flock` on a file in the system
  temp folder, keyed by the store's path, with a 30-second wait. It is taken
  only by resolving transitions, `record_tombstone` and `delete_resolved`.
  - `start`, `submit` and `rework` run unlocked, and so does the claim commit
    `_own_locally` makes from the CLI.
  - A resolving transition's `git push` (`_publish_after_transition`) runs
    inside the lock, so a slow remote holds everyone else up.
- The lock file lives in `tempfile.gettempdir()`. Two sessions with different
  `TMPDIR` values, which Claude Code gives every session, do not exclude each
  other at all.
- A git command refused because some other git process holds
  `.git/index.lock`, such as a session's own `git commit`, fails at once.

## Goals

1. **One store lock**, `_store_lock`, replacing `_graveyard_lock`. Every
   store operation that writes and commits takes it, for its check, write and
   commit, and nothing longer:
   - every transition in `_effect_transition`, not only resolving ones;
   - the commit paths of `start` (the claim, the take-over, and the backlog
     claim);
   - `record_tombstone`, `delete_resolved`;
   - the claim commit now in `_own_locally`, moved into a store method;
   - the creation commits added by
     `2026-09-29-make-work-new-and-work-escalate-commit-their-own-files-as-status-moves-do`.
2. **The lock file lives in the repository's git folder**:
   `<git common dir>/tcw-store-<key>.lock`, where the key is a hash of the
   store root. It is shared by every session and every worktree of that
   repository, whatever `TMPDIR` is. It is never tracked, since git never looks
   inside its own folder. Outside a repository it falls back to the temp
   folder, as today.
3. **Reentrant within one thread.** A thread that holds the lock may take it
   again (a per-thread depth count), so a store helper that locks can be called
   from another that already does. Other threads and processes still wait: the
   web app serves each request on its own thread, and each takes `flock` on
   its own open file.
4. **A bounded wait with a clear message.** The wait stays at 30 seconds.
   After taking the lock, the holder writes its process id and command into the
   lock file. The file is opened for appending, so a waiter never wipes it. On
   timeout the message names the store, the holder's process id and command if
   readable, and says that nothing was changed.
5. **Network calls are outside the lock.** The publish (`git push`) after a
   transition, and the refresh (`fetch`) before one, run without it. So do
   hooks, tracker calls and the worktree merge-back, which live in the CLI
   anyway.
6. **A short retry on another git process's `index.lock`.** When a git command
   that touches the index (`add`, `mv`, `rm`, `commit`) fails and
   `git rev-parse --git-path index.lock` exists, it is retried for up to about
   2 seconds. The check is for the file, never for git's error text, which is
   translated and changes between versions. If the lock outlives that, the
   existing error is raised, with a sentence naming the lock file and saying
   that a lock left behind by a crashed git must be deleted by hand.

## Non-goals

- **Across machines.** Two clones on two machines end in a git merge, as today.
- **The worktree merge-back** (`merge_worktree`) under the lock. It works in
  the code repository and can take a long time. The index retry covers its
  collisions with a store commit.
- **A lock in the store's interface.** The lock is the filesystem adapter's own
  way of keeping its writes apart. A database-backed store would use a
  transaction.

## Design

- `FsWorkStore._store_lock()`: a context manager.
  - It keeps a per-thread depth count, and only the outermost call opens,
    locks and unlocks.
  - It opens the lock path with `"a+"`, takes `flock`, then truncates and writes
    `pid command`.
  - The timeout reads the file for the message.
- `GRAVEYARD_LOCK_TIMEOUT` becomes `STORE_LOCK_TIMEOUT`, keeping the old name
  as an alias, since tests monkeypatch it.
- `_effect_transition` takes the lock unconditionally. `_publish_after_transition`
  moves after the `with` block.
- `start`'s commit paths and a new `FsWorkStore.commit_claim(...)` (the body of
  `_own_locally`) take it.
- `_git_index(...)`, a wrapper for index-touching git calls, does the retry.
  `git_stage`, `git_mv`, `git_rm` and `git_commit_result` use it.
- The docstrings that say "not reentrant" and "every acquirer is top-level" are
  rewritten.

Litmus: serializing writes is an adapter concern. The base class gains one
sentence in its docs, "an adapter keeps concurrent state changes on one store
apart", and no method.

## Acceptance criteria

1. Two processes run `tcw work start` on two different items of one store at
   the same moment, 20 times over. Every run gives two commits, each holding
   only its own item, with no `index.lock` error. The same for `submit`.
2. The lock file is in `git rev-parse --git-common-dir`, not in the temp
   folder, and two processes with different `TMPDIR` values exclude each
   other. The test holds the lock in one process and shows the other waits.
3. A process holding the lock past the timeout: the other's message names the
   holder's process id, and nothing changed.
4. A thread that holds the lock takes it again without waiting (reentrancy),
   and a second thread waits.
5. A resolving transition with a slow `git push`, faked with a remote hook
   that sleeps: another session's `start` does not wait for the push.
6. A foreign `index.lock` removed after 0.5 s: the transition's commit
   succeeds. One left in place: the error names `index.lock` and says to
   delete it by hand.
7. Existing lock tests (`tests/test_*graveyard*`, and any that monkeypatch the
   timeout) pass, updated only for the rename and the lock path. The full
   suite passes as CI runs it.

## Risks

- **A git `pre-commit` hook runs while the lock is held.** A slow hook slows
  every session. That is stated in the guide.
- **`flock` on network filesystems** is unreliable. That is unchanged from
  today, and the docs say so.
- **Per-thread reentrancy hides nothing across threads**: two web requests
  never share a depth count.

## Notes

- Advisors: Opus, and Sonnet in place of Codex (at its usage limit until
  2026-10-03). Both agreed:
  - lock every transition and claim;
  - keep the lock to the check, write and commit;
  - take the push out of it;
  - leave the merge-back out;
  - move `_own_locally` into a store method;
  - detect `index.lock` by the file, not the message.
- **Split on reentrancy.**
  - Sonnet wanted non-reentrant, with a per-thread assertion so that nesting
    fails at once. Opus wanted a per-thread depth count.
  - I took Opus's. Nesting under a lock one already holds is not an error,
    and the non-reentrant rule ("every acquirer is top-level") is what makes
    adding the call sites this item needs fragile.
  - Both agreed a process-wide count would be wrong, because of the web app's
    threads.
- **Split on the `index.lock` retry.** Sonnet said optional, or separate. Opus
  said to apply it to every index-touching command. The issue names
  `index.lock` failures explicitly, so it is in, and in Opus's scope.
- **The lock's location.** Both raised `TMPDIR` as a risk, and neither
  proposed the fix. The git folder location is my own choice. It keeps the
  existing reason for not putting the file in the store (it must not show in
  `git status`), and removes the per-session temp folder problem.

## Notes

- *Corrected at review:* the base class gains a method after all,
  `WorkStore.commit_claim`, with a default that only sets the owner, since
  the CLI's tracker claim now calls it on any store. The litmus sentence is on
  `WorkStore`'s docstring.
- *Corrected at review:* the index retry covers a store command meeting the
  merge-back's `index.lock`, not the reverse; `merge_worktree` runs plain
  git. Recorded as a follow-up.
- *Changed at review:* the lock is keyed by the working tree's git folder, not
  the store root, because two stores in one repository share one index.
