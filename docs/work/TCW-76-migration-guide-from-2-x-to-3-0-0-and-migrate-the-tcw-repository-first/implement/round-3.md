# Implement round 3 (TCW-76, Task B22): review round 2's findings

Review round 2 (`review/round-2.md`) rejected round 2 with four defects and
four notes. By the owner's decision of 2026-10-20 ("I fix + test, no
review"), this round fixes all eight, gives each defect a test that fails
without its fix, and mutation-checks each such test; no further review
round follows. Each finding was checked against the code or the files
before anything changed. Only `docs/` and `tests/` changed (the fixes are in
`5d86a290`); nothing under `tcw/`, `skills/`, `agents/` or `web/`
(`git diff --stat d5fd6dc0 HEAD -- tcw skills agents web` prints nothing).

The lifecycle was driven with the 3.0 CLI (the private environment
`tcw76/venv`, installed from the epic worktree), since this round changes no
code under `tcw/`.

`guide` is `docs/migration-guide-2.8-to-3.0.0.md`, `log` is
`docs/tcw-3.0-migration-log.md`.

## Defects

- **D1. Accepted.** Step 2's first bullet makes each missing status, and the
  spelling comparison was only in step 3, which runs after it; the
  `work.tracker.statuses` row ended "(step 3)". Step 1's stages entry now
  says to compare each status name with Jira's exactly first (reading the
  project's statuses, [Talking to Jira]), so a 2.x `in progress` for Jira's
  `In Progress` is a spelling the plan corrects, not a status to add. Step
  2's first bullet says to compare the plan's names with that read before
  deciding one is missing, and to leave Jira as it is when a name differs
  only in spelling. The row now says each name is compared in the plan
  (step 1) and again before Jira is changed (step 2). Step 3 keeps a
  one-sentence reminder.
  Test: `test_status_names_are_compared_with_jiras_before_step_2_changes_jira`.
- **D2. Accepted.** The test ran its own `grep -rnE -f old.re docs`. It now
  takes step 9's check's own search from the guide (the backquoted command
  holding `-f <the file of patterns>`), puts the sample's files in place of
  the plan's folders and documents, and runs it with `sh`.
  Test: `test_step_9s_patterns_find_a_whole_old_name_and_not_a_longer_one`.
- **D3. Accepted.** Nothing below `docs/lifecycle/harness.md` line 19 says a
  subagent is never required; `skills/work/SKILL.md`'s section
  `## Rules no project text changes` does ("A subagent is permitted, never
  required: a session that cannot dispatch runs the same stage itself"). The
  line now states the rule in place and links that section
  (`../../skills/work/SKILL.md#rules-no-project-text-changes`). A pointer test
  in this style exists: `test_every_link_in_an_owned_document_resolves`
  checks that each link's file exists, but reads anchors only in owned
  documents, and the work skill is not one. So a new test checks the
  sentence, that the anchor is one of the skill's headings, and that the
  section states the rule.
  Test: `test_harness_points_at_where_a_subagent_is_never_required`
  (`tests/test_docs_describe_3_0.py`).
- **D4. Accepted.** macOS's `/bin/realpath` fails on a link that points
  nowhere (tried: exit 1, "No such file or directory"); GNU's, run without
  options, resolves it, so the old line added the missing target to the
  places. Step 12's loop now skips such a link with `[ -e "$l" ] || continue`
  before `realpath`. The test's links gain `.claude/skills/gone`, pointing at
  a missing folder outside every listed place. **That case can fail only
  under a GNU-like `realpath`**, so the test runs twice whichever machine
  runs it: once with the machine's own `realpath`, and once with a stand-in
  first on `PATH` that behaves as GNU's does without options (Python's
  `os.path.realpath`, which resolves a missing target instead of failing).
  CI's Linux `realpath` is GNU's, so there the first run catches it as well.
  Test: `test_step_12s_places_follow_links_and_keep_the_project_relative`,
  `[this machine's]` and `[GNU's]`.

## Notes

- **N1. Accepted.** Tried on a sample: two comment files beginning with the
  same first line, the first without a final newline, counted `0` with the
  old loop and `2` with the new command. Step 5's counter is now
  `awk 'FNR==1' docs/work/<folder>/comments/*.md 2>/dev/null | grep -cxF '<first line>'`,
  with a sentence on why; with no comment files it prints `0`.
  Tests: `test_step_5_skips_a_filesystem_comment_already_written` (the new
  command), and `test_step_5s_counter_reads_a_comment_without_a_final_newline`,
  which runs the guide's command on that sample and on an empty folder.
- **N2. Accepted.** `tcw/work/model.py` (314-316) gives `completed` and
  `discarded` no prompt, and `tcw-config.yaml` binds the pull prompt to
  `request`, `spec`, `plan`, `implement`, `review`, `qa` and `postmortem`.
  The changelog entry now names those stages, and says `inbox` is bound none
  and the two end stages take no prompt. `AGENTS.md`'s "every stage's
  instructions from `request` on" is left as it is: the two end stages have
  no instructions, so it is true as written.
- **N3. Accepted.** The B-F correction had rewritten a sentence inside
  `## Approved plan`. The sentence is back exactly as at `61af5c5a`
  (`git show 61af5c5a:docs/tcw-3.0-migration-log.md`, 551-555), followed by
  a note dated 2026-10-20 that says it is not part of the approved plan and
  gives the correction. Compared afterwards, the section differs from
  `61af5c5a`'s only by that added note.
- **N4. Accepted, and widened by one name.** Pi's
  `dist/core/resource-loader.js` (`loadContextFileFromDir`) looks for
  `AGENTS.override.md`, `AGENTS.md`, `AGENTS.MD`, `CLAUDE.md` and
  `CLAUDE.MD`, in the agent folder and in the working folder and its
  parents, and its `docs/configuration.md` lists the same five for the agent
  folder (both under `@earendil-works/pi-coding-agent` in this machine's Node
  installation; `~/.pi/agent/npm` holds only packages, not Pi's own
  documentation). So step 12 names `AGENTS.MD` and `CLAUDE.MD` for the
  project and for `~/.pi/agent/`, and also the project's
  `AGENTS.override.md`, which Pi reads in the project as well as in the
  agent folder. On a disk that ignores capitals, `AGENTS.MD` is `AGENTS.md`
  again, and listing both would print each line twice and fail step 12's
  check; so the snippet adds a capitals name only when it is not the same
  file as its lower-case name (`[ "$p" -ef "${p%.MD}.md" ]`).
  Tests: the three names added to `PLACES` (`test_step_12_names_each_place`),
  and `test_step_12s_places_add_pis_capital_names_only_when_they_are_other_files`,
  which writes `AGENTS.MD` beside `AGENTS.md` when the disk tells capitals
  apart and expects it listed, and otherwise expects it left out.

## Tests

Runs, with bare `pytest -p no:cacheprovider` from the epic worktree and the
private environment first on `PATH`:

- the guide's and the lifecycle tests, the cross-scan files
  (`test_documented_cli_surface`, `test_docs_describe_3_0`,
  `test_shipped_text`, `test_upcoming_entries`), every test file that names
  a changed file (`grep -rlE` over `tests/` for the guide, `harness.md`,
  `docs/lifecycle`, the log and `upcoming`), and the standing guards
  (`test_cli_contract`, `test_cli_help_standard`, `test_static_guards`,
  `test_cli_handler`, `test_tree_store_raises`, `test_no_node`,
  `test_ledger_3_0`, `tests/work/test_model_guards`): 27 files in sorted
  order, **1615 passed, 15 skipped**;
- `pytest --collect-only -q`: 5283 tests, no errors (5275 at round 2, and
  the 8 added here);
- `tcw validate`: `0 errors, 0 warnings, 0 unresolved`, exit 0.

The full suite was not run (the epic's rule: targeted tests per child, the
full suite near the epic's end).

## Mutations

Run in a `git archive` copy of the fixed tree (made a git repository, since
the document scans list files with `git ls-files`), with bare `pytest`; each
mutation applied alone, its tests run, and the file's bytes restored. The
named tests were green before the first mutation and after the last. Each
went red, and the D2 and D4 failures were read: D2's search found nothing
(`[] == ['1', '2', '5']`), and D4's listed `…/gone` among the places.

| Mutation | Red |
| --- | --- |
| M1 D1: step 1's comparison removed | `test_status_names_are_compared_with_jiras_before_step_2_changes_jira` |
| M2 D1: step 2's comparison removed | the same |
| M3 D1: the statuses row points at step 3 again | the same |
| M4 D2: step 9's search made `grep -rnF` | `test_step_9s_patterns_find_a_whole_old_name_and_not_a_longer_one` |
| M5 D3: `harness.md` back to "(the rules below)" | `test_harness_points_at_where_a_subagent_is_never_required` |
| M6 D4: the `[ -e "$l" ]` guard removed | `test_step_12s_places_follow_links_and_keep_the_project_relative[GNU's]`; `[this machine's]` stays green on macOS, as expected |
| M7 N1: step 5's counter back to `head -n 1` | `test_step_5_skips_a_filesystem_comment_already_written`, `test_step_5s_counter_reads_a_comment_without_a_final_newline` (red because it no longer finds the `awk` command; the old loop's miscount was shown on the sample above) |
| M8 N4: the capitals loop removed | `test_step_12_names_each_place[AGENTS.MD]`, `[CLAUDE.MD]` |
| M9 N4: the same-file guard removed | `test_step_12s_places_add_pis_capital_names_only_when_they_are_other_files` (on this machine's disk, which ignores capitals; on a disk that tells capitals apart, as CI's Linux one usually does, it stays green, since the two names are different files there and the guard does not apply) |
