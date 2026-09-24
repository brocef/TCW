# Outcome: leave an accepted or imported ticket in the backlog status, matching its item

## What shipped

| Task | Commit | What |
|---|---|---|
| 1 | `adb62e7d` | `ClaimOutcome.claimed_from`: the status `claim` found the ticket in, after any pre-backlog step, set only on a claim. Tests in `test_tracker_claim.py` and `test_tracker_pre_backlog.py`. |
| 2 | `6336b4c9` | `intake.put_back` and the call in `_tracker_import`. After the binding is written, a ticket the claim moved goes back to `claimed_from` through the one transition the ticket offers there (`assess_move`). A failure is a `warning:` and exit 0. Skipped under strict mode, and when the ticket is still in `claimed_from`. New `tests/test_tracker_import_returns.py` covers AC1–AC8. |
| 3 | `54fede2b` | Documentation: Jira guide ("Then the ticket goes back where the claim found it"), README (table row and Example 1), `skills/work/references/commands.md`, the `work/manage-external-tracker-intake` capability description (new sentence, fifth accepted limit), the item's `capabilities.yaml` (`changed:`), and changelog and release notes `upcoming.md`. |

## Tests

- Full suite, run as CI runs it (bare `pytest`), on the Task 2 code: 4471 passed,
  3 skipped, **1 failed** in 26 min. The failure was
  `test_import_of_a_triage_ticket_already_yours`, which asserted no `warning:` at
  all on a workflow with no way back from In Progress (see below). Its assertion
  was narrowed to the triage warning it is about.
- After that fix and a wording fix to the warning: every tracker and inbox test
  file, `pytest tests/test_tracker_*.py tests/test_inbox*.py`: **1118 passed**.
  The full suite was not re-run: the changes after the full run touch only the
  warning's text and that one test, and every test that imports a ticket is in
  those files.
- `tcw validate`: OK. `tcw capabilities check`: OK.
- Mutation checks:
  - Removing the strict-mode condition fails
    `test_strict_mode_leaves_the_ticket_where_the_claim_put_it`.
  - Removing the "still where the claim found it" condition fails
    `test_a_ticket_already_yours_and_under_way_is_left_alone`, through its
    assertion that the ticket's transitions are read only once.

## What the plan or spec got wrong

- **The plan's `outcome.transitioned` condition was redundant.** Removing it
  changed no test result. A claim that sends no transition (row `1e`) leaves the
  ticket in `claimed_from`, so the status comparison already skips it. It was
  dropped, and the status comparison is now the one guard. The test was
  tightened so that removing the guard fails (see mutation checks). Without the
  guard, an import of a ticket already under way would make three extra tracker
  reads, and a failure in any of them would print a misleading warning.
- **AC6's test mechanism in the plan (`before` arming `fail`) does not work.** The
  hook armed inside `before` matches the same request. The test uses the existing
  `post_fails` helper from `test_tracker_pre_backlog.py` instead.
- **The plan predicted that old tests might see the new warning.** One did
  (above). No others did.
- The warning at first read "…'Duplicate'.. Move it back": the reasons from
  `assess_move` end with a full stop. It is now stripped, and a test asserts it.

## Not verifiable by the suite

Behaviour against the real TCW Jira workflow. The next real `inbox accept` of a
Triage ticket on this project, after the patch is cut, should end with the ticket
in To Do. The `Stop` transition added on 2026-09-24 makes that possible.

## Follow-ups

- `2026-09-24-make-the-test-suite-run-in-minutes-not-half-an-hour`, filed at the
  user's request during this item.
