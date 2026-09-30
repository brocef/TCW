# Plan — Hold one lock on the work store for every transition, not only the resolving ones

Worked in a worktree (`start --worktree`), with a scratch venv pinned to it.
It runs after #66, whose creation commits it must also lock.

## Task 1 — Failing tests

**Creates** `tests/test_store_lock.py`:

- criterion 1: two `subprocess` workers racing `start` and `submit` on two
  items, 20 rounds;
- criterion 2: lock path and `TMPDIR`;
- criterion 3: holder process id in the timeout, with the timeout
  monkeypatched short;
- criterion 4: reentrancy and a second thread;
- criterion 5: push outside the lock, using a bare remote with a sleeping
  `pre-receive` hook;
- criterion 6: a foreign `index.lock`.

All are committed `xfail(strict=True)` except where they pass today.

## Task 2 — The lock

**Modifies** `tcw/store/fs.py`:

- `_graveyard_lock` becomes `_store_lock`, with the git-folder path, the
  temp-folder fallback, per-thread depth, and writing the process id and
  command under the lock;
- `STORE_LOCK_TIMEOUT`, keeping `GRAVEYARD_LOCK_TIMEOUT` as an alias;
- the timeout message.

The docstrings are rewritten. **Proves** criteria 2-4.

## Task 3 — Every writer takes it

**Modifies** `tcw/store/fs.py`:

- `_effect_transition` locks always, with the publish moved after the lock;
- `start`'s commit paths;
- a new `commit_claim` (from `_own_locally`), and `_own_locally` calls it;
- the creation commit method from #66.

**Checks** by grep that no lock holder calls the publish or the fetch. **Proves**
criteria 1 and 5.

## Task 4 — The index retry

**Modifies** `tcw/store/fs.py`: `_git_index`, used by `git_stage`, `git_mv`,
`git_rm` and `git_commit_result`, with the stale-lock sentence. **Proves**
criterion 6.

## Task 5 — Documentation Sync

- `docs/guide/work.md` ("Transitions and commits"): sharing a store, the lock,
  the wait, a slow `pre-commit` hook, and network filesystems.
  [Guide-Topic-Change]
- `skills/work/references/transitions.md`: one sentence saying concurrent
  sessions are safe on one machine, with no external lock needed.
  [Skill-Driven-Component]
- The new capability, and the item's `capabilities.yaml`.
- The changelog, and release notes.

## Task 6 — Full suite

Bare `pytest`, with the venv first on PATH, run twice, since the concurrency
tests are timing-sensitive. **Proves** criterion 7.

## Verification

By hand: three shells on one scratch store, each looping `start`, `submit`
and `complete` over its own items, with a `git commit` loop in a fourth.
Afterwards read `git log --stat` for stray files.
