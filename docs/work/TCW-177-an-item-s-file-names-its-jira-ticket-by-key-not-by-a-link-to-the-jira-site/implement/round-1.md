# Implement — round 1

Answers no rejection: this is the first round.

## What was done

1. **Tests first.** Changed `tests/work/jira/test_jira_write.py::test_a_new_item`,
   `tests/work/jira/test_jira_tickets.py::test_a_folder_left_without_item_yaml_is_finished`
   (adoption) and `tests/work/jira/test_jira_state_files.py::test_new_writes_the_version_and_the_ticket`
   to expect `ticket: <KEY>`; `test_jira_nested.py::test_a_key_named_folder_with_no_state_file_is_no_item`
   to expect "it holds the ticket's key" and to assert "ticket's link" is absent;
   added `test_the_key_form_is_clean` and two `test_each_error` rows (`ticket: TCW-2`
   in `TCW-1-x`; `ticket: 7`) to `test_jira_validate_offline.py`, whose `folder`
   fixture still writes the 4.0.0 link by default, so `test_a_clean_tree_is_clean`
   and the "is not on" and "names TCW-2" rows keep proving the old form is accepted
   and checked. Red before the code, each for the reason it names:

   ```
   AssertionError: error: docs/work/TCW-1-x/tcw-work-item.yaml: ticket 'TCW-1' is not on https://acme.atlassian.net (work.jira.site)
   AssertionError: error: docs/work/TCW-1-x/tcw-work-item.yaml: ticket 'TCW-2' is not on https://acme.atlassian.net (work.jira.site)
   AssertionError: error: docs/work/TCW-1-x/tcw-work-item.yaml: ticket 7 is not on https://acme.atlassian.net (work.jira.site)
   AssertionError: assert 'tcw-version:...rowse/TCW-1\n' == 'tcw-version:...cket: TCW-1\n'   (test_a_new_item)
   AssertionError: assert 'tcw-version:...rowse/TCW-1\n' == 'tcw-version:...cket: TCW-1\n'   (adopt)
   FAILED test_jira_nested.py::test_a_key_named_folder_with_no_state_file_is_no_item
   6 failed, 23 passed
   ```

2. **The code** (`tcw/work/jira/backend.py`): `_item_file` writes
   `ticket: {key}`; `_item_file_problems` applies spec Design rule 2 (not a
   string; no `/` and equal to the folder's key; with `/`, the 4.0.0 check with
   its messages unchanged); `UNMADE_MESSAGE` says "the ticket's key", and the
   missing-file branch uses it instead of repeating the text. Green:
   `tests/work/jira` 839 passed, 2 skipped.
3. **Full suite**, bare `.venv/bin/pytest` from the worktree root, run just now
   after every commit: `8302 passed, 115 skipped in 1177.19s`.
4. **This repository's item files**, in a commit of their own: a script (not
   committed) rewrote 117 `docs/work/**/tcw-work-item.yaml` lines to
   `ticket: <KEY>`, refusing if any key differed from its folder's key prefix
   (none did). Afterwards no item file holds `/browse/`;
   `.venv/bin/tcw validate`: `0 errors, 0 warnings, 0 unresolved`;
   `.venv/bin/tcw validate --remote`: `117 item folders checked against their
   tickets`, `0 errors, 0 warnings, 0 unresolved`.
5. **Documentation Sync**, evaluated from `tcw work docs`:
   - `docs/guide/jira.md` [Jira-Change]: the folder paragraph says the file
     holds the key, why, how a link is built, and that a 4.0.0 file stays
     valid; "Checking the workflow" says how the ticket line is checked.
   - `docs/guide/linking-and-validation.md` and `docs/guide/work.md`
     [Guide-Topic-Change]: the missing-file message; the Jira bullet's "the
     ticket's address" is now "the ticket's key".
   - `docs/capabilities/work/keep-work-items-in-jira/description.md`: the
     declared capability change.
   - `docs/release-notes/upcoming/<folder>.md` and
     `docs/changelogs/upcoming/<folder>.md`: new.
   - No change: `README.md` (its Jira table names no `ticket` line),
     `skills/*/SKILL.md` (none describes the line), `skills/configure/references`
     (no key changes), `docs/use-cases.md` (no setup's requirements change).

## What the plan or spec got wrong

- The plan listed `docs/guide/work.md` as naming only the file; its line 70
  described the line as "the ticket's address", and was changed.
- The plan's step 1 missed `test_jira_state_files.py::test_new_writes_the_version_and_the_ticket`,
  which also pins the written text; found by the step-2 run, as the plan
  allowed for.
- `test_the_key_form_is_clean` first asserted `"error" not in text`, which
  "0 errors" defeats; it now asserts `"error:"`. Its red run above was for the
  right reason ("is not on").

## Records changed

- `tcw.capabilities/work/keep-work-items-in-jira`: description updated, as
  `capabilities.yaml` declares.
