# 09 — Worktree isolation and merge-back

`tcw work start --worktree` puts an item on its own git branch in its own
checkout, and `complete` merges it back. This is the highest-blast-radius path in
TCW: it moves directories *and* merges, and its failure mode is silent data loss.

## Functionality covered

- `tcw work start --worktree`
- The merge-back at `tcw work complete`
- `--already-integrated`
- `merge.directoryRenames` handling for lifecycle folder moves
- `tcw work start --owner`, `--take-over`, and claim ownership

## What is tested

| # | Assertion |
| - | --------- |
| 1 | `tcw work start --worktree $SLUG` creates a worktree under the node's worktree directory and a branch named for the item; `git worktree list` shows both. |
| 2 | The item's folder is `active/` **in the worktree**, and the primary checkout is left clean. |
| 3 | Work committed on the branch (a new file in the item folder) is present in the primary checkout **after** `complete`. This is the assertion that catches a dropped merge. |
| 4 | After a successful `complete`, the worktree is removed and the branch is deleted; `git worktree list` and `git branch --list` confirm both. |
| 5 | **The rename/modify case.** The lifecycle moves the item folder (`active/ → review/ → completed/`) while the branch also modified a file inside it. `complete` must merge this cleanly — historically it silently dropped the merge (fixed: `2026-06-21-work-complete-silently-drops-worktree-branch-merge-on-rename-modify-conflict`). Assert the branch's file content survives at the item's **final** path. |
| 6 | A merge that genuinely conflicts leaves the branch **intact**, the primary checkout **not half-merged** (`git status` shows no `MERGING` state), exits non-zero, and the error names the branch. |
| 7 | After a failed merge, re-running `complete` once the conflict is resolved succeeds — the failure is recoverable, not terminal. |
| 8 | `--already-integrated` skips **only** the merge-back; every other gate still applies. Demonstrate with a gate that actually exists — an unresolved blocker, or an epic with open initiative children — **not** with missing artifacts, since no artifact gate exists (scenario 03, assertion 9). |
| 9 | `--already-integrated` on an item whose branch was really merged externally completes and cleans up without attempting a merge. |
| 10 | `tcw work start --owner alice` stamps the claim; `tcw work show` reports the owner. |
| 11 | With no `--owner`, the owner falls back to `TCW_WORK_OWNER`, then to git `user.email`/`user.name`. All three precedence levels asserted. |
| 12 | Starting an item already claimed by another owner is **refused**; `--take-over` replaces the claim and the new owner is recorded. |
| 13 | **The race.** Two `tcw work start` processes launched simultaneously against the same backlog item: exactly one exits 0, the other exits non-zero, and the item ends with exactly one owner. Repeat several times, each round against a **freshly created backlog item** — re-racing the same item after round one tests "both refuse an already-active item", which is a different and much weaker claim. |
| 14 | Running `tcw work complete` from **inside the item's own worktree** is refused. Left alone it exits 0 having done nothing: the merge would be the branch into itself and the teardown would look in the wrong place, reporting a completion that never happened. |
| 15 | A node path **containing a space** works end-to-end: init, new, start `--worktree`, complete. Cheap, and it protects a class of failure this codebase has already been bitten by. |

## Refusals asserted

- conflicting merge leaves everything intact (6)
- `--already-integrated` does not weaken the DoD gate (8)
- claimed item refuses a second start (12)
- exactly one winner in the race (13)

## Explicitly not covered here

Worktrees on a detached HEAD. (Paths containing a space were moved *into* scope
as assertion 15 — a repo path with a space is already a fixed defect elsewhere in
this codebase, so the concern is not hypothetical.)

## Notes for the implementer

**Every `git config` must be set `--local`.** Never read or mutate the developer's
global identity, `init.defaultBranch`, `core.hooksPath`, `commit.gpgsign`, or
`merge.directoryRenames` — assertion 5 depends on the last of those, and a
developer who has overridden it globally must not change this suite's result.

This scenario is slow and destructive by nature. Give it its own temp repo per
assertion group rather than threading one repo through all thirteen — a failure
in assertion 6 otherwise poisons everything after it.

Assertion 13 needs real concurrency: launch both with `&` and collect both exit
codes with `wait -n` / explicit PIDs. Do not simulate it sequentially.

Assertion 5 is the reason this file is long. Reproduce it exactly: commit a
change to a file inside the item folder on the branch, run the transitions that
move the folder on the trunk, then complete.
