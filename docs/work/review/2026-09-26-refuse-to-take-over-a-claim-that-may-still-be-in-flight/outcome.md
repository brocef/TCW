# Outcome — Refuse to take over a claim that may still be in flight

## What shipped

| Task | Commit | What |
| ---- | ------ | ---- |
| 1–2  | `3f0e0274` | Failing tests, then the claim protocol: `_await_interrupted` (the 500 ms wait), the steal-first take-over, `_stamp_claim` (atomic stamp from a temporary file in `.claiming/`), and every lost step routed through `_lost_the_claim`. |
| docs | `63ca1754` | `docs/guide/work.md` and `skills/work/references/commands.md` describe the wait; changelog and release-note entry files. |
| review | `28018d2d` | Fixes from the adversarial code review (below). |
| docs | `ff532e52` | The changelog names the refusal the wait raises. |

## Tests

- New in `tests/test_interrupted_claim.py`: a live claimant publishing inside
  the window is refused under `take_over` and under `recover` (AC1, AC2); a
  claimant whose folder is taken at its stamp reports the winner (AC4); a
  take-over whose steal loses reports the winner (AC5); a claimant resuming
  after a take-over's stamp cannot publish; the CLI's `--take-over` refuses a
  claim published while its `pre` hooks ran; an unrelated missing folder at
  publish still rolls back; a stamp leaves nothing behind and keeps the item's
  fields (AC6). New in `tests/test_non_git_writes.py`: `init` relocates a store
  whose `.claiming/` holds only a stray stamp file.
- Every new test was mutation-checked: removing the wait, the steal, the CLI's
  memory of recovering, the rollback condition, the temporary file cleanup and
  the pristine-check exemption each turns the intended test red.
- Full suite (`pytest -q -n 8`, private virtual environment on this worktree):
  4766 passed, 3 skipped before the review fixes; re-run after them — see
  `refined-outcome.md`.
- Hands-on: the spec's reproduction script now prints the recoverer's refusal
  and `owner now: alice`; a genuinely interrupted claim in a scratch node is
  recovered by `tcw work start <slug> --take-over --owner me` in 1.6 s and
  leaves `.claiming/` empty.

## What the plan or spec got wrong

- **The spec's sibling sweep cited the wrong evidence.** It said
  `tcw work tracker claim --take-over` reaches `start` through
  `tcw/tracker/ownership.py:92`. That line is `assert_ownership`; `tracker claim`
  never calls `start`. The conclusion (no sibling defect outside `start`) holds.
- **The spec missed the CLI's own gap.** `tcw work start --take-over` detects
  the interrupted claim, runs the `pre` hooks and strict tracker checks, and only
  then calls the store with `take_over=True`; a claim published in between was
  taken over as an active item, bypassing the new wait entirely. Found by the
  code review and fixed: the CLI remembers it began as a recovery and calls
  `start(recover=True)`.
- **The planned refusal was the wrong exception.** The spec had the wait raise
  `AlreadyClaimed`, whose message advises re-running `--take-over` — the
  opposite of what `commands.md` now says. It raises `IllegalTransition` naming
  the claimant instead.
- **Plan task 3 named `pytest -n auto`**, and the shared environment has no
  `pytest-xdist`. The private environment installs it; `-n 8` runs the suite in
  about seven minutes.
- **AC6 cannot detect a return to the in-place write.** The plan asked to say so
  if it could not: it cannot. The in-place truncate race needs a writer holding
  an open file across another process's rename, which no test here can force;
  the atomic replace is guarded by reading, not by a test. AC6 does catch a
  leaked temporary file (via the lost-race tests) and lost fields.
- **The first window tests were timing-fragile** (a fixed 100 ms, then 300 ms,
  delay raced the git calls that precede the wait). They now publish 50 ms after
  a signal from inside the wait.

## Autonomous decisions

- **Design of the fix (spec).** Codex: steal-first plus atomic stamp plus the
  wait, or a per-slug lock. Opus: steal-first plus atomic stamp; the wait adds no
  correctness. Chose steal-first, atomic stamp **and** the wait: the request asks
  that a claim possibly in flight not be taken, and only the wait stops a live
  claimant losing in the normal case. The lock was rejected as a new
  operating-system dependency the rename order makes unnecessary.
- **Review findings (adversarial-code-reviewer, NOT DONE).** Accepted and fixed:
  the CLI gap, the missing cleanliness assertions, the triplicated wait loop,
  the contradictory refusal message, the unrelated-`FileNotFoundError` rollback,
  the timing-fragile tests, and the `init` pristine check (the reviewer placed it
  in a separate change; it was three lines, so it was folded in). Accepted as a
  note only: a Ctrl-C landing right after a successful publishing rename is
  reported as a lost race — rare and cosmetic.
