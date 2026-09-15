# Rework — Add a tcw-work-create skill that checks for overlap before creating a work item

Decision, 2026-09-15: the user rejected the first pass and chose to fix all six
findings in this item. The verifier's assessment found them, and each was checked
before this was written.

Acceptance criteria 1–7 were met, and the full suite passed (3368 at `5df02e41`).
The rejection is about the skill text's write paths and two contradictions with
the user's decisions. The by-hand run could not reach any of them, because every
run stopped before writing.

## What the implementation still has to do

**A. A new raw inbox entry cannot be committed.**
- `skills/tcw-work-create/SKILL.md` step 4 commits with
  `git -C "$(tcw work path)" commit -- <paths>` and never runs `git add`.
- Reproduced in a seeded eval fixture:
  - a created item commits, because `tcw work new` stages its `intake.md` and
    `state.yaml`;
  - a raw entry written into `tcw work inbox path` fails with
    `pathspec … did not match any file(s) known to git`;
  - a path relative to the repository root also fails when `-C` points at the
    store folder.
- **Fix:** stage before committing (`git add`, then a commit limited to those
  paths), using the absolute paths the CLI prints. This covers step 1's inbox
  entry, the append rule and the strict-mode fallback.
- Fix spec D1 to match.

**B. Step 0 moves only steps 2–4 to the primary checkout.**
- In a worktree, step 1's unattended inbox entry, and the strict-mode fallback
  entry, would therefore land on the work branch. That contradicts the user's
  decision that items are searched, created and amended on the primary checkout's
  board.
- **Fix:** step 0 applies to every `tcw` and `git` command in steps 1–4.
- Fix spec D1 to match.

**C. Delegated blockers contradict the user's decision.**
- The modes table says a delegated run returns whatever the brief leaves open as
  `needs decision`. The step 4 table says a delegated run with a silent brief
  determines blockers automatically. As written, `needs decision: blockers` is
  unreachable.
- **Fix:** in a delegated run with a silent brief (or a blocker described but
  unconfirmed), return `needs decision: blockers`, with step 2's `blocks` lines
  as candidates. Determine automatically only when the brief says to.
- Fix spec D1 to match.

**D. Smaller gaps in the skill text.**
- **References and origin with a silent brief** in a delegated run are not
  questions for the user. Record "none given in the brief"; `request` asks again
  later.
- **"Revised"** is reported once every artifact being revised is written: the
  spec alone when there is no plan.
- **A discarded close match** goes into the reason part of the single outcome
  line.
- **A folder inbox entry's main file** is the Markdown file that
  `tcw work inbox show` prints as the body.

**E.** Add `Bash(grep *)` to `allowed-tools`, since `find-overlap.md` tells the
agent to grep. Replace the `$(tcw work path)` substitution inside the git
command with two plain steps.

**F.** In `docs/release-notes/upcoming.md`, say that for work already underway
the skill tells the user and records nothing.

## How the second pass is checked

- Acceptance criteria 1–8 are re-run: the AC 1–3 checks, the targeted tests, and
  `tcw capabilities check`.
- A new by-hand check that **does write**, in a freshly seeded eval fixture
  outside the checkout, following the fixed step 4 text exactly:
  - (g) commit a created item;
  - (h) commit a raw inbox entry;
  - (i) append to a tracked inbox entry and commit it.

  Each must commit, with `git status --porcelain` clean afterwards.
- Step 0's reach into step 1 is checked by reading. A worktree write test would
  write to this repository's real inbox.
- Bare `pytest` on the final HEAD.
