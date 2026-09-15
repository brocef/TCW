# Implementation plan

Five ordered tasks, one commit each, suite green at every boundary.

The ordering is chosen so the riskiest change — auto-commit, which alters what
every transition does to the repository — lands **second**, after its
infrastructure exists and with its own test file already in place. Task 1 builds
the machinery without switching it on.

## Task 1 — commit plumbing, off by default

Everything auto-commit needs, wired to a flag that is `false` at this point. No
observable behavior change.

- `git_commit_result(node_root, message, *paths) -> str | None` beside the
  existing `git_commit` in `fs.py`. Returns `None` on success or on either benign
  condition; returns an error message on a real failure. It classifies:

  | Condition | Detection | Return |
  |---|---|---|
  | Not a repo | `git rev-parse --git-dir` non-zero | `None` |
  | Nothing to commit | `git commit` non-zero **and** output matches nothing-to-commit | `None` |
  | Anything else | `git commit` non-zero otherwise | the message |

  **Resolved during implementation: do not match git's output at all.** Probing
  the real cases showed *three* distinct benign sentences, all localized and all
  version-dependent. `git status --porcelain` is the stable signal — it exits 0
  even for a pathspec git has never heard of. Two further findings, both from
  running it rather than reasoning about it: untracked (`??`) entries must be
  excluded, because a scoped commit records tracked content only; and pathspecs
  must be filtered individually, because `git commit` fails outright if *any* one
  of them matches nothing — which is exactly what a transition's vacated source
  folder does.

- `FsWorkStore._auto_commit_enabled()` reading `work.auto-commit-transitions`
  through the existing `_config()`, defaulting to `True`. Not yet consulted.
- `FsWorkStore._trunk_branch()` reading `work.trunk-branch`, default `None`.

**Test:** `tests/test_work_autocommit.py` covering `git_commit_result`'s three
outcomes directly — including the real-failure path, driven by holding
`.git/index.lock` — plus config defaults and absence.

**Green when:** the new helper is fully tested and nothing else in the suite
changed behavior.

## Task 2 — switch auto-commit on

The behavior change, isolated to one method and one flag flip.

```python
def _effect_transition(self, slug: str, to_status: str) -> None:
    src = self._find(slug)
    dst = self.root / to_status / slug
    (self.root / to_status).mkdir(parents=True, exist_ok=True)
    self._mv(src, dst)
    if self._auto_commit_enabled():
        self._commit_transition(slug, src, dst, to_status)
```

`_commit_transition` resolves both paths relative to `node_root`, calls
`git_commit_result`, and on a real failure raises so the caller reports it. The
move is **not** rolled back.

**How the failure surfaces matters and is easy to get wrong.** `_effect_transition`
returns `None` and is called from `transition()` deep inside the store. Raising is
the only way the CLI hears about it — but a bare exception would read as "the
transition failed", which is false. Define `TransitionCommitError` in `base.py`
carrying the message and the fact that **the move succeeded**, and have the CLI
print it and exit non-zero without implying the item did not move.

- `work.trunk-branch`: compare against `git rev-parse --abbrev-ref HEAD` before
  committing. On mismatch, warn once naming both branches. Suppress when the
  item's own `branch` field equals `HEAD`, which needs the item — read it before
  the move, since afterwards `_find` points elsewhere.
- Flip the default to `True`.

**Tests** extend `tests/test_work_autocommit.py`:

- Each of `start`, `submit`, `rework`, `complete --resolution done`,
  `complete --resolution wontfix` leaves exactly one new commit.
- **The scoping test, which is the one that matters:** modify a *different*
  item's `spec.md`, transition this one, assert the other file is still dirty
  afterwards. A broad pathspec passes every other test in this file and fails
  only this one.
- `auto-commit-transitions: false` leaves the move staged and uncommitted.
- Transitioning twice — the second finding nothing to commit — does not raise
  and creates no empty commit.
- A store on a non-repo directory fails at *creation*, as it always has —
  pinned as pre-existing behavior, not fixed. `git_commit_result`'s not-a-repo
  branch stays as defensive depth and is tested directly.
- A rejecting **pre-commit hook** produces `TransitionCommitError` with the item
  **moved**. Not a held `index.lock`: the lock blocks `git mv` too, so the move
  would never happen and the case under test could not arise. (`index.lock` still
  drives the unit-level test of `git_commit_result`, where no move is involved.)
- `trunk-branch` matching / mismatching / suppressed-in-worktree.

Existing tests that transition items now produce commits. Most use `tmp_path`
git repos and will not care, but **check for tests asserting a clean or dirty
tree** before assuming the suite absorbs this.

## Task 3 — `--worktree` stops double-committing

`_start`'s worktree branch currently commits `"docs/work", ".gitignore"` before
`add_worktree`. The status move is now already committed by the store, so that
call must narrow to what remains uncommitted: `.gitignore` and the item's
`state.yaml`, which `_start` writes *after* the transition.

The ordering constraint is unchanged and load-bearing: the worktree branch is
created from `HEAD`, so both commits must land before `add_worktree`.

**`--worktree` commits regardless of `auto-commit-transitions`.** With the
setting off the store does not commit the move, and the branch would then be
created without it — producing a worktree whose own item is not on it. `_start`
therefore commits the move itself when the setting is off. Documented as an
exception rather than left to be discovered.

**Tests:** `--worktree` with the setting on (one commit for the move from the
store, one for the fields from `_start`, no empty commit) and off (the move
still committed, by `_start`). Assert the branch contains the status move in
both.

## Task 4 — stop persisting `dod:`

- Drop `self.set_field(slug, "dod", dod_ack)` from `WorkStore.complete()`.
  `dod_ack` stays in the signature — removing it is an interface change for no
  gain, and a remote adapter may have somewhere to put it.
- `_complete` keeps printing the checklist before `--confirm`. That is the only
  thing it ever did.

Follows child 1's `phase` precedent exactly: the key becomes unread, existing
items keep it inertly, and no migration pass is added.

**Test:** a newly completed item has no `dod:`; an item whose `state.yaml`
carries one loads and completes normally.

## Task 5 — `tcw work complete --already-integrated`

Narrower than it looks. `_complete` already does merge-back conditionally
(`work/cli.py:652`), so this is one more condition on an existing branch:

```python
if shipping and has_worktree and branch and not args.already_integrated:
    err = merge_worktree(...)
```

Everything after it is untouched — the capabilities gate, `complete()`, and
teardown all run as they do today. `remove_worktree` is already best-effort and
`merge_worktree` already treats a missing branch as a no-op, so tolerance of
prior external cleanup mostly exists; the task is to confirm it rather than
build it.

Two guards worth adding:

- **Reject `--already-integrated` on an item with no worktree** — it means the
  caller misunderstands the flag, and silently accepting it teaches the wrong
  model.
- **Skip the "branch was not merged" warning** on this path. It is emitted for
  discards today; on an `--already-integrated` completion the branch *was*
  merged, just not by TCW.

**Tests:** merge is skipped; every other gate still runs (assert the capability
gate still refuses); an already-deleted worktree and branch are tolerated; the
flag is rejected without a worktree.

## Task 6 — documentation sync

| Entry | Fires | Why |
|---|---|---|
| `README.md` | yes | Transitions now commit; two new config keys; a new flag. |
| `docs/release-notes/upcoming.md` | yes | **The largest behavior change in the epic.** |
| `docs/changelogs/upcoming.md` | yes | Code change. |
| `skills/tcw-work/SKILL.md` | yes | The lifecycle handshake's commit guidance is now partly wrong. |

**The skill needs more than a mention.** It currently instructs the agent to
commit transitions by hand — "commit the `start` move after the separate
`plan.md` checkpoint" — and repeats that guidance in several places. Those
instructions become wrong, not merely incomplete: following them produces an
empty commit or a confusing second one. Every such instruction has to be found
and corrected, which is a grep, not a skim.

Keep it minimal in every other respect: child 4 restructures the skill wholesale.

**The release note leads with auto-commit.** It changes what every `tcw work`
command does to the repository, including from the web app, for every existing
user. It needs plain language, the `auto-commit-transitions: false` escape
hatch, and an explicit note that `tcw serve` now commits too.

## Verification

1. `tcw validate` on this repo.
2. Drive a scratch item through every transition in a real repo and inspect
   `git log --stat` — confirming each commit contains only the moved item.
3. Dirty an unrelated work item, transition another, confirm the dirt survives.
4. `tcw serve`, transition an item from the web UI, confirm a commit appears.
5. `start --worktree` end to end, confirming the branch carries its own status
   move and teardown still works.

## Rollback

Tasks 2 and 3 are coupled — reverting auto-commit without reverting task 3
leaves `--worktree` committing nothing for the move. Revert both or neither.
Tasks 1, 4, and 5 are independent.
