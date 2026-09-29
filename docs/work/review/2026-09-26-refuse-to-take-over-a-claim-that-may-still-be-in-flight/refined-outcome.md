# Refined outcome — Refuse to take over a claim that may still be in flight

## Decision

**Accepted**, 2026-09-29, during an unattended run: the decision is the
implementing agent's, taken in place of the user's at the user's request, on the
evidence below.

## Evidence

- `tcw:verifier` assessment: criteria 1–5 met, 6 met for leftovers and fields
  (the in-place-truncation half is backed by reading `_stamp_claim`, not by a
  test — recorded in `outcome.md`), 7 unverified by it for want of a recorded run.
- Full suite after the review fixes, run 2026-09-29 from the item worktree with
  its private virtual environment: **4769 passed, 3 skipped** (`pytest -q -n 8`,
  exit 0). The verifier re-ran `tests/test_interrupted_claim.py` and
  `tests/test_non_git_writes.py` (84 passed) and `tests/test_work_start.py` plus
  `tests/test_serve*.py` (181 passed).
- Hands-on: the spec's reproduction now ends `owner now: alice` with the
  recoverer refused; a genuinely interrupted claim in a scratch node is still
  recovered from the real CLI.

## Accepted deviations from the spec

- Criterion 1 expected `AlreadyClaimed`; the wait raises `IllegalTransition`
  naming the claimant. `AlreadyClaimed`'s message advises re-running
  `--take-over`, the opposite of the right advice here. Both the CLI (`_ERRORS`)
  and the web app map it as a refusal. Accepted.
- The CLI's `--take-over` change (it recovers with `recover=True` when it found
  an interrupted claim) goes beyond the spec's design; it closes the gap the
  review found and is tested.

## Closeout

- Capability reconciliation: none declared; nothing to reconcile.
- Documentation: `docs/guide/work.md`, `skills/work/references/commands.md`,
  changelog and release-note entry files.
- Not from a GitHub issue.
- Merge route: `tcw work complete` from the `bug-run` integration worktree,
  merging into `bug-run`; `main` is left for the user to merge.
- Follow-ups: none filed; the review's one deferred note (a stray stamp file
  blocking `init`) was folded in.
