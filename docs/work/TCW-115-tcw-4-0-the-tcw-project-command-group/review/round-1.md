---
verdict: rejected
judges: 1
---

# Review round 1 — TCW-115

Reviewed by a separate read-only agent (the `tcw:reviewer` agent) on
2026-10-24 in a frozen worktree at `38f582b5`, the head of the item's branch
rebased onto `v4` after TCW-114 completed, over the 14 TCW-115 commits. The
item was reviewed on its branch before landing, because TCW-113 lands in `v4`
first. The dispatching session checked each finding against the code before
writing this round.

## Checks run

- The full suite as CI runs it, `.venv/bin/pytest -q -p no:cacheprovider`,
  run by the dispatching session on the branch at `38f582b5` in two halves by
  folder: `2078 passed, 2 skipped` and `4975 passed, 111 skipped`. `pnpm test`
  `198 passed`; `tsc --noEmit`, `pnpm lint`, `pnpm check:build` clean.
- By the reviewer: the item's own and central test files, `1253 passed,
  28 skipped`, `195 passed` and `360 passed`; the provisioning files skipped
  nothing, so AC 36 (e) ran on macOS.
- By hand, through a guarded wrapper with every `TCW_*` variable unset and
  scratch home folders, cloning only local scratch repositories: the four
  removed commands exit 2 naming their replacement; a single project has
  nothing to fetch; `../../far` and `..` are refused naming the bound and the
  `-C` way out, `../sib` is fetched; `--template=` and `#--orphan` addresses
  are refused by TCW-107's reader; an occupied folder is left unchanged and a
  folder holding only `.git` untouched; an empty folder is cloned into; an
  interrupt during a clone removes its staging folder and leaves nothing at
  the target.

## Acceptance criteria

AC 1 to 38 and 40 are met by their named tests, AC 2, 3, 24, 34 and 37 also
by hand, except that AC 32 holds only when one project is fetched (finding
1). AC 39 is the suite run. Provisioning safety holds: every git call goes
through one helper with `git_environment()`; the placement bound resolves the
holding folder strictly and compares by identity; staging uses an exclusive
folder and a rename after an empty-or-absent check; a clone never overwrites
or deletes a person's files. The 8 removed tests are each replaced or
justified. The implementing agent's decisions are sound, and the
`test_git_write_scan` allowance is narrow (`fetch_project: {clone}`).

Two places where the documentation followed the code over the spec, judged:
only taxonomy and capabilities stores are opened through a locator for
another project, so "never a work store" is true in this tree; and the
suggestion order (shared leading words, then depth) was already in the code
on `v4` before this item and gives the spec's table. Neither is a defect of
this change.

## Findings

1. `tcw/provision.py:533-540`: Design 7.11's refusal names `fetched_here[-1]`,
   the last project fetched, not the one whose manifest has the problem.
   With parents `aa` and `bb`, where `aa`'s committed manifest has an unknown
   key, it says `bb: fetched into <D>/bb, but <D>/aa/.tcw/tcw-manifest.yaml:
   … remove <D>/bb to undo the fetch`, telling the person to delete the
   wrong clone.
2. `implement/round-1.md:16-31`: the commit table cites the hashes from
   before the rebase onto `v4`, which are not on the branch.
3. `tcw/provision.py:213`, `_folder_state`: `os.scandir` on an unreadable
   target folder raises `PermissionError` and prints a traceback instead of a
   refusal. Folded in by the dispatching session as a small follow-up.

## Needs a separate change

To be checked when TCW-113 and TCW-115 are reviewed together in `v4`: TCW-113
opens a descendant's work store with no locator (`tcw/work/scoped.py:96` on
its branch), so a child whose work store is declared but not fetched would be
told `run tcw project provision --component work`, which, run in the active
project, fetches the active project's own store (Design 7.2).

## What implement must do

- (a) Name, in the 7.11 refusal, the fetched project whose folder holds the
  file with the problem, falling back to the general text when none does,
  with an AC 32 test fetching two projects in one round.
- (b) Refuse an unreadable target folder with a plain message, with a test.
- (c) Correct the commit table in `implement/round-1.md` and write
  `implement/round-2.md`.
