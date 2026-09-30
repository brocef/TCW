# Plan: Refuse to tear down a detached worktree whose commits are on no branch

_Compressed plan, agreed with the maintainer for a small fix._

## Tasks

1. **Tests first** — create `tests/test_detached_worktree_teardown.py`, modelled
   on the worktree fixtures in `tests/test_already_integrated_check.py`: start an
   item with `--worktree`, detach its worktree and commit there.
   - completion refused, nothing changed: status, `work/<slug>`, worktree folder,
     commit still reachable by hash from nothing but the worktree (criterion 1);
   - the same under `--already-integrated` (2);
   - discard succeeds, worktree kept, stderr names the commit (3);
   - detached at a commit `work/<slug>` contains: completes as today (4);
   - after `git -C <wt> branch keep`: completes, `keep` survives (5);
   - `remove_worktree` directly: warning, folder kept (6).
   Red before task 2.
2. **Code** — `tcw/store/fs.py`: new `unbranched_commits(worktree) -> list[str] |
   str` beside `remove_worktree` (list of short hashes; `[]` for a missing
   folder; a reason string when git cannot answer). `remove_worktree` returns a
   warning instead of removing when it is non-empty or a reason.
   `tcw/work/cli.py` `_complete`: for a shipping completion of a worktree item,
   refuse before the merge-back (beside the `--already-integrated` check) with
   the worktree path, the hashes and the `git -C <wt> branch <name>` remedy.
   For a discard, the teardown's warning is printed and the worktree kept.
   Proof: task 1 green, suite green under bare `pytest`.

## Documentation Sync

- `docs/changelogs/upcoming/<slug>.md` [Any-Code-Change] — `## Fixed`.
- `docs/release-notes/upcoming/<slug>.md` [Public-API].
- `README.md` [Public-API] — the `complete` row's refusal list gains "a worktree
  holds commits on no branch".
- `skills/work/references/transitions.md` [Skill-Driven-Component] — the
  `complete` gate list gains the refusal (and the discard keeps the worktree).
- `docs/guide/work.md` [Guide-Topic-Change] — the worktree completion text, if
  it describes teardown.

## Verification

- A by-hand run in a scratch project: detach, commit, complete, see the refusal,
  save the commit, complete.
