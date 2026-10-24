---
verdict: rejected
judges: 1
---

# Review round 1 — TCW-116

Reviewed by two separate read-only agents (the `tcw:reviewer` agent), one on
the file migration and the departures from the spec, one on the Jira side,
on 2026-10-24 in a frozen worktree at `029455f8`, branch `v4` with TCW-116
landed after its rebase onto `f1755e1b` (TCW-113 completed), over
`f1755e1b..029455f8`. The dispatching session checked each finding against
the code before writing this round.

## Checks run

- The full suite as CI runs it, run by the dispatching session on the
  rebased branch at `6c16a8d2` in two halves by folder, every `TCW_*`
  variable unset: `2246 passed, 2 skipped` and `5474 passed, 111 skipped,
  1 failed`; the failure is the worktree's `node_modules` link, and the same
  file in `v4` gives `120 passed`. `pnpm test` `247 passed`; `tsc --noEmit`,
  `pnpm lint`, `pnpm check:build` clean.
- By the reviewers: `tests/migrate` `314 passed`; the Jira migrate tests
  `116 passed`; `tests/work/jira/` `825 passed, 2 skipped`; a scratch test
  against the stand-in Jira, `3 passed`; three mutation checks in a scratch
  copy, each red.
- By hand, through a guarded wrapper with every `TCW_*` variable unset and
  scratch home folders, no live Jira: a scratch 3.x project made with 3.0.2
  migrates (the dry run changes nothing; the run passes 4.0 `tcw validate`
  with no findings; a second run has nothing to migrate); a read-only folder
  stops the run and a re-run gives files identical to an uninterrupted run;
  a hand-edited file is refused before any write (B17); a clone of this
  repository migrates with `--no-jira` (296 written, 2 moved, 231 deleted)
  and validates clean. Each deleted file is removed only after its 4.0 copy
  is written and only while it matches its recorded digest.

## Acceptance criteria

The file-side criteria 1 to 54 and 57 to 69 are met, by their tests or by
hand, except as finding 1 says for 50; 53's live dry run, 55 and 56 are not
checkable here and fall to TCW-118 and the user. The Jira-side criteria 5,
6, 10 to 12, 14, 43, 44, 50, 57 to 59, 65, 66 and 68 are met: the dry run
plans through a client that allows only reads; `--no-jira` builds no client
and reads no credential; only the project's own credentials are used and
none is printed or recorded; tickets are edited only after every file change
succeeded; a ticket edited by someone else is named and never overwritten.

The four departures recorded in implement round 1 are each right, and each
is a spec defect: criterion 46 contradicted TCW-106 Design 4.2; criterion
64's rename case cannot happen because 4.0 refuses to move an override, and
both halves it meant are tested; emptied override folders must go, or
criterion 51 fails, and the removal is narrow; and a second person's
absolute paths cannot be recovered, so Design 2.11 promised too much (but
see finding 1).

## Findings

1. `tcw/migrate/config.py:609-613` and `:619-621`: an absolute path that the
   3.x shared file held for everyone (M1, M4) is moved only into this
   person's untracked `.tcw/tcw-manifest.local.yaml`, and the run says
   nothing. Another person who clones is refused ("not on this machine")
   and their own `tcw migrate` says "nothing to migrate".
2. `tcw/migrate/jira.py:161-166`: `edited_tickets` reads only `edit` lines,
   so a ticket whose edit Jira applied but whose answer was lost, listed
   under "not done", is left out of the way back; the re-run skips it as
   already converted. Shown with the stand-in.
3. `tcw/migrate/jira.py:169-181`: `restore_tickets` raises when it leaves any
   ticket out, so the list of tickets it did put back is lost.

## Needs a separate change

For TCW-118's gate 2, decided by the dispatching session and posted on its
ticket: the way back lives only in 4.0, so it runs before 3.0.2 is
reinstalled; the edits do not slow down when Jira limits requests (a re-run
finishes them); and on a real test project, check that the edit is accepted
for every issue type, whether each edit emails watchers, the search index
lag after the run, and the way back with one ticket edited by hand.

## What implement must do

- (a) Report each M1 and M4 path a run moves into the personal manifest,
  naming the entry and the file and saying that every other person must add
  their own entry, with a test; correct the round's note that only M5 is
  recovered.
- (b) The way back also offers the tickets a run listed as not done (the
  restore edits only a ticket that still holds the 4.0 value, so offering
  one that was never edited is harmless), with a test using the stand-in's
  lost-answer case.
- (c) `restore_tickets` reports the tickets it put back even when it leaves
  some out, with a test.
- (d) `implement/round-2.md`.
