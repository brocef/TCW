# Plan — An item's file names its Jira ticket by key, not by a link to the Jira site

Spec: [`../spec/spec.md`](../spec/spec.md). The CLI under change is `tcw/`, so
every check of the new behavior runs this checkout's `.venv/bin/tcw` and
`.venv/bin/pytest`; the lifecycle is driven with the released `tcw` 4.0.0.

## Steps

1. **Tests first (red).** Change or add, in this order:
   - `tests/work/jira/test_jira_validate_offline.py`: the `folder` fixture
     keeps writing the 4.0.0 link by default (so `test_a_clean_tree_is_clean`
     and the link rows of `test_each_error` keep proving AC 4 and 5); add
     `test_the_key_form_is_clean` (`ticket: TCW-1` in `TCW-1-x`, exit 0, AC 2),
     and rows to `test_each_error` for `ticket: TCW-2` in `TCW-1-x` ("names
     TCW-2, but the folder's key is TCW-1", AC 3) and `ticket: 7` ("is not the
     folder's key, TCW-1", AC 6).
   - `tests/work/jira/test_jira_write.py::test_a_new_item`: expect
     `ticket: TCW-1\n` (AC 1).
   - `tests/work/jira/test_jira_tickets.py::test_a_folder_left_without_item_yaml_is_finished`:
     expect `ticket: <key>\n` (AC 1, adoption).
   - `tests/work/jira/test_jira_nested.py::test_a_key_named_folder_with_no_state_file_is_no_item`:
     expect "it holds the ticket's key" (AC 7).
   - Any other test that asserts the text the writer writes (found by running
     the suite after step 2; `grep -rn '/browse/' tests/` lists the
     candidates, most of which write a 4.0.0 file as a fixture and stay).
   Done when: these tests fail against the current code, each for the
   reason it names. Record the failing lines for the round.
2. **The code (green).** `tcw/work/jira/backend.py`:
   - `_item_file` (`:942`) writes `ticket: {key}`.
   - `_item_file_problems` (`:198-232`) applies Design rule 2: not a string;
     no `/` (key, equal to the folder's); with `/` (the 4.0.0 check,
     unchanged messages). Docstring updated.
   - `UNMADE_MESSAGE` (`:143`) and the missing-file message (`:207`) say "the
     ticket's key"; `:207` uses `UNMADE_MESSAGE` so the two cannot drift.
   Done when: the step-1 tests pass and `.venv/bin/pytest tests/work/jira`
   passes.
3. **The full suite.** `.venv/bin/pytest` from the worktree root (as CI runs
   it). Fix any test that pinned the written form. Done when: it passes.
   Commit steps 1-3 together with step 5's documents.
4. **This repository's item files, in a commit of their own.** A script in
   the session's scratch folder (not committed) rewrites each
   `docs/work/**/tcw-work-item.yaml` line `ticket: <anything>/browse/<KEY>` to
   `ticket: <KEY>`, refusing (and changing nothing) if any `<KEY>` differs
   from its folder's key prefix (`^[A-Z][A-Z0-9]*-\d+`). Done when:
   `grep -rl '/browse/' docs/work --include=tcw-work-item.yaml` finds nothing;
   `.venv/bin/tcw validate` and `.venv/bin/tcw validate --remote` (Jira
   credentials loaded) report 0 errors. Commit message:
   "TCW-177: this repository's item files name their tickets by key".
5. **Documentation Sync** (one block, before the step-3 commit):
   - `docs/guide/jira.md` [Jira-Change] fires (what `tcw work new` and
     `tickets adopt` write): the folder paragraph says the file holds the
     ticket's key, and that a file written by TCW 4.0.0 with the ticket's
     link stays valid; the "Checking the workflow" paragraph says the key is
     checked against the folder's.
   - `docs/guide/linking-and-validation.md` [Guide-Topic-Change] fires (a
     message changes): the row for a work item folder with no state file
     gives "is missing; it holds the ticket's key".
   - `docs/capabilities/work/keep-work-items-in-jira/description.md` (the
     capability this item declares as changed): "the ticket's key" for "the
     link to the ticket".
   - `docs/release-notes/upcoming/TCW-177-an-item-s-file-names-its-jira-ticket-by-key-not-by-a-link-to-the-jira-site.md`
     [Public-API] and
     `docs/changelogs/upcoming/TCW-177-an-item-s-file-names-its-jira-ticket-by-key-not-by-a-link-to-the-jira-site.md`
     [Any-Code-Change]: new files.
   - Evaluated, no change: `README.md` (its Jira table names no `ticket`
     line; grep for `/browse/` and `tcw-work-item` lines 260, 500-511);
     `skills/*/SKILL.md` (no skill describes the line; `grep -rn
     'tcw-work-item\|/browse/' skills` is empty); `skills/configure/references`
     (no configuration key changes); `docs/use-cases.md` (no setup's
     requirements change; UC-7's requirement that nothing published names
     private details is met better, not changed); `docs/guide/work.md` and
     `docs/guide/web-viewer.md` (they name the file, not its `ticket` line).
   Done when: `grep -rn 'link to the ticket\|ticket.s link\|ticket.s address'
   docs/guide docs/capabilities` finds nothing that describes the file, and
   the new files use only example sites.
6. **The round.** `implement/round-1.md` with what was done, the red and green
   lines, the suite's summary and the validate results.

Before each commit: `git diff --cached | grep -i -f
~/.tcw-4.0-release/private-names.txt` finds nothing new outside `ticket:`
lines being removed.

## Verification

- `tcw validate --remote` against the real Jira project (step 4) is the one
  check the tests cannot make: it proves this repository's rewritten files
  agree with their tickets.
- A Jira-mode `tcw work new` against the real site is not run (it would
  create a real ticket); the fake Jira site in the tests covers the writer.
