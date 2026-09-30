# Refined outcome

**Accepted.**
- `complete --resolution done` from review refuses without
  `refined-outcome.md`, naming where it belongs and any stray folder.
- `tcw validate` reports stray folders and slugs held twice.
- The stage text says where to write.
- Printed folders work from where the command ran.

## Evidence

- **Full suite, bare `pytest` at `68e51574`:** 5070 passed, 3 skipped, 13
  failed.
  - 11 were the lifecycle baselines. `tcw work lifecycle` now lists
    "refined-outcome.md from review" among `complete`'s gates, and a diff of
    old against new output showed that line and nothing else. The baselines
    were regenerated with their own `capture.py`.
  - 2 were hint tests completing from review without the file, exposed once the
    refusal moved ahead of the checklist.
  - Both files pass after `9f211ad3` (28 tests). The combined run on main after
    the last merge is the final confirmation.
- **`tcw:verifier`:** criteria 1-8 met, each with tests plus reproductions
  through the real CLI, including a worktree item submitted from inside its
  worktree and `start kid/<slug>` from a parent.
- **Hands-on, the issue's own case:**
  - submit, then write `active/<slug>/refined-outcome.md`;
  - `complete` refused and named `docs/work/active/<slug> (refined-outcome.md)`;
  - `validate` reported the stray folder;
  - after moving the file into `review/<slug>/`, `complete` went through.

## Found at verify, fixed

- **Capability records.** `cli/validate-a-node` and
  `work/run-a-lifecycle-stage` were updated, and the item's
  `capabilities.yaml` written. The spec had named a capability that does not
  exist.
- **Criterion 6's web-app premise (a 500 error) was wrong.** Recorded in the
  outcome. The per-item validation the web app does run now returns the
  duplicate.

## Deferred

- **Closing GitHub issue #58 waits for publication.** The order is: complete
  the batch → cut the version → push → answer and close, with the reply text
  approved first.
- **Inbox follow-up:** keep an item's folder in one place, with its status
  only in `state.yaml`.
