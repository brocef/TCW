# Resume state — delete this file before completing the item

Rewritten at `07e61b57`. This is scaffolding, not a lifecycle artifact. The
version it replaced was written mid-implementation and is now wrong in every
particular.

## Where this item stands

**Implementation is finished.** All six tasks done, `outcome.md` written, suite
green at 2656 passed against a 2627 baseline, `tcw validate` on this repository
back to exiting 0.

| Task | State | Commit |
| --- | --- | --- |
| 1 — failing tests for the loader contract | done | `7aaf66ae` |
| 2 — the loader raises on a non-mapping | done | `b94ab11f` |
| 3 — classify the uncaught call sites | done | `edfe5733` |
| 4 — `validate` shape-checks what TCW owns | done | `edfe5733` |
| 5 — the contract in the abstract store | done | `edfe5733` |
| 6 — end-to-end by hand | done | no diff |
| — docs | done | `9e8b7e08` |
| — outcome + inbox note | done | `07e61b57` |

Tasks 3 to 5 share one commit because the suite forced a redesign that moved
edits across all three; the split is recorded in `outcome.md`.

## What is left

Review, then `refined-outcome.md` with an `## Autonomous decisions` section,
then `tcw work complete`. **The verify stage takes the user's acceptance
decision, so it is not something a session should run past unattended.**

`tcw validate` passing again is what unblocks `tcw work complete` at all — it is
a `pre` hook here, so while it failed no item in this repository could be
completed.

## The two things the suite found that reading the code had not

Both are in `outcome.md` in full; they are here because they are the parts most
likely to be re-litigated.

- **A top-level `yaml.YAMLError` handler was the wrong fix for task 3.** Two
  existing tests assert that a malformed node sentinel is a `ValueError` naming
  the path. The sentinel now has one reader, `load_config`, which converts.
- **`capabilities.yaml` does not belong in the owned-mapping set.** A work
  item's sidecar has two valid shapes, and forcing one made the
  Definition-of-Done gate fail closed on a sound file. The spec's justification
  for the set measured this repository rather than the format.

## Out of scope, done anyway

`.claude` added to the skipped directories in
`tests/test_skill_lifecycle_parity.py` (`c6024854`). A linked worktree nested
there turned four parameters red on files the test already means to ignore.
Filed at `docs/work/inbox/2026-09-11-a-linked-worktree-under-dot-claude-makes-the-parity-test-fail.md`.

## Run-level state

Five of six items in the sweep are complete; this one is implemented and not
yet verified. The sixth,
`2026-08-18-report-the-missing-skill-caveat-from-tcw-work-lifecycle-rather-than-the-skill`,
has not been started.

Five follow-ups sit in `docs/work/inbox/` and none is triaged. The largest is
`2026-09-11-take-over-cannot-recover-a-claim-from-the-cli.md`: the documented
remedy for an interrupted claim cannot be run from the command line at all.

Standing instruction for the run: accumulate changelog and release notes in
`upcoming.md`, never cut a version, and never push.
