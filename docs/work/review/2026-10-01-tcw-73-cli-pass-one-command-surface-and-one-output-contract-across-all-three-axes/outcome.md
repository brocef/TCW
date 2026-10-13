# Outcome — TCW-73: one command surface and one output contract

Implemented on `work/2026-10-01-tcw-73-cli-pass-one-command-surface-and-one-output-contract-across-all-three-axes`,
made from `epic/tcw-3.0` at `89ff245d`, one commit per plan task (two for
Task 14), `a05fedc5` to `20f0b9f4`. The spec's implement-finding notes, this file and `capabilities.yaml`
are on main.

Tests were run per task against the changed areas, never as a full suite, in a
private virtual environment pointed at the worktree. `pytest --collect-only -q`
on the branch collects every test with no error.

## What was built

| Task | Commit | What |
| --- | --- | --- |
| 1 | `a05fedc5` | The top-level handler (`tcw <command words>: <error>`, the error's exit code, a created name printed on stdout after a late failure, a quiet broken pipe) and `tcw/output.py`. Options can no longer be abbreviated. |
| 2 | `7f703f12` | The `tcw work` surface: `show` with the request and comments, one-object `--json`, one tag per `--tag`, `procedure`, `lifecycle` without a slug, `tags add|rm` naming the config. |
| 3 | `d78297ed` | `tcw projects list`; `tcw work nodes` removed. |
| 4 | `f3e6965f` | The tree stores raise `NotFound`, `UsageError`, `Refused` or `BackendError`; a static test guards it. |
| 5 | `b71c1e4e` | `Finding(severity, where, message)` from every `check()` and `validate()`; notes about the run go to stderr. |
| 6 | `fdcd3153` | Taxonomy and capabilities write files only and record each path; nothing is staged; `tcw init` works outside git. |
| 7 | `d2996660` | `tcw taxonomy` on the contract: paths on stdout, stdin-only description, no `init`, `check`, shorthand or short flags. |
| 8 | `fe13ebb3` | `tcw capabilities` on the contract: `--local`, `extends add|rm`, strict `--field`, `Planning doc` and `Tracker` retired. |
| 9 | `af44f3e6` | `tcw validate`: the current project only, graded findings on stdout, the count on stderr; a broken other project is a warning; an invalid latest verdict round is a warning. |
| 10 | `500b6e7d` | Validating one work item (`ValidationTarget(axis="work")`), for `tcw serve`. |
| 11 | `d34befea` | `tcw capabilities drift` prints `<kind>: <path>: <message>` and reads completed work through the backend. |
| 12 | `cbae2ad1` | `tcw init` and `tcw provision` say everything on stderr; `provision --refresh` removed. |
| 13 | `72191347` | `tcw/cli_help.py` and the `--help` standard on all 42 leaf commands; the exit-code table on `tcw --help`. |
| 14 | `363602ea`, `3bffb71d` | Static guards: no git word in messages outside the exempt functions, nothing but `tcw/stdin.py` reads stdin, names in `open.py` in single quotes. Four messages reworded. |
| 15 | `ea5e2b8f` | `tests/test_cli_contract.py`, and the deviations it found (below). |
| 16 | `c49f7c51` | The shell scenarios: `06` and `13` rewritten, the other twelve deleted, the README says why. |
| 17 | `8c29e698` | The `projects:` key; `connected-projects` is an error naming the migration guide. |
| 18 | `ca305c08` | "project" in place of "node" under `tcw/` (outside `tcw/serve/`), "entry" for the tree sense; `tests/test_no_node.py`. |
| 19 | `1d60a231` | The ledger and taxonomy records; their declaration, kept on main. |
| 20 | `20f0b9f4` | Release-notes and changelog entries. |

## Acceptance criteria

| AC | Evidence |
| --- | --- |
| 1 Surface | `test_cli_help_standard.py::test_the_surface_is_exactly_the_3_0_column`, `::test_no_removed_command_parses` |
| 2 Removed commands suggest | `tests/work/test_cli_surface.py` (`start` suggests `advance`), `tests/test_command_suggestions.py` |
| 3 Spellings | `test_cli_surface.py`, `test_taxonomy_cli_contract.py`, `test_capabilities_cli_contract.py` (removed spellings exit 2) |
| 4 Help | `test_cli_help_standard.py` (help, description, `Prints:`/`Writes:`, examples that parse, help on every argument, long options with one spelling, exit codes in `tcw --help`) |
| 5 Git words | `test_static_guards.py` |
| 6 No "node" | `test_no_node.py` |
| 7 `projects:` key | `test_projects_list.py` (old key fails `validate` naming the guide; the graph under `projects:` validates; list order), `test_doc_allowance.py` |
| 8 stdout per command | `test_cli_contract.py` (subprocess, fixture made by `tcw init --id fx`) |
| 9 Every written file named | `test_cli_contract.py::written` compares the fixture before and after each writing command against stderr; `test_the_tree_commands` counts two `removed` lines |
| 10 Exit codes | `test_cli_contract.py`, including every `ROWS` entry outside a project |
| 11 Slug input, Jira output | `test_cli_contract.py` (`test_a_key_names_an_item`, `test_a_refused_create_prints_the_key_it_left`, `test_tickets_list_prints_keys_only`) |
| 12 Cross-project | `test_cli_contract.py` (`graph` fixture) |
| 13 Nothing prompts | `test_static_guards.py::test_nothing_but_the_stdin_module_reads_standard_input` |
| 14 Folding | `test_validate_command.py` |
| 15 stdout and stderr split | `test_validate_command.py`, `tests/work/jira/test_jira_validate_remote.py` |
| 16 Drift | `tests/work/test_drift_work.py`, `tests/work/jira/test_jira_drift.py`, `tests/work/test_gates.py` |
| 17 No git state changes | `test_tree_store_files_only.py`, `tests/work/test_git_write_scan.py` |
| 18 Retired fields | `test_capabilities_cli_contract.py`, `test_validate_command.py::test_a_retired_capability_field_is_an_error` |
| 19 `list --tag` | `test_cli_surface.py`, `test_cli_contract.py::test_list_by_tag` |
| 20 Contract coverage | `test_cli_contract.py::test_a_command_without_a_row_is_caught` |
| 21 Ledger and taxonomy | `test_ledger_3_0.py` |
| 22 Documented surface, full suite | `test_documented_cli_surface.py` and `test_doc_allowance.py` pass. The full suite was not run, by the epic's instruction; see "For later children". |
| 23 Release notes | `test_upcoming_entries.py` |
| 24 One work item | `test_validate_target.py`; the Jira half in `tests/work/jira/test_jira_validate_offline.py::test_one_item_without_its_item_contacts_nothing` |
| 25 No bare errors | `test_tree_store_raises.py` |
| 26 Names after a late failure | `test_cli_contract.py` (`test_a_late_backend_error_prints_the_slug`, `test_a_rename_that_fails_after_moving_prints_the_new_slug`, `test_an_early_failure_prints_nothing`) |
| 27 Finding type | `test_findings_type.py` |
| 28 People in Jira mode | `test_cli_contract.py::test_people_by_name_in_text_and_by_id_in_json`, `test_cli_surface.py` |

## Verification by hand

In a throwaway folder that is not a git repository, with the branch's code:
`tcw init --id walk` printed nothing and named its seven paths on stderr;
`printf 'Need X\n' | tcw work new "A b"` printed `walk/2026-10-13-a-b`;
`tcw work advance` printed `spec`; `tcw work comment` printed nothing and named
the comment file; `tcw work show` printed the record, `request:` with `Need X`,
and `comments:`; `tcw taxonomy add Widget` printed `widget`;
`tcw capabilities add ns/do-a-thing` printed its path; `tcw validate` printed
nothing on stdout and `0 errors, 0 warnings, 0 unresolved` on stderr, exit 0;
`tcw projects list` printed `walk`. `tcw --help` ends with the stream rule and
the exit-code table, and `tcw taxonomy add --help` reads plainly with its
`Prints:`/`Writes:` lines and three examples.

## Mutation checks

Each guard below was broken on purpose; the named tests went red, and the
code was restored.

- Task 1–6: the tree-store raise guard (a `raise ValueError` restored), the
  finding type, and the files-only guard (staging restored) each failed their
  tests.
- Task 8: removing the repeated-key check in `_fields` fails 2 tests;
  removing the retired-field check fails 1.
- Task 9: removing the invalid-round check fails 1; mapping `BROKEN` back to
  `UNRESOLVED` fails 1.
- Task 10: removing the folder filter in `round_findings` fails 1.
- Task 11: printing the unreviewed lines after the completed-work half fails
  the Jira exit-5 test.
- Task 13: an option without help fails
  `test_every_argument_and_option_has_help`.
- Task 14: `"run git commit first"` in a `tcw/taxonomy/` function is reported
  (`test_the_guard_sees_a_git_word_in_the_taxonomy_commands`); the stdin and
  quoting guards each have a test that feeds them an offending line.
- Task 15: dropping the `wrote` line for a comment fails
  `test_the_work_commands`; not printing a failed error's name fails the three
  late-failure tests.
- Task 17: removing the `connected-projects` check fails
  `test_the_2x_key_is_an_error_naming_the_guide` and its allowance guard.
- Task 18: a comment saying "the node's tcw-config.yaml" in
  `tcw/taxonomy/cli.py` fails `test_no_node_under_tcw`.

## 2.x tests deleted or rewritten

Deleted, because the behavior they pinned is removed (each replaced, where
the 3.0 behavior exists, by the named test):

- `test_cli_help_coverage.py` (whole file) — absorbed by `test_cli_help_standard.py`.
- `test_capabilities.py`: `test_cli_capabilities_init_mirrors_top_level`;
  `test_cli_check_with_taxonomy` → `test_check_with_taxonomy`;
  `test_cli_drift_does_not_affect_check` → `test_drift_does_not_affect_check`.
- `test_capabilities_rm.py`: `test_remove_deletes_local_capability_and_stages_it` (no staging).
- `test_legacy_store_config.py`: `test_validate_names_the_descendant_that_holds_the_leftover`
  → `test_validate_in_the_project_that_holds_the_leftover_names_it`.
- `test_literal_store_names.py`: `test_an_inherited_literal_pathspecs_setting_still_writes` (no staging).
- `test_multiproject.py`: the three `tcw work nodes` tests, rewritten against
  `tcw projects list` (`test_projects_list.py`).
- `test_routing_nodes.py`: `test_nodes_still_prints_the_direct_topology`.
- `test_serve_write.py`: `test_every_write_route_refuses_outside_a_repository` (writes need no repository).
- `test_smoke.py`: `test_capabilities_check_outside_a_node_reports_helpfully`
  → `test_capabilities_list_outside_a_node_reports_helpfully`;
  `test_init_refuses_outside_git` → `test_init_without_an_id_is_a_usage_error`.
- `test_stdin_cli.py`: `test_a_positional_description_short_circuits_past_stdin`.
- `test_store_editor.py`: the three staging-rollback tests.
- `test_store_provisioning.py`: `test_extends_add_stages_in_the_nodes_repository_not_the_stores`;
  the three `--refresh` tests (one became `test_an_available_store_is_never_fetched_into`,
  one `test_provision_refresh_is_a_usage_error`);
  `test_provision_outside_a_node_says_so` → `test_provision_outside_a_project_says_so`.
- `test_taxonomy.py`: `test_cli_bare_path_is_show` → `test_cli_bare_path_is_not_show`;
  `test_cli_taxonomy_init_mirrors_top_level`; `test_cli_list_unknown_kind_uses_unknown_marker`
  (rewritten through `--json`); `test_extends_add_names_the_key_not_a_store_path`
  → `test_extends_add_names_the_config_file_not_a_store_path`.
- `test_taxonomy_rm_gaps.py`: the five tests of git-tracking refusals (removal now decides from the disk).
- `test_upstream_projects.py`: the three `tcw work nodes` upstream tests, rewritten against `projects list`.
- `test_validate.py`: `test_path_narrows_scan_and_runs_that_check`, and the five
  recursion tests (`test_cli_recurses_through_registered_descendants` became
  `test_cli_checks_only_the_current_project`).
- `test_validate_moved_stores.py`: the three path-mode tests.
- `test_validate_target.py`: `test_rejects_path_and_target_together`,
  `test_the_work_axis_is_not_a_target` (the work axis is a target now).
- `tests/work/test_cli_items.py`: `test_list_json_is_an_array_of_records` (one object now).
- `tests/work/test_drift_work.py`: `test_drift_through_the_command` (rewritten in the file).

Rewritten to read the new streams or wording, keeping what they test: the
validate, provisioning, override, upstream, legacy-config, store-provisioning,
environment-hardness, config-writer and Jira remote-validate tests named in
each task's commit, and every test that wrote `connected-projects` (now
`projects`, 32 files) or imported a renamed name (Task 18).

## Where the work differs from the plan

1. **No shorthand allowance list (Task 7).** The documented-surface test already
   treats `<path>` as an argument, so the list would have been empty.
2. **`REMOVED_FORMS` added to the documentation allowance (Task 8)** for
   `tcw capabilities extends <id>`, a removed spelling of a command that
   survives; its guard asserts each form fails to parse.
3. **The Jira half of AC 24 is in `tests/work/jira/test_jira_validate_offline.py`**,
   beside the fake, not in `test_validate_target.py`.
4. **`Finding.__str__` puts a multi-line message on one line** (spec note added).
5. **A blocker in a project that is here but cannot be read is a `warning`**
   (`references.BROKEN`), naming `tcw validate` there; `unresolved` stays for an
   unreachable project only (plan choice 9).
6. **`tcw provision` on an existing checkout that is unusable is an error**
   after the declared-checkout and layout checks, since it may no longer fetch.
7. **`tcw init` without an id exits 2** (plan choice 12).
8. **Found by the contract test (Task 15) and fixed:** `provision` and `serve`
   printed "no tcw node here" and returned 1 themselves; every command now
   raises one `NO_PROJECT` message. A created item folder is named
   `created <path>/` like other created folders. An absent declared project's
   message names `tcw provision`, as AC 12 asks.
9. **Help text spells no stage name.** `tests/work/test_model_guards.py` forbids
   stage names outside the stage table, so the help examples take theirs from
   the table (`start_stage()`, `completion_stage()`); fixed in Task 15.
10. **`MIGRATION_GUIDE` lives in `tcw/store/base.py`**, used by the retired
    fields, the retired key and the work configuration alike.
11. **The `procedure` row works outside a project** (plan choice 3; spec note
    added).
12. **AC 25's static test allows more classes than the criterion lists**
    (spec note added).
13. **`validate`'s finding for a broken work configuration** names
    `tcw-config.yaml` relative to the project and no longer repeats the path
    in its message (found while checking this repository's ledger, Task 19).
14. **One renamed ledger record.** `work/declare-capability-changes-in-a-child-nodes-ledger`
    is now `…-child-projects-ledger`; the declaration lists it as removed and
    new. Its `Planning doc` line was dropped with the rename, since its value
    named "nodes" and AC 21's check reads every `meta.yaml`. Records this item
    did not otherwise touch keep their `Planning doc` lines for TCW-76.
15. **The records were written with a helper agent** working only in
    `docs/capabilities/` and `docs/taxonomy/`, then checked here: AC 21's grep
    prints nothing, `test_ledger_3_0.py` passes, and `tcw validate` on the
    branch reports no ledger or taxonomy finding other than the expected
    `Planning doc` and `Tracker` ones and the repository's 2.x `work` keys.

## Records gate

`records_problems(..., finished=True)` over this item's `capabilities.yaml`,
against the branch's ledger and taxonomy, reports no problem. Declaring the
removal of a record that still exists (`cli/scaffold-the-doc-trees`) makes it
report one.

## Documentation

| Entry | Handled |
| --- | --- |
| `README.md` | Deferred to TCW-75; the allowance lists what it may still name. |
| `docs/guide/jira.md` | Does not fire. |
| `docs/guide/<topic>.md` | Deferred to TCW-75. |
| Release notes (upcoming) | Written (Task 20). |
| Changelog (upcoming) | Written (Task 20). |
| `skills/<component>/SKILL.md` | Deferred to TCW-74. |
| `skills/configure/references/` | Deferred to TCW-75 (`connected-projects` there is allowed by `REFUSED_KEYS`). |

## For later children

- **TCW-72:** add `config show`, `--mine` and `--assign-me` each with a row in
  `tests/test_cli_contract.py`'s `ROWS` and a help entry through
  `tcw/cli_help.py`; `test_cli_help_standard.py`'s `SURFACE` gains
  `config show`.
- **TCW-74:** skills, agents and prompts still name `procedure prompt`,
  `work nodes`, `<axis> init`, `taxonomy check` and the `connected-projects`
  key; shrink `tests/doc_allowance.py` as they go.
- **TCW-75:** README, guides and `skills/configure/` for the same names, the
  output contract and the exit-code table.
- **TCW-76:** the migration guide's table must cover everything in
  `REMOVED_COMMANDS`, `REMOVED_FLAGS`, `REMOVED_FORMS` and `REFUSED_KEYS`,
  plus `TCW_NODE_ROOT`. This repository's capability records still carry
  `Planning doc` (and some `Tracker`), which `tcw validate` now reports.
- **TCW-77:** `tcw/serve/` still says "node" (excluded from the sweep) and
  prints its own "no tcw node here" in `tcw/serve/runtime.py`; it now imports
  `find_project_root` and `descendant_projects` and reads `store.project_root`.
- **The full suite** has not been run on this branch, by instruction; run it
  before the epic merges. Tests marked "not ported in TCW-70" still name 2.x
  wording and stay skipped.

## Review fixes (2026-10-13)

An adversarial review of the branch at `20f0b9f4` raised the findings below.
All are fixed on the branch except S1, which was narrowed (reason given).
Commits on `work/2026-10-01-tcw-73-…`: `e83c759f` stores, `e7d85801` the
retired key, `e510f3b6` records and scenarios, `090795e0` the output contract,
`12cf7886` the config-writer test, `bde41393` the notes. Spec notes on `main`:
`debde570`.

| Finding | Commit | Test |
| --- | --- | --- |
| S1 `taxonomy rm` left a reference to a sub-folder without `meta.yaml` | `e83c759f` | `tests/test_taxonomy_rm_gaps.py::test_a_reference_to_a_folder_under_the_term_refuses_the_removal`, `…::test_a_term_naming_a_folder_under_the_term_refuses_the_removal` |
| S2 a partial delete named nothing and raised a raw `[Errno 13]` | `e83c759f` | `tests/test_partial_removal.py` (taxonomy rm, capabilities rm, capabilities reset; skipped as root) |
| S3 `extends add 'Bad ID!'` exited 1 | `e83c759f` | `tests/test_taxonomy_cli_contract.py::test_extends_add_of_a_malformed_name_is_a_usage_error` (both axes) |
| S4 guards missed "-ing" git words and `from sys import stdin` | `e83c759f` | `tests/test_static_guards.py::test_the_guard_sees_an_ing_form_of_a_git_word`, `…::test_the_stdin_guard_sees_a_prompt` |
| R1 the old key refused only by some commands; `projects list` hid registry problems | `e7d85801` | `tests/test_projects_list.py::test_every_command_refuses_the_2x_key` (projects list, provision, work list, work new --project, taxonomy list), `…::test_provision_refuses_the_2x_key_in_a_child`, `…::test_an_upstreams_own_2x_key_is_not_its_readers_problem`, `…::test_projects_list_reports_a_registry_problem` |
| R2 the key pattern matched inside slugs | `e7d85801` | `tests/test_documented_cli_surface.py::test_the_top_key_pattern_matches_the_key_and_not_a_slug` |
| D1–D5 records and scenarios | `e510f3b6` | `tests/test_ledger_3_0.py` (D4); D1, D2, D3, D5 are text |
| C1 short output into a closed pipe exited 120 | `090795e0` | `tests/test_cli_handler.py::test_a_reader_gone_before_short_output_exits_quietly` (subprocess) |
| C2 `tags rm` of an unregistered tag exited 0 | `090795e0`, `12cf7886` | `tests/test_cli_contract.py::test_tags_rm_of_an_unregistered_tag_is_not_found`, `tests/test_config_edit_writers.py::test_a_tags_change_that_changes_nothing_writes_nothing` |
| C3 `validate --remote` called a broken Jira config "filesystem" | `090795e0` | `tests/work/jira/test_jira_validate_remote.py::test_a_jira_project_with_a_broken_work_config_is_not_called_filesystem` |
| C4 a late Jira failure printed no name | `090795e0` | `tests/work/jira/test_jira_tickets.py::test_new_whose_read_back_fails_names_the_item`, `…::test_adopt_whose_read_back_fails_names_the_item`, `…::test_adopt_whose_move_fails_names_the_item` |
| C5 the contract test was narrower than Design 10 | `090795e0` | `tests/test_cli_contract.py::test_the_reading_commands_in_a_project`, `…::test_the_writing_work_commands_in_a_project`, `…::test_the_writing_tree_commands_in_a_project`, `…::test_jira_edit_comment_and_rename`, `…::test_jira_tickets_adopt` |
| C6 `moved <old> to <new>` was not in Design 1.2 | `debde570` (spec), `090795e0` (test) | `MOVED` and `unnamed()` in `tests/test_cli_contract.py`, exercised by the rename rows |
| N1 notes shaped like error lines; an indented warning | `090795e0` | `tests/test_stdin.py::test_nothing_arrives_proceeds_with_a_warning`, `tests/test_project_overrides.py::test_an_override_warning_is_a_warning_line`; `checked()` in the contract test refuses an error-shaped line on success |
| N2 a rolled-back create named the folder | `090795e0` | `tests/test_cli_handler.py::test_a_create_rolled_back_names_each_file_removed` |
| N3 `edit --blocks` into another project lacked the uncommitted note | `090795e0` | `tests/work/test_cli_items.py::test_edit_blocks_into_another_project` |
| N4 validate's `<where>` absolute in some findings; path repeated | `090795e0` | `tests/test_validate_command.py::test_a_config_finding_names_the_file_relative_to_the_project`, `…::test_the_former_child_warning_names_its_file_once` |
| N5 present but unreadable project is a warning | `debde570` (spec note) | unchanged behaviour |
| N6 duplicate-key finding dropped for one Jira item | `090795e0` | `tests/test_validate_target.py::test_one_jira_item_sharing_its_key_with_another_folder` |
| N7 help standard 5 untested | `090795e0` | `tests/test_cli_help_standard.py::test_choices_are_shown_in_the_help` |

**S1, narrowed.** The review proposed counting every listed sub-folder as a
nested term, so `rm` would refuse. That contradicts two existing tests that
hold Design 8.2's decision: a sub-folder holding only `.DS_Store`/`Thumbs.db`,
or a stray `notes.md`, goes with the term (otherwise such a term could never be
removed). The defect the review found is the dangling reference, so the fix is
there: `rm` refuses when any term or capability names the term's folder **or
any folder inside it**. A meta-less sub-folder nothing names still goes with the
term.

**S2, how.** `_rm` lists the files first, and when `shutil.rmtree` stops partway
it reads back which of them are gone, records those, and raises "the removal
was partial: N of M files removed; still present: …". No `onexc`/`onerror`
handler was needed, so nothing depends on the Python version.

**R1, how.** `refuse_retired_config` (`tcw/store/fs.py`) runs once in `main`
before every command except `validate`, which reports the key as a finding.
`declared_connected_projects` reports it too, so `provision` names a child that
still holds it; an upstream's own config is not read by either.

### Mutation checks for the fixes

Each was applied, the named test went red for the stated reason, and the code
was restored.

- S1: `_in_folder` back to `_same_folder` in both reference checks: both S1 tests exit 0 instead of 3.
- S2: the `except OSError` in `_rm` never matching: raw `[Errno 13]`, no `removed` lines. The handlers' `finally: changed(...)` removed: no `removed` lines.
- S3: re-raising the `ValueError`: exit 1, not 2.
- S4: an "-ing" git word and `from sys import stdin as _probe` added to `tcw/work/cli.py`: both guards report them.
- R1: the `main` check removed: `work list` and `work new --project` exit 0 and 3. `require_valid` removed from `projects list`: the invalid child is silently omitted. `declared_connected_projects` ignoring the key: provision passes over the child.
- R2: the old `\b…\b` pattern: matches `cli/list-connected-projects`.
- C1: the flush in `main` removed: exit 120 with "Exception ignored while flushing sys.stdout".
- C3: the old `read_work_config`-based check: exit 2 with the false usage error.
- C4: the backend and adopt fixes reverted: all three tests print nothing on stdout.
- N2, N3, N4, N6: each fix reverted: its test goes red (folder line printed; no "uncommitted in"; absolute `where`; path repeated; duplicate-key finding missing).
- The reviewer's own C5 mutations, re-run against the extended contract test:
  `print` added after success in `_path` (red: reading commands),
  `_discard` (red: writing work commands), `_tags_list` (red: reading commands
  and the C2 test); `print` added to `JiraBackend.comment` and to
  `JiraBackend.update` (red: `test_jira_edit_comment_and_rename`); `wrote(path)`
  dropped from `_write_tags` (red: writing work commands). Also: the `moved`
  line dropped from the filesystem rename (red), and C2's refusal disabled (red).

### Tests run for the fixes

Not the full suite. With a private venv on the worktree: every file named in
the table above, plus `tests/work/`, the taxonomy and capabilities test files,
`tests/test_cli_contract.py`, `test_documented_cli_surface.py`,
`test_static_guards.py`, the registry, provisioning, override and multiproject
files: all pass (2018 + 684 + 295 + 373 across four runs, skips are the
"not ported" tests). `pytest --collect-only -q`: 3632 collected, no errors.
Note that `tests/test_stdin_cli.py`'s stdin-warning case is skipped as not
ported, so the warning prefix is held by `tests/test_stdin.py` instead.
