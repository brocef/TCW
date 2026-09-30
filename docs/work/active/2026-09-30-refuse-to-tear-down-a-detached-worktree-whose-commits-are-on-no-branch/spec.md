# Spec: Refuse to tear down a detached worktree whose commits are on no branch

_Compressed spec, agreed with the maintainer for a small fix._

## Capability changes

None. `cli/run-from-a-git-worktree` and the worktree flow keep their status; this
makes an existing command safer.

## Problem

`tcw work start --worktree` makes `.worktrees/<slug>/` on branch `work/<slug>`
(`add_worktree`, `tcw/store/fs.py:1007`). If the user later detaches that
worktree's `HEAD` (`git checkout <commit>`, `git switch --detach`, a rebase left
half-done) and commits there, those commits are on no branch.

`tcw work complete` then:

- merges only the **branch** `work/<slug>` (`merge_worktree`, `tcw/store/fs.py:1073`),
  so the detached commits are not merged; or, under `--already-integrated`,
  checks only the branch (`branch_integration`, `tcw/store/fs.py:1123`);
- removes the worktree with `git worktree remove` (`remove_worktree`,
  `tcw/store/fs.py:1177`, called from `tcw/work/cli.py:4514`). That refuses a
  worktree with uncommitted changes, but removes a clean detached one;
- for a completion, force-deletes the branch (`git branch -D`).

The detached commits are then reachable only from git's reflog. Nothing says so.
A discard also removes the worktree (without deleting the branch), with the same
loss.

## Goals

1. A **completion** (`--resolution done`, either route: merge-back or
   `--already-integrated`) of a worktree item whose worktree holds commits no
   branch, tag or remote-tracking branch contains is **refused before anything
   changes**: the item, its branch and its worktree stay exactly as they were.
   The refusal names the worktree, the commits (short hashes), why they would be
   lost, and how to save them (`git -C <worktree> branch <name>`, then merge
   into `work/<slug>` if they belong to this item).
2. A **discard** is not refused: abandoning work already keeps the unmerged
   branch (`tcw/work/cli.py:4505-4513`), and it keeps such a worktree the same
   way. The item is discarded, the worktree is **left in place**, and a warning
   names the commits and how to save them before removing it by hand.
3. `remove_worktree` itself never removes a worktree holding such commits, so
   any future caller inherits the protection.

## Non-goals

- Detached worktrees whose `HEAD` is contained in some ref: nothing is lost, so
  nothing changes.
- Uncommitted changes: `git worktree remove` already refuses them.
- Making the merge-back carry detached commits. Which commits belong to the item
  is the user's call.
- Worktrees TCW did not create.

## Design

"Would be lost" means: reachable from the worktree's `HEAD` and from no local
branch, tag or remote-tracking branch —
`git -C <worktree> rev-list HEAD --not --branches --tags --remotes`. The request
said "no branch"; tags and remote-tracking branches are included because a commit
they hold is not lost either, and refusing over it would be a false alarm.
`--all` cannot be used: it counts every worktree's `HEAD`, including this one.

A new helper beside `remove_worktree` in `tcw/store/fs.py` returns those commits
for a worktree folder, an empty list when the folder does not exist, and fails
closed (a reason string) when git cannot answer for a folder that does exist.
Worktrees are a filesystem-adapter detail with no store-interface analog, so the
helper stays a module function in `fs.py`, like its neighbours; nothing is added
to the abstract store.

`_complete` calls it for a worktree item alongside the other checks that run
before the merge-back. `remove_worktree` calls it first and returns a warning
instead of removing.

## Acceptance criteria

1. A worktree item whose worktree is detached at a new commit on no ref:
   `tcw work complete <slug> --resolution done --confirm` exits 1; the message
   names the commit's short hash and the worktree path; afterwards the item's
   status, the branch `work/<slug>`, the worktree folder and the detached commit
   are all unchanged.
2. The same with `--already-integrated`: same refusal, same nothing-changed.
3. The same with `--resolution wontfix --confirm`: the item is discarded (exit
   0), the worktree folder still exists, and stderr names the commit.
4. A detached worktree whose `HEAD` is contained in `work/<slug>`: completion
   proceeds exactly as today (worktree removed, branch deleted).
5. After the commit is saved on a branch (`git -C <wt> branch keep`), the
   completion of criterion 1 succeeds and branch `keep` still exists.
6. `remove_worktree` called directly on such a worktree returns a warning and
   leaves the folder.

## Risks

- A repository with a very large number of refs makes the `rev-list` slower; it
  runs once per completion of a worktree item, which is acceptable.
- A worktree folder that exists but is not a git worktree any more: git errors,
  and the helper fails closed, so completion refuses. The message must say git
  could not check, not claim commits exist.

## Notes

- Found by the adversarial review of #72; the defect predates that change.
- The refusal-versus-rescue-branch choice was made by the maintainer at triage
  (refuse and explain).
