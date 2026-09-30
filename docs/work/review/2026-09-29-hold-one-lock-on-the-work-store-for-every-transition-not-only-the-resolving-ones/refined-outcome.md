# Refined outcome

**Accepted.** One store lock covers every writer from check through commit.
It sits in the repository's git folder, is keyed by the working tree's own git
folder, is reentrant within a thread, and names its holder on a timeout. Pushes
and fetches run outside it, and git index commands wait out another process's
`index.lock`.

## Evidence

- **Full suite, bare `pytest` at `dc62aba3`:** 5185 passed, 3 skipped, 0
  failed. This branch had merged main after the other seven items of the
  batch, so this is the combined run for all eight.
- **`tcw:verifier`:** criteria 1-6 met, each with named tests; 277 focused tests
  passed.
- **Hands-on, the plan's own check.** Three shells looped start, submit and
  complete over 18 items of one scratch store, while a fourth shell ran 60 plain
  `git commit`s:
  - no failures;
  - 18 completion commits;
  - no commit that holds two items' files;
  - nothing left staged.

## Found at verify, fixed

- **The first run of the hands-on check failed.** Two `start` commits failed
  on `index.lock`: the other git process released the lock between the failure
  and the retry's check, so nothing retried. Index commands now also retry on
  git's exit status 128, the status of a lock git could not create
  (`a2ce9a39`, with tests).
  - A refusing `pre-commit` hook exits 1 and is never run twice.
  - Any other fatal git error is reported about 2 s later than before.
  - The run above was made after this fix.
- **Creation staged its files outside the lock.** It now stages and commits in
  one locked span, so a whole-store `reconcile --commit` cannot carry them.
- **`rename`'s repoint on another board** takes that board's lock.
- **Two stale docstrings** were corrected (`dc62aba3`).

## Deferred

- **Closing GitHub issue #73 waits for publication.** The order is: complete
  the batch → cut the version → push → answer and close, with the reply text
  approved first.
- **Inbox follow-up:** the merge-back and the index retry, and one shared
  "commit this item's folder" method.
