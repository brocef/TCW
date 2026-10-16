# Outcome — pre-freeze clean-up

Work branch `work/2026-10-15-fix-what-tcw-71-to-tcw-75-s-reviews-left-in-the-3-0-code-before-the-freeze`,
from `epic/tcw-3.0` at `e301bef5`.

## Commits

- Task 1 `627848f5`, Task 2 `ccf86a9a` (previous session).
- Task 3 `72d19a12` (the WIP commit `ac282f61`, amended after it was
  compared with the plan, tested and mutation-checked), Task 4 `db4e749a`,
  Task 5 `be977ad5`, Task 6 `70ba3b95`, Task 7 `fe43d6e3`, Task 8 `4acea8bf`.
- Review fix round `a0db5a98`..`aa6f94c5` (nine commits); final fixes
  `1d4e2032`..`1c34dfe9` (eight commits).
- Task 9 `6f0440b7`, `6746f629`.

## Deviations from the plan

- C4: `GIT_ASKPASS` is set to the empty string, not removed, since an unset
  variable lets git fall back to `core.askPass` (spec amended). The user's own
  ssh command is found with one `git config --show-scope --includes --get-all
  core.sshCommand` read, counting every scope but `local` and `worktree`.
- T5 also covers single-item validation (owner's choice, 2026-10-16),
  including a given item at a finished stage.
- Added at the owner's choice during review: the Jira token is no longer sent
  on a redirect (also published as 2.8.3), a 401 after a redirect names the
  redirect, `tcw provision` refuses a `tcw-config.yaml` it cannot parse, a
  `tcw-config.yaml` that is not UTF-8 is named, and `work new --project
  --stage` is a usage error.
- The block reader treats a table row and a heading as blocks of their own
  (Task 7). Task 2's tests are in `tests/config/test_config_edges.py`.
- No 2.x test was deleted or skipped. 3.0 tests rewritten: two in
  `tests/work/jira/test_jira_validate_remote.py`, the AC 24 test of TCW-73,
  six in `tests/serve/test_records.py` (they now send a revision) and
  `tests/serve/test_records.py:87` (the `parent=` form).
- `pnpm typecheck` fails across the repository on its Prettier check (271
  files, none touched here); `pnpm test`, `tsc`, lint and `check:build` pass.
- Left failing, not caused here: `tests/test_prompt_fallback.py::test_an_unconfigured_project_sees_the_recorded_bytes[review]`,
  whose recorded fixture predates TCW-74's "Who reviews" paragraph (owner
  chose not to refresh it in this item).

## Task 9 (J2): the live run

The owner did checklist steps 1 and 2; the agent linked the transition's
screen in the owner's browser (it had been left off) and confirmed steps 1 to 3
by REST GET. Step 4 (delete permission) was skipped: TCWTEST's permission
scheme 10002 is shared with PRPI, TCW and TCWCLAIM. One live run, passed in
74.7 s; Jira writes were 101 creates and one move with no comment. Probe
tickets TCWTEST-86 to TCWTEST-186 remain for the owner to delete
(`project = TCWTEST AND summary ~ "\"J2 paging probe\""`). The recordings
matched what `JiraClient.search`, `transitions` and `remote._definition` read,
so step 4 of Task 9 changed nothing.

### Its output

```text
============================= test session starts ==============================
platform darwin -- Python 3.14.6, pytest-9.1.1, pluggy-1.7.0
rootdir: /Users/brian/Projects/TCW/.worktrees/2026-10-15-fix-what-tcw-71-to-tcw-75-s-reviews-left-in-the-3-0-code-before-the-freeze
configfile: pyproject.toml
plugins: asyncio-1.4.0, anyio-4.14.2
asyncio: mode=Mode.STRICT, debug=False, asyncio_default_fixture_loop_scope=None, asyncio_default_test_loop_scope=function
collected 1 item

tests/work/jira/test_jira_live_shapes.py step 1: 0 probe tickets already exist
step 1: 101 probe tickets in all
step 2: search found every probe after 0.5s
step 2: page 1: 100 issues, isLast False, nextPageToken str
step 2: page 2: 1 issues, isLast True, nextPageToken NoneType
step 2: 2 pages held all 101 probe keys, each once
step 3: JiraClient.search returned all 101 probe keys, each once
step 4: [{'id': '2', 'name': 'J2 probe: reopen', 'type': 'DIRECTED', 'links': [{'fromStatusReference': '10041', 'fromPort': 7, 'toPort': 3}]}]; other types ['DIRECTED', 'GLOBAL', 'INITIAL'], global links ['[]']
step 5: TCWTEST-186 was at 'To Do', moved to 'Won't Do'
step 5: Transition(id='2', name='J2 probe: reopen', to_status='To Do', to_status_id='10012', fields=('labels',), required=(), has_screen=True)
clean-up: the account may not delete tickets in TCWTEST, so none was deleted
clean-up: 101 probe tickets remain, kept in /private/tmp/claude-501/-Users-brian-Projects-TCW/08cee05f-e27b-44e4-804e-304993a161cb/scratchpad/j2-capture/j2-keys.json: TCWTEST-86 TCWTEST-87 TCWTEST-88 TCWTEST-89 TCWTEST-90 TCWTEST-91 TCWTEST-92 TCWTEST-93 TCWTEST-94 TCWTEST-95 TCWTEST-96 TCWTEST-97 TCWTEST-98 TCWTEST-99 TCWTEST-100 TCWTEST-101 TCWTEST-102 TCWTEST-103 TCWTEST-104 TCWTEST-105 TCWTEST-106 TCWTEST-107 TCWTEST-108 TCWTEST-109 TCWTEST-110 TCWTEST-111 TCWTEST-112 TCWTEST-113 TCWTEST-114 TCWTEST-115 TCWTEST-116 TCWTEST-117 TCWTEST-118 TCWTEST-119 TCWTEST-120 TCWTEST-121 TCWTEST-122 TCWTEST-123 TCWTEST-124 TCWTEST-125 TCWTEST-126 TCWTEST-127 TCWTEST-128 TCWTEST-129 TCWTEST-130 TCWTEST-131 TCWTEST-132 TCWTEST-133 TCWTEST-134 TCWTEST-135 TCWTEST-136 TCWTEST-137 TCWTEST-138 TCWTEST-139 TCWTEST-140 TCWTEST-141 TCWTEST-142 TCWTEST-143 TCWTEST-144 TCWTEST-145 TCWTEST-146 TCWTEST-147 TCWTEST-148 TCWTEST-149 TCWTEST-150 TCWTEST-151 TCWTEST-152 TCWTEST-153 TCWTEST-154 TCWTEST-155 TCWTEST-156 TCWTEST-157 TCWTEST-158 TCWTEST-159 TCWTEST-160 TCWTEST-161 TCWTEST-162 TCWTEST-163 TCWTEST-164 TCWTEST-165 TCWTEST-166 TCWTEST-167 TCWTEST-168 TCWTEST-169 TCWTEST-170 TCWTEST-171 TCWTEST-172 TCWTEST-173 TCWTEST-174 TCWTEST-175 TCWTEST-176 TCWTEST-177 TCWTEST-178 TCWTEST-179 TCWTEST-180 TCWTEST-181 TCWTEST-182 TCWTEST-183 TCWTEST-184 TCWTEST-185 TCWTEST-186
clean-up: they are found by: project = TCWTEST AND summary ~ "\"J2 paging probe\""
.

========================= 1 passed in 74.74s (0:01:14) =========================
```

## Mutation record (Task 10)

Tasks 1 and 2 were mutation-checked in the previous session; those results were not saved, and the owner chose not to repeat them.


#### Task 3: P4: move the stdin read back before creation_stage

- Expected: the P4 test's patched read_piped_stdin raises: 'standard input was read before the usage error'
- Tests: tests/work/test_cli_surface.py::test_new_at_the_inbox_is_refused_before_piped_input_is_read
- Result: **RED** (1 failed in 1.61s)
- Reason check: failure output contains `standard input was read before the usage error`
  - `E       AssertionError: standard input was read before the usage error`
  - `FAILED tests/work/test_cli_surface.py::test_new_at_the_inbox_is_refused_before_piped_input_is_read`
- Restored; file content matches the original.

#### Task 3: C1: drop reset's nested check

- Expected: reset deletes the override and the nested capability; exit 0 instead of 3
- Tests: tests/test_capabilities_cli_contract.py::test_reset_refuses_a_capability_nested_under_the_override
- Result: **RED** (1 failed in 0.26s)
- Reason check: failure output contains `assert (0, '') == (3, '')`
  - `E       AssertionError: removed docs/capabilities/auth/login/meta.yaml`
  - `E         removed docs/capabilities/auth/login/nested/description.md`
  - `E         removed docs/capabilities/auth/login/nested/meta.yaml`
  - `E`
  - `E       assert (0, '') == (3, '')`
  - `E`
- Restored; file content matches the original.

#### Task 3: C2: drop the slug check

- Expected: taxonomy add --slug 'A B' exits 0 instead of 2
- Tests: tests/test_taxonomy.py::test_cli_add_refuses_a_slug_that_is_not_one, tests/serve/test_records.py::test_a_slug_that_is_not_one_is_400_without_naming_a_flag
- Result: **RED** (1 failed in 0.11s)
- Reason check: failure output contains `assert 0 == 2`
  - `E       AssertionError: assert 0 == 2`
  - `E        +  where 0 = <function main at 0x108307950>(['taxonomy', 'add', 'X', '--slug', 'A B'])`
  - `FAILED tests/test_taxonomy.py::test_cli_add_refuses_a_slug_that_is_not_one[A B]`
- Restored; file content matches the original.

#### Task 3: C4: drop the _run environment

- Expected: the clone call carries no env, so env['GIT_TERMINAL_PROMPT'] fails (env is None)
- Tests: tests/test_store_provisioning.py::test_git_is_told_never_to_prompt
- Result: **RED** (1 failed in 0.08s)
- Reason check: failure output contains `TypeError: 'NoneType' object is not subscriptable`
  - `E       TypeError: 'NoneType' object is not subscriptable`
  - `FAILED tests/test_store_provisioning.py::test_git_is_told_never_to_prompt - T...`
- Restored; file content matches the original.

#### Task 3: C8: restore the bare SENTINEL

- Expected: run from fx/docs, the message says 'tcw-config.yaml' instead of '../tcw-config.yaml'
- Tests: tests/test_projects_list.py::test_the_2x_key_refusal_names_the_file_from_a_sub_folder
- Result: **RED** (1 failed in 0.23s)
- Reason check: failure output contains `: ../tcw-config.yaml: the key`
  - `E       AssertionError: tcw taxonomy list: tcw-config.yaml: the key 'connected-projects' was renamed to 'projects' in TCW 3.0 — see docs/migration-guide-2.8-to-3.0.0.md`
  - `E`
  - `E       assert ": ../tcw-config.yaml: the key 'connected-projects'" in "tcw taxonomy list: tcw-config.yaml: the key 'connected-projects' was renamed to 'projects' in TCW 3.0 — see docs/migration-guide-2.8-to-3.0.0.md\n"`
  - `FAILED tests/test_projects_list.py::test_the_2x_key_refusal_names_the_file_from_a_sub_folder`
- Restored; file content matches the original.

#### Task 3: C9: drop require_valid() from open_backend

- Expected: work list exits 0 with the child's retired key instead of 1
- Tests: tests/test_projects_list.py::test_work_list_refuses_the_2x_key_in_a_child
- Result: **RED** (1 failed in 0.27s)
- Reason check: failure output contains `== (1, '')`
  - `E       AssertionError:`
  - `E       assert (0, '') == (1, '')`
  - `E`
  - `E         At index 0 diff: 0 != 1`
  - `E         Use -v to get more diff`
  - `FAILED tests/test_projects_list.py::test_work_list_refuses_the_2x_key_in_a_child`
- Restored; file content matches the original.

#### Task 3: C2: drop the slug check (viewer create route)

- Expected: the viewer creates the term and answers 201 instead of 400
- Tests: tests/serve/test_records.py::test_a_slug_that_is_not_one_is_400_without_naming_a_flag
- Result: **RED** (1 failed in 0.58s)
- Reason check: failure output contains `400`
  - `E       AssertionError: b'{"term": {"slug": "A B", "name": "X", "description": "", "kind": "Vocabulary", "relates_to": [], "vocabulary": [], "..."origin": "local", "modified": "2026-10-16T15:31:22.937845Z", "qualified": `
  - `E       assert 201 == 400`
  - `E        +  where 201 = Response(status=201, headers={'server': 'BaseHTTP/0.6 Python/3.14.6', 'date': 'Fri, 16 Oct 2026 15:31:22 GMT', 'conten...origin": "local", "modified": "2026-10-16T15:31:22.937845Z", "qualified": "`
  - `FAILED tests/serve/test_records.py::test_a_slug_that_is_not_one_is_400_without_naming_a_flag[A B]`
- Restored; file content matches the original.

#### Task 4: T7: remove the external skip from round_findings

- Expected: the Jira-mode qa round gets 'the latest qa round is invalid' again
- Tests: tests/work/jira/test_jira_validate_offline.py::test_a_qa_round_is_only_ignored
- Result: **RED** (1 failed in 0.14s)
- Reason check: failure output contains `latest qa round is invalid`
  - `E       AssertionError: warning: docs/work/TCW-1-x/qa: Jira keeps the qa record, so this folder is ignored`
  - `E         warning: docs/work/TCW-1-x/qa/round-1.md: the latest qa round is invalid: its front matter needs `verdict: accepted` or `verdict: rejected` and a whole-number `judges`, and `tcw work advance` refuses past qa un`
  - `E         0 errors, 2 warnings, 0 unresolved`
  - `E`
  - `E       assert 'latest qa round is invalid' not in 'warning: do...unresolved\n'`
  - `E`
- Restored; file content matches the original.

#### Task 4: T5: remove the offline parse check

- Expected: offline validate exits 0 with a malformed capabilities.yaml
- Tests: tests/work/jira/test_jira_validate_offline.py::test_a_malformed_declaration_is_one_error_naming_the_file
- Result: **RED** (1 failed in 0.17s)
- Reason check: failure output contains `assert 0 == 1`
  - `E       AssertionError: 0 errors, 0 warnings, 0 unresolved`
  - `E`
  - `E       assert 0 == 1`
  - `FAILED tests/work/jira/test_jira_validate_offline.py::test_a_malformed_declaration_is_one_error_naming_the_file`
- Restored; file content matches the original.

#### Task 4: T5: remove the --remote skip of a declaration that does not parse

- Expected: with --remote the malformed file is reported twice (offline at the file, remote at the item)
- Tests: tests/work/jira/test_jira_validate_remote.py::test_a_malformed_declaration_is_reported_once_with_remote
- Result: **RED** (1 failed in 1.42s)
- Reason check: failure output contains `error: tcw/TCW-3-open: capabilities.yaml: unknown key`
  - `E       AssertionError: error: docs/work/TCW-3-open/capabilities.yaml: capabilities.yaml: unknown key(s) no-such-key; expected new, changed, removed or taxonomy`
  - `E         warning: tcw/TCW-3-open: stage is at implement but has nothing from spec; an item forced past a stage warns until it is finished`
  - `E         warning: tcw/TCW-3-open: stage is at implement but has nothing from plan; an item forced past a stage warns until it is finished`
  - `E         error: tcw/TCW-3-open: capabilities.yaml: unknown key(s) no-such-key; expected new, changed, removed or taxonomy`
  - `E`
  - `E       assert ['error: docs... or taxonomy'] == ['error: docs... or taxonomy']`
- Restored; file content matches the original.

#### Task 5: V5: restore the nesting in `Conflict` (buttons' Flex and `Text as="p"` back inside `Callout.Text`)

- Expected: the vitest test sees React's DOM-nesting warning on `console.error`
- Tests: web/client/src/ui/content-views.test.tsx (vitest)
- Result: **RED** (1 failed, 7 passed)
- Reason check: failure output contains `In HTML, %s cannot be a descendant of <%s>.` ("expected "error" to not be called at all, but actually been called 4 times")
- Restored; file content matches the fixed version.

#### Task 5: V1: revision optional again (required=False)

- Expected: a PATCH without revision saves and answers 200 instead of 400
- Tests: tests/serve/test_records.py::test_a_save_without_a_revision_is_400
- Result: **RED** (1 failed in 0.72s)
- Reason check: failure output contains `assert 200 == 400`
  - `E       AssertionError: b'{"term": {"slug": "work-item", "name": "Work item", "description": "Changed.\`
  - `E         ", "kind": "Vocabulary", "relates_to"...n": "local", "modified": "2026-10-16T15:45:18.414365Z", "qualified": "work-item"}, "coreRevision": "14e4d74cc76f61d9"}'`
  - `E       assert 200 == 400`
  - `E        +  where 200 = Response(status=200, headers={'server': 'BaseHTTP/0.6 Python/3.14.6', 'date': 'Fri, 16 Oct 2026 15:45:18 GMT', 'conten...": "local", "modified": "2026-10-16T15:45:18.414365Z", "qualified": "work-i`
  - `FAILED tests/serve/test_records.py::test_a_save_without_a_revision_is_400[taxonomy/work-item]`
- Restored; file content matches the original.

#### Task 5: V1: revision optional again on the capability route

- Expected: a capability PATCH without revision answers 200 instead of 400
- Tests: tests/serve/test_records.py::test_a_save_without_a_revision_is_400[capabilities/web]
- Result: **RED** (1 failed in 0.67s)
- Reason check: failure output contains `assert 200 == 400`
  - `E       AssertionError: b'{"capability": {"path": "web", "name": "Web app", "id": "cap-943f86", "fields": {"Status": "Missing"}, "body": "Chan...odified": "2026-10-16T15:45:19.309239Z", "status": "Missing", "qualified": `
  - `E       assert 200 == 400`
  - `E        +  where 200 = Response(status=200, headers={'server': 'BaseHTTP/0.6 Python/3.14.6', 'date': 'Fri, 16 Oct 2026 15:45:19 GMT', 'conten...dified": "2026-10-16T15:45:19.309239Z", "status": "Missing", "qualified": "`
  - `FAILED tests/serve/test_records.py::test_a_save_without_a_revision_is_400[capabilities/web]`
- Restored; file content matches the original.

#### Task 5: V2: drop the containment check

- Expected: the GET reads the outside file (200) and the PUT writes spec.md into the outside folder
- Tests: tests/serve/test_files.py::test_a_stage_folder_linked_outside_is_not_read_or_written
- Result: **RED** (1 failed in 1.32s)
- Reason check: failure output contains `assert 200 == 404`
  - `E       AssertionError: b'{"content": "secret\`
  - `E         ", "revision": "b37e50cedcd3e3f1ff64f4afc0422084ae694253cf399326868e07a35f4a45fb"}'`
  - `E       assert 200 == 404`
  - `E        +  where 200 = Response(status=200, headers={'server': 'BaseHTTP/0.6 Python/3.14.6', 'date': 'Fri, 16 Oct 2026 15:45:20 GMT', 'conten...f'"}, body=b'{"content": "secret\\n", "revision": "b37e50cedcd3e3f1ff64f4af`
  - `FAILED tests/serve/test_files.py::test_a_stage_folder_linked_outside_is_not_read_or_written`
- Restored; file content matches the original.

#### Task 5: V2: drop the check from the declaration routes only

- Expected: the declaration GET follows the link and answers 200 with the outside file's lists
- Tests: tests/serve/test_files.py::test_a_declaration_linked_outside_is_not_read_or_written
- Result: **RED** (1 failed in 0.65s)
- Reason check: failure output contains `assert 200 == 404`
  - `E           AssertionError: b'{"revision": "ba3aad210b75716db80ed1bd227277b031c4c2dbc1a1f84e02e5109e33c0fd48", "present": true, "problem": null, "capabilities": {"new": ["secret"], "changed": [], "removed": []}, "taxonom`
  - `E           assert 200 == 404`
  - `E            +  where 200 = Response(status=200, headers={'server': 'BaseHTTP/0.6 Python/3.14.6', 'date': 'Fri, 16 Oct 2026 15:45:21 GMT', 'conten...abilities": {"new": ["secret"], "changed": [], "removed": []}, "taxonom`
  - `FAILED tests/serve/test_files.py::test_a_declaration_linked_outside_is_not_read_or_written`
- Restored; file content matches the original.

#### Task 5: V2: drop the containment check (write half only, through a temporary probe test)

- Expected: the PUT answers 200 and spec.md appears in the outside folder
- Tests: tests/serve/test_zz_v2_probe.py
- Result: **RED** (1 failed in 0.63s)
- Reason check: failure output contains `assert 200 == 404`
  - `E       AssertionError: b'{"revision": "603c828a03383f98b82bf9c6787deeb5c40c02871a1b8d6ba14b0d538020a02b"}'`
  - `E       assert 200 == 404`
  - `E        +  where 200 = Response(status=200, headers={'server': 'BaseHTTP/0.6 Python/3.14.6', 'date': 'Fri, 16 Oct 2026 15:45:33 GMT', 'conten...licy': "default-src 'self'"}, body=b'{"revision": "603c828a03383f98b82bf9c6`
  - `FAILED tests/serve/test_zz_v2_probe.py::test_write_half - AssertionError: b'{...`
- Restored; file content matches the original.

#### Task 6: the stage-name guard (existing guard; no new guard, so no mutation)

- Before the fix (Tasks 3-5 runs, `tcw/work/config.py` as on `e301bef5`):
  `tests/work/test_model_guards.py::test_no_stage_name_is_spelled_outside_the_table[config.py]`
  was **RED**, naming `config.py:65` ("postmortem stage prompt"), `:67` ("plan stage prompt")
  and `:71` ("an outside plan").
- After the fix (names built from the table's columns; the third message reworded): **GREEN**.

#### Task 7: C3: remove the -c value skip

- Expected: `["git", "-c", "a=b", "switch", "x"]` is read as verb 'a=b', not 'switch'
- Tests: tests/work/test_git_write_scan.py::test_the_scan_reads_every_spelling
- Result: **RED** (1 failed in 0.03s)
- Reason check: failure output contains `-c`
  - `E           AssertionError: ["git", "-c", "a=b", "switch", "x"]`
  - `E           assert 'a=b' == 'switch'`
  - `E`
  - `E             - switch`
  - `E             + a=b`
  - `FAILED tests/work/test_git_write_scan.py::test_the_scan_reads_every_spelling`
- Restored; file content matches the original.

#### Task 7: C3: remove `switch` from the verbs; the planted ["git", "-C", r, "switch", "x"] is not reported

- Expected: the planted switch call is not reported, so the test's single finding is missing
- Tests: tests/work/test_git_write_scan.py::test_each_added_verb_is_reported[switch]
- Result: **RED** (1 failed in 0.03s)
- Reason check: failure output contains `ValueError: not enough values to unpack`
  - `E       ValueError: not enough values to unpack (expected 1, got 0)`
  - `FAILED tests/work/test_git_write_scan.py::test_each_added_verb_is_reported[switch]`
- Restored; file content matches the original.

#### Task 7: C3: re-key the allowance on the class; a clone planted in another method

- Expected: the clone in FsStoreProvisioner.other passes as allowed
- Tests: tests/work/test_git_write_scan.py::test_the_allowance_covers_only_the_one_method
- Result: **RED** (1 failed in 0.03s)
- Reason check: failure output contains `assert [] == [`
  - `E       AssertionError: assert [] == ['planted.py:...Provisioner)']`
  - `E`
  - `E         Right contains one more item: 'planted.py:6: git clone (in other < FsStoreProvisioner)'`
  - `E         Use -v to get more diff`
  - `FAILED tests/work/test_git_write_scan.py::test_the_allowance_covers_only_the_one_method`
- Restored; file content matches the original.

#### Task 7: C3: remove --no-optional-locks from the status call in tcw/store/fs.py

- Expected: the status check reports store/fs.py
- Tests: tests/work/test_git_write_scan.py::test_every_status_keeps_no_optional_locks
- Result: **RED** (1 failed, 7 passed in 0.06s)
- Reason check: failure output contains `git status without --no-optional-locks`
  - `E       AssertionError: assert ['store/fs.py...tional-locks'] == []`
  - `E`
  - `E         Left contains one more item: 'store/fs.py:206: git status without --no-optional-locks'`
  - `E         Use -v to get more diff`
  - `FAILED tests/work/test_git_write_scan.py::test_every_status_keeps_no_optional_locks[store/fs.py]`
- Restored; file content matches the original.

#### Task 7: C6: remove the PATH prepend, with a folder first on PATH holding a `tcw` that prints `tcw 2.8.2`

- Expected: `shutil.which("tcw")` finds the planted script instead of the interpreter's
- Tests: tests/test_suite_runs_its_own_tcw.py, run with `PATH=<fake-tcw>:<venv>/bin:...`
- Result with the prepend in place (control): GREEN (1 passed)
- Result with the prepend removed: **RED** (1 failed): `assert PosixPath('.../fake-tcw') == PosixPath('.../venv/bin')`
- Restored; `tests/conftest.py` matches the fixed version.

#### Task 7: V4: plant `review` as a literal inside ${...} in a client file (web/client/src/planted.ts)

- Expected: the client scan reports planted.ts
- Tests: tests/serve/test_no_stage_names.py::test_no_client_literal_names_a_stage
- Result: **RED** (1 failed, 6 passed in 0.03s)
- Reason check: failure output contains `planted.ts:1: 'review'`
  - `E       AssertionError: planted.ts:1: 'review'`
  - `E       assert not ["planted.ts:1: 'review'"]`
  - `FAILED tests/serve/test_no_stage_names.py::test_no_client_literal_names_a_stage[planted.ts]`
- Restored; file content matches the original.

#### Task 7: V4: plant `review` as an unquoted object key in a client file (web/client/src/planted.ts)

- Expected: the client scan reports planted.ts
- Tests: tests/serve/test_no_stage_names.py::test_no_client_key_or_member_is_a_stage
- Result: **RED** (1 failed, 6 passed in 0.03s)
- Reason check: failure output contains `planted.ts:1: review`
  - `E       AssertionError: planted.ts:1: review`
  - `E       assert not ['planted.ts:1: review']`
  - `FAILED tests/serve/test_no_stage_names.py::test_no_client_key_or_member_is_a_stage[planted.ts]`
- Restored; file content matches the original.

#### Task 7: V4: plant `review` as a member name in a client file (web/client/src/planted.ts)

- Expected: the client scan reports planted.ts
- Tests: tests/serve/test_no_stage_names.py::test_no_client_key_or_member_is_a_stage
- Result: **RED** (1 failed, 6 passed in 0.03s)
- Reason check: failure output contains `planted.ts:1: review`
  - `E       AssertionError: planted.ts:1: review`
  - `E       assert not ['planted.ts:1: review']`
  - `FAILED tests/serve/test_no_stage_names.py::test_no_client_key_or_member_is_a_stage[planted.ts]`
- Restored; file content matches the original.

#### Task 7: V4: drop the regex-after-a-keyword rule (first attempt; the test was too weak and was strengthened)

- Expected: the ' inside /it's/ after return starts a string, hiding the real literal
- Tests: tests/serve/test_no_stage_names.py::test_scanner_reads_a_regex_after_a_keyword
- Result: **GREEN (mutation survived)** (3 passed in 0.02s)
- Reason check: failure output does not contain `assert []`
- Restored; file content matches the original.

#### Task 7: V4: drop the regex-after-a-keyword rule

- Expected (strengthened test, plant `return /["']/.test(x) && "review"`): the quote inside the regex starts a string, hiding the real literal
- Tests: tests/serve/test_no_stage_names.py::test_scanner_reads_a_regex_after_a_keyword
- Result: **RED** (for the stated reason: the quote inside the regex started a false string `']/.test(x) && `, so `review` was not seen; the expected-text check in the script named the wrong text, `assert []`) (1 failed in 0.03s)
  - `E       assert [(1, "']/.test(x) && ")] == [(1, 'review')]`
  - `E`
  - `E         At index 0 diff: (1, "']/.test(x) && ") != (1, 'review')`
  - `E         Use -v to get more diff`
  - `FAILED tests/serve/test_no_stage_names.py::test_scanner_reads_a_regex_after_a_keyword[return]`
- Restored; file content matches the original.

#### Task 7: V6: restore the one-line backtick pattern

- Expected: `tcw work\nlist --bogus` is not found as a command
- Tests: tests/test_documented_cli_surface.py::test_a_command_wrapped_inside_its_backticks_is_one_command
- Result: **RED** (1 failed in 4.22s)
- Reason check: failure output contains `ValueError: not enough values to unpack`
  - `E       ValueError: not enough values to unpack (expected 1, got 0)`
  - `FAILED tests/test_documented_cli_surface.py::test_a_command_wrapped_inside_its_backticks_is_one_command`
- Restored; file content matches the original.

#### Task 7: T6: restore line-by-line scanning (every line its own block)

- Expected: scan('TCW no\nlonger ...') finds nothing
- Tests: tests/test_doc_vocabulary.py::test_a_phrase_wrapped_across_a_line_is_found_at_its_first_line
- Result: **RED** (1 failed in 0.02s)
- Reason check: failure output contains `ValueError: not enough values to unpack`
  - `E       ValueError: not enough values to unpack (expected 1, got 0)`
  - `FAILED tests/test_doc_vocabulary.py::test_a_phrase_wrapped_across_a_line_is_found_at_its_first_line`
- Restored; file content matches the original.

#### Task 7: V6/T6 (extra): switch off the table-row, list-item and heading boundaries

- Expected: an unpaired backtick in one row, item or heading pairs with the next line's
- Tests: tests/test_documented_cli_surface.py::test_an_unpaired_backtick_does_not_pair_across_a_boundary
- Result: **RED** (1 failed, 1 passed in 0.09s)
- Reason check: failure output contains `assert [`
  - `E       AssertionError: assert [] == ['tcw work list']`
  - `E`
  - `E         Right contains one more item: 'tcw work list'`
  - `E         Use -v to get more diff`
  - `FAILED tests/test_documented_cli_surface.py::test_an_unpaired_backtick_does_not_pair_across_a_boundary[| a ` b |\n| `tcw work list` |\n]`
- Restored; file content matches the original.

### Fix round


#### Task Fix round 1: J1: count any matching comment, old or new

- Expected: the older identical comment is taken for the lost note; the move reports success (exit 0)
- Tests: tests/work/jira/test_jira_set_stage.py::test_an_older_identical_note_does_not_hide_one_that_did_not_land
- Result: **RED** (1 failed in 0.29s)
- Reason check: failure output contains `assert 0 == 6`
  - `E       AssertionError:`
  - `E       assert 0 == 6`
  - `E        +  where 0 = Result(code=0, out='implement\n', err='').code`
  - `FAILED tests/work/jira/test_jira_set_stage.py::test_an_older_identical_note_does_not_hide_one_that_did_not_land`
- Restored; file content matches the original.

- Note: a first version of this test posted the bare reason as the older comment, which never matched the trace `advance` writes ("Moved from ... Reason: ..."), so the mutation survived. The test was rewritten to make the older comment by the same forced move, and the mutation above was rerun.

#### Task Fix round 2: advance: say 'was not recorded' whatever the backend knows

- Expected: the uncertain case says the trace was not recorded
- Tests: tests/work/jira/test_jira_set_stage.py::test_a_dropped_note_whose_comments_cannot_be_read_may_have_been_posted
- Result: **RED** (1 failed in 0.11s)
- Reason check: failure output contains `the trace may not have been recorded`
  - `E       AssertionError: assert 'the trace may not have been recorded' in 'moved to implement, but the trace was not recorded (tcw/TCW-1-x moved to implement, but the connection failed while p...ad the comments with `tcw `
  - `E        +  where 'moved to implement, but the trace was not recorded (tcw/TCW-1-x moved to implement, but the connection failed while p...ad the comments with `tcw work show tcw/TCW-1-x` before adding it); if it is miss`
  - `FAILED tests/work/jira/test_jira_set_stage.py::test_a_dropped_note_whose_comments_cannot_be_read_may_have_been_posted`
- Restored; file content matches the original.

#### Task Fix round 2: a dropped move whose comments cannot be read reports the note missing (the old behavior)

- Expected: MovedWithoutNote is raised without `uncertain`
- Tests: tests/work/jira/test_jira_set_stage.py::test_a_dropped_move_whose_comments_cannot_be_read_says_the_note_may_be_there
- Result: **RED** (1 failed in 0.15s)
- Reason check: failure output contains `assert False`
  - `E       AssertionError: assert False`
  - `E        +  where False = MovedWithoutNote('tcw/TCW-1-x moved to plan, but the connection failed (the connection to the tracker at https://acme....annot be read now; the note may have been posted: read the comments with `
  - `E        +    where MovedWithoutNote('tcw/TCW-1-x moved to plan, but the connection failed (the connection to the tracker at https://acme....annot be read now; the note may have been posted: read the comments with `tcw w`
  - `FAILED tests/work/jira/test_jira_set_stage.py::test_a_dropped_move_whose_comments_cannot_be_read_says_the_note_may_be_there`
- Restored; file content matches the original.

#### Task Fix round 2: a dropped move whose comments cannot be read: back to `found = False`

- Expected: the error says the note is not among the newest comments, not that it may have been posted
- Tests: tests/work/jira/test_jira_set_stage.py::test_a_dropped_move_whose_comments_cannot_be_read_says_the_note_may_be_there
- Result: **RED** (1 failed in 0.09s)
- Reason check: failure output contains `assert False`
  - `E       AssertionError: assert False`
  - `E        +  where False = MovedWithoutNote('tcw/TCW-1-x moved to plan, but the connection failed and the note is not among its newest 10 comments').uncertain`
  - `E        +    where MovedWithoutNote('tcw/TCW-1-x moved to plan, but the connection failed and the note is not among its newest 10 comments') = <ExceptionInfo MovedWithoutNote('tcw/TCW-1-x moved to plan, but the connecti`
  - `FAILED tests/work/jira/test_jira_set_stage.py::test_a_dropped_move_whose_comments_cannot_be_read_says_the_note_may_be_there`
- Restored; file content matches the original.

#### Task Fix round 4: T5 single item: drop the Jira-mode parse of capabilities.yaml

- Expected: the single-item check and the viewer save report nothing for a malformed declaration
- Tests: tests/work/jira/test_jira_validate_offline.py::test_one_item_without_its_item_still_reports_a_malformed_declaration, tests/serve/test_files.py::test_a_malformed_declaration_save_is_reported_without_asking_the_backend
- Result: **RED** (1 failed in 0.17s)
- Reason check: failure output contains `assert [] ==`
  - `E       AssertionError: []`
  - `E       assert [] == [('error', '/...or taxonomy')]`
  - `E`
  - `E         Right contains one more item: ('error', '/private/var/folders/wd/f2f6844s5jx4ggzsst835bzc0000gn/T/pytest-of-brian/pytest-296/test_one_item_without_i...k/TCW-1-spec/capabilities.yaml', 'capabilities.yaml: unknow`
  - `E         Use -v to get more diff`
  - `FAILED tests/work/jira/test_jira_validate_offline.py::test_one_item_without_its_item_still_reports_a_malformed_declaration`
- Restored; file content matches the original.

#### Task Fix round 4: T5 single item: parse every folder, not only the target

- Expected: the other item's malformed file is reported too
- Tests: tests/work/jira/test_jira_validate_offline.py::test_one_item_without_its_item_still_reports_a_malformed_declaration
- Result: **RED** (1 failed in 0.16s)
- Reason check: failure output contains `Left contains one more item`
  - `E       AssertionError: [Finding(severity='error', where='/private/var/folders/wd/f2f6844s5jx4ggzsst835bzc0000gn/T/pytest-of-brian/pytest-297/...pec/capabilities.yaml', message='capabilities.yaml: unknown key(s) added; e`
  - `E       assert [('error', '/...or taxonomy')] == [('error', '/...or taxonomy')]`
  - `E`
  - `E         Left contains one more item: ('error', '/private/var/folders/wd/f2f6844s5jx4ggzsst835bzc0000gn/T/pytest-of-brian/pytest-297/test_one_item_without_i...k/TCW-2-spec/capabilities.yaml', 'capabilities.yaml: unknown`
  - `E         Use -v to get more diff`
  - `FAILED tests/work/jira/test_jira_validate_offline.py::test_one_item_without_its_item_still_reports_a_malformed_declaration`
- Restored; file content matches the original.

#### Task Fix round 4: T5 single item, viewer save: drop the Jira-mode parse

- Expected: the viewer's capabilities save carries no warning
- Tests: tests/serve/test_files.py::test_a_malformed_declaration_save_is_reported_without_asking_the_backend
- Result: **RED** (1 failed in 0.85s)
- Reason check: failure output contains `KeyError: 'warnings'`
  - `E       KeyError: 'warnings'`
  - `FAILED tests/serve/test_files.py::test_a_malformed_declaration_save_is_reported_without_asking_the_backend`
- Restored; file content matches the original.

#### Task Fix round 4: T5 rewritten AC 24 test: read the item from Jira when none is given

- Expected: the single-item check asks Jira (offline fails the test)
- Tests: tests/work/jira/test_jira_validate_offline.py::test_one_item_without_its_item_contacts_nothing
- Result: **RED** (1 failed in 0.14s)
- Reason check: failure output contains `plain validate made a request`
  - `E       Failed: plain validate made a request`
  - `FAILED tests/work/jira/test_jira_validate_offline.py::test_one_item_without_its_item_contacts_nothing`
- Restored; file content matches the original.

#### Task Fix round 5: P5: write a list of pairs as a plain block list

- Expected: the block-written ordered map fails to read back (now refused, exit 1)
- Tests: tests/config/test_config_show.py::test_an_ordered_map_and_pairs_read_back_as_themselves
- Result: **RED** (1 failed in 0.14s)
- Reason check: failure output contains `cannot print x-extra.om`
  - `E           AssertionError: Ran(code=1, out='', err='tcw config show: cannot print x-extra.om[0]: written as YAML, it does not read back as the same value`
  - `E             ')`
  - `E           assert 1 == 0`
  - `E            +  where 1 = Ran(code=1, out='', err='tcw config show: cannot print x-extra.om[0]: written as YAML, it does not read back as the same value\n').code`
  - `FAILED tests/config/test_config_show.py::test_an_ordered_map_and_pairs_read_back_as_themselves`
- Restored; file content matches the original.

#### Task Fix round 5: P5: write a list of pairs in flow form as a plain list

- Expected: the ordered map inside a list fails to read back
- Tests: tests/config/test_config_show.py::test_an_ordered_map_and_pairs_read_back_as_themselves
- Result: **RED, but not for the stated reason** (1 failed in 0.24s)
- Reason check: failure output does not contain `cannot print x-extra.inside`
  - `E           AssertionError: Ran(code=1, out='', err='tcw config show: cannot print the configuration: written as YAML, it does not read back as the same value`
  - `E             ')`
  - `E           assert 1 == 0`
  - `E            +  where 1 = Ran(code=1, out='', err='tcw config show: cannot print the configuration: written as YAML, it does not read back as the same value\n').code`
  - `FAILED tests/config/test_config_show.py::test_an_ordered_map_and_pairs_read_back_as_themselves`
- Restored; file content matches the original.

#### Task Fix round 5: P5: drop the read-back check

- Expected: the wrongly written value is printed
- Tests: tests/config/test_config_show.py::test_a_value_that_would_not_read_back_is_refused
- Result: **RED** (1 failed in 0.15s)
- Reason check: failure output contains `DID NOT RAISE`
  - `E           Failed: DID NOT RAISE BackendError`
  - `FAILED tests/config/test_config_show.py::test_a_value_that_would_not_read_back_is_refused`
- Restored; file content matches the original.
- Note on the entry above: the stated reason was too narrow. With the flow form broken, the tuple inside the list is written as text that is not valid YAML at all, so the read-back check reports "cannot print the configuration" rather than naming x-extra.inside. It is the right failure: the value is refused rather than printed wrong.

#### Task Fix round 6: C4: read core.sshCommand with a plain `git config --get` again

- Expected: the current repository's own setting turns BatchMode off
- Tests: tests/test_store_provisioning.py::test_the_current_repositorys_ssh_command_does_not_turn_batch_mode_off, tests/test_store_provisioning.py::test_with_real_git_a_local_ssh_command_is_not_read
- Result: **RED** (1 failed in 0.52s)
- Reason check: failure output contains `KeyError: 'GIT_SSH_COMMAND'`
  - `E       KeyError: 'GIT_SSH_COMMAND'`
  - `FAILED tests/test_store_provisioning.py::test_the_current_repositorys_ssh_command_does_not_turn_batch_mode_off`
- Restored; file content matches the original.

#### Task Fix round 6: C4 (real git only): read core.sshCommand with a plain `git config --get` again

- Expected: real git reads the repository's local core.sshCommand, so BatchMode is not set
- Tests: tests/test_store_provisioning.py::test_with_real_git_a_local_ssh_command_is_not_read
- Result: **RED** (1 failed in 0.14s)
- Reason check: failure output contains `KeyError: 'GIT_SSH_COMMAND'`
  - `E       KeyError: 'GIT_SSH_COMMAND'`
  - `FAILED tests/test_store_provisioning.py::test_with_real_git_a_local_ssh_command_is_not_read`
- Restored; file content matches the original.

#### Task Fix round 6: C4: read only the global scope

- Expected: a system core.sshCommand is not seen and BatchMode replaces it
- Tests: tests/test_store_provisioning.py::test_a_configured_core_ssh_command_is_not_replaced[--system]
- Result: **RED** (1 failed in 0.09s)
- Reason check: failure output contains `assert 'GIT_SSH_COMMAND' not in`
  - `E       AssertionError: assert 'GIT_SSH_COMMAND' not in {...the environment, not copied here...}`
  - `FAILED tests/test_store_provisioning.py::test_a_configured_core_ssh_command_is_not_replaced[--system]`
- Restored; file content matches the original.

#### Task Fix round 7: B1: rounds unfiltered (listing and verdicts read outside rounds)

- Expected: the outside round is listed
- Tests: tests/serve/test_files.py::test_files_linked_outside_are_not_listed_or_judged
- Result: **RED** (1 failed in 0.87s)
- Reason check: failure output contains `rounds`
  - `E       AssertionError: assert [{'path': 're...: 'accepted'}] == []`
  - `E`
  - `E         Left contains one more item: {'path': 'review/round-1.md', 'revision': None, 'number': 1, 'verdict': 'accepted'}`
  - `E         Use -v to get more diff`
  - `FAILED tests/serve/test_files.py::test_files_linked_outside_are_not_listed_or_judged`
- Restored; file content matches the original.

#### Task Fix round 7: B1: a document reached outside counts as present

- Expected: spec.md is present
- Tests: tests/serve/test_files.py::test_files_linked_outside_are_not_listed_or_judged
- Result: **RED** (1 failed in 0.65s)
- Reason check: failure output contains `'present': True`
  - `E       AssertionError: assert {'path': 'spe...resent': True} == {'path': 'spe...esent': False}`
  - `E`
  - `E         Omitting 2 identical items, use -vv to show`
  - `E         Differing items:`
  - `E         {'present': True} != {'present': False}`
  - `E         Use -v to get more diff`
- Restored; file content matches the original.

#### Task Fix round 7: B1: an outside file's revision is shown

- Expected: spec.md has a revision
- Tests: tests/serve/test_files.py::test_files_linked_outside_are_not_listed_or_judged
- Result: **RED** (1 failed in 0.64s)
- Reason check: failure output contains `'revision':`
  - `E       AssertionError: assert {'path': 'spe...esent': False} == {'path': 'spe...esent': False}`
  - `E`
  - `E         Omitting 2 identical items, use -vv to show`
  - `E         Differing items:`
  - `E         {'revision': 'b37e50cedcd3e3f1ff64f4afc0422084ae694253cf399326868e07a35f4a45fb'} != {'revision': None}`
  - `E         Use -v to get more diff`
- Restored; file content matches the original.

#### Task Fix round 7: B1: handoffs unfiltered

- Expected: the outside handoff is listed
- Tests: tests/serve/test_files.py::test_files_linked_outside_are_not_listed_or_judged
- Result: **RED** (1 failed in 0.64s)
- Reason check: failure output contains `handoffs`
  - `E       AssertionError: assert [{'path': 'pl...ision': None}] == []`
  - `E`
  - `E         Left contains one more item: {'path': 'plan/handoff-20261015T120000Z.md', 'revision': None}`
  - `E         Use -v to get more diff`
  - `FAILED tests/serve/test_files.py::test_files_linked_outside_are_not_listed_or_judged`
- Restored; file content matches the original.

#### Task Fix round 7: B1: verdicts judged by the full layout

- Expected: the outside accepted round decides the verdict
- Tests: tests/serve/test_files.py::test_files_linked_outside_are_not_listed_or_judged
- Result: **RED** (1 failed in 0.65s)
- Reason check: failure output contains `'accepted' == 'none'`
  - `E       AssertionError: assert 'accepted' == 'none'`
  - `E`
  - `E         - none`
  - `E         + accepted`
  - `FAILED tests/serve/test_files.py::test_files_linked_outside_are_not_listed_or_judged`
- Restored; file content matches the original.

#### Task Fix round 9: B3: the declaration PUT skips the containment check

- Expected: with the real revision, the write goes through the link (status 200, outside file changed)
- Tests: tests/serve/test_files.py::test_a_declaration_linked_outside_is_not_read_or_written
- Result: **RED** (1 failed in 0.68s)
- Reason check: failure output contains `assert 200 == 404`
  - `E           AssertionError: b'{"revision": "77cebab1f9b6b4bb8cd5f8d83afd1d7d08190f52e5bf8cb6e2f874414243536c"}'`
  - `E           assert 200 == 404`
  - `E            +  where 200 = Response(status=200, headers={'server': 'BaseHTTP/0.6 Python/3.14.6', 'date': 'Fri, 16 Oct 2026 17:44:31 GMT', 'conten...licy': "default-src 'self'"}, body=b'{"revision": "77cebab1f9b6b4bb8cd5`
  - `FAILED tests/serve/test_files.py::test_a_declaration_linked_outside_is_not_read_or_written`
- Restored; file content matches the original.

#### Task Fix round 9: B3 (control): the same bypass, against the test as it was (revision None)

- Expected: survives: write_checked answers 409 first, which is the defect B3 names
- Tests: tests/serve/test_files.py::test_a_declaration_linked_outside_is_not_read_or_written
- Result: **RED** (1 failed in 0.68s)
  - `E           AssertionError: b'{"error": "capabilities.yaml already exists", "code": "stale-revision"}'`
  - `E           assert 409 == 404`
  - `E            +  where 409 = Response(status=409, headers={'server': 'BaseHTTP/0.6 Python/3.14.6', 'date': 'Fri, 16 Oct 2026 17:44:31 GMT', 'conten...curity-policy': "default-src 'self'"}, body=b'{"error": "capabilities.y`
  - `FAILED tests/serve/test_files.py::test_a_declaration_linked_outside_is_not_read_or_written`
- Restored; file content matches the original.
- Note on the control run above: the old test does go red under the bypass, but for the stale revision (409), not because the outside file was written. With the real revision the bypass is red with 200 and the outside file changed, which is what the test claims to observe.

#### Task Fix round 11: token on redirect: add Authorization as an ordinary header again

- Expected: the redirected request to the other host carries the Authorization header
- Tests: tests/work/jira/test_client.py::test_a_redirect_carries_no_credentials
- Result: **RED** (1 failed in 1.07s)
- Reason check: failure output contains `assert 'Authorization' not in`
  - `E       AssertionError: {'Accept-Encoding': 'identity', 'Host': 'localhost:56088', 'User-Agent': 'Python-urllib/3.14', 'Authorization': 'Basic cHJvYmVAZXhhbXBsZS50ZXN0OnNlbnRpbmVsLXRva2VuLXZhbHVl', ...}`
  - `E       assert 'Authorization' not in {'Accept-Encoding': 'identity', 'Host': 'localhost:56088', 'User-Agent': 'Python-urllib/3.14', 'Authorization': 'Basic cHJvYmVAZXhhbXBsZS50ZXN0OnNlbnRpbmVsLXRva2VuLXZhbHVl', ...}`
  - `FAILED tests/work/jira/test_client.py::test_a_redirect_carries_no_credentials`
- Restored; file content matches the original.

#### Task Fix round 12: provision: drop the parse check

- Expected: each broken config reads as declaring nothing: exit 0, Nothing to provision
- Tests: tests/test_store_provisioning.py::test_a_config_that_cannot_be_parsed_is_an_error_not_nothing
- Result: **RED** (1 failed in 0.17s)
- Reason check: failure output contains `assert 0 == 1`
  - `E       AssertionError: assert 0 == 1`
  - `E        +  where 0 = main(['provision'])`
  - `FAILED tests/test_store_provisioning.py::test_a_config_that_cannot_be_parsed_is_an_error_not_nothing[id: corelib\n? [a]\n: 1\n-a mapping key must be a single value]`
- Restored; file content matches the original.

#### Task Fix round 13: work new --project: drop the --stage refusal

- Expected: the item is created in q and --stage is ignored (exit 0)
- Tests: tests/work/test_cli_items.py::test_new_with_project_refuses_stage
- Result: **RED** (1 failed in 0.73s)
- Reason check: failure output contains `code=0`
  - `E       AssertionError: Result(code=0, out='q/2026-10-16-t`
  - `E         ', err='created /private/var/folders/wd/f2f6844s5jx4ggzsst835bzc0000gn/T/pytest-of...ivate/var/folders/wd/f2f6844s5jx4ggzsst835bzc0000gn/T/pytest-of-brian/pytest-340/test_new_with_project_refuses_0/q)`
  - `E         ')`
  - `E       assert 0 == 2`
  - `E        +  where 0 = Result(code=0, out='q/2026-10-16-t\n', err='created /private/var/folders/wd/f2f6844s5jx4ggzsst835bzc0000gn/T/pytest-of...ivate/var/folders/wd/f2f6844s5jx4ggzsst835bzc0000gn/T/pytest-of-brian/pytest-`
  - `FAILED tests/work/test_cli_items.py::test_new_with_project_refuses_stage - As...`
- Restored; file content matches the original.

#### Task Fix round 8: B2: the setup reference says 'never prompts' without the exception again

- Expected: the setup reference fails the wording check
- Tests: tests/test_store_provisioning.py::test_the_documents_name_the_ssh_command_exception
- Result: **RED** (1 failed, 1 passed in 0.08s)
- Reason check: failure output contains `skills/setup/references/project.md`
  - `E       AssertionError: skills/setup/references/project.md`
  - `E       assert ('never asks' not in '# start usi...gure` skill.'`
  - `E`
  - `E         'never asks' is contained here:`
  - `E           ure` skill. and 'never prompts' not in '# start usi...gure` skill.'`
  - `E`
- Restored; file content matches the original.

#### Task Fix round 10: B4: point at the procedure for the request rule again

- Expected: the body no longer states the rule
- Tests: tests/test_unattended_work_skill.py::test_the_request_rule_is_in_the_body_itself
- Result: **RED** (1 failed in 0.40s)
- Reason check: failure output contains `the procedure below says how`
  - `E       assert 'the procedu...low says how' not in "**version c...item's slug."`
  - `E`
  - `E         'the procedure below says how' is contained here:`
  - `E         ?           ^^^^^^^^^^^^^`
  - `E            know, so the procedure below says how to write the request without them. stop only on a hard blocker. **ask once, at the start:** confirm the item set (the user's list, or pick from `tcw work list`) and the `
  - `E`
- Restored; file content matches the original.

### Final fixes

Each mutation was applied with a script that replaces one exact line, runs the
named tests, and writes the original file back; `git diff --stat` was empty
for the source file afterwards each time.

#### Final 1a: C4, count only the global and system scopes again (tcw/store/fs.py `_no_prompt_env`)

- Mutation: `f[0] not in ("local", "worktree")` -> `f[0] in ("global", "system")`
- Tests: tests/test_store_provisioning.py -k "ssh or prompt or real_git"
- Result: **RED** (2 failed, 12 passed)
  - `test_a_configured_core_ssh_command_is_not_replaced[command]`: `assert 'GIT_SSH_COMMAND' not in {...}`
  - `test_with_real_git_a_command_line_ssh_command_is_kept` (real git, GIT_CONFIG_COUNT/KEY_0/VALUE_0): `assert 'GIT_SSH_COMMAND' not in fs._no_prompt_env()`
- Reason check: the command-scope value was ignored and BatchMode was set, which is the regression.
- Restored.

#### Final 1b: C4, count the current repository's own setting too

- Mutation: drop the `f[0] not in ("local", "worktree")` condition
- Result: **RED** (3 failed): `test_the_current_repositorys_ssh_command_does_not_turn_batch_mode_off[local]`, `[worktree]`, and the real-git `test_with_real_git_a_local_ssh_command_is_not_read` (BatchMode no longer added).
- Restored.

#### Final 2: the four documents without the scope wording

- Mutation: `git stash` of the four document edits (multi-repo.md, setup/references/project.md, provision-declared-stores/description.md, release notes)
- Tests: tests/test_store_provisioning.py -k documents_name
- Result: **RED** (4 failed): each names its file; `assert 'git command line' in ...` (three) and `assert 'global or system git config' in ...` (skills/setup/references/project.md).
- Restored with `git stash pop`.

#### Final 3: changelog and release notes without the request rule and the viewer rewording

- Mutation: `git stash` of the two entry-file edits
- Tests: tests/test_unattended_work_skill.py
- Result: **RED** (3 failed): `test_the_request_rule_is_announced[changelogs]`, `[release-notes]` (`AssertionError: <folder>`, from `"unattended-work" in text`), and `test_the_release_notes_say_what_the_viewer_shows_for_a_link_outside_the_item`.
- Restored with `git stash pop`.

#### Final 4: T5, skip the declaration parse when the item is given and terminal (tcw/validate.py)

- Mutation: `elif isinstance(backend, JiraBackend):` -> `elif False:`
- Tests: tests/work/jira/test_jira_validate_offline.py tests/test_validate_target.py
- Result: **RED** (1 failed, 33 passed): `test_one_finished_item_given_its_item_still_reports_a_malformed_declaration`: `assert [] == [('error', '.../TCW-1-done/capabilities.yaml', 'capabilities.yaml: must be a mapping of new, changed, removed and taxonomy')]`
- Reason check: no finding at all, which is the bug (the `offline` fixture also fails any Jira request, so the fixed path makes none).
- Restored.

#### Final 5a: Jira 401 after a redirect, no redirect check (tcw/work/jira/client.py)

- Mutation: `if error.code == 401 and landed and landed != request.full_url:` -> `if False:`
- Tests: tests/work/jira/test_client.py (two localhost servers: the site answers 301 to the other, which answers 401)
- Result: **RED** (1 failed): `test_a_401_after_a_redirect_names_the_redirect[True]`: got `the tracker rejected the credentials (/rest/api/3/myself). Check the values of the variables named in work.jira.credentials.`
- Restored.

#### Final 5b: treat every 401 as a redirect

- Mutation: drop `and landed != request.full_url`
- Result: **RED** (1 failed): `test_a_401_after_a_redirect_names_the_redirect[False]` (a 401 from the site itself must still name the credentials).
- Restored.

#### Final 6: the codec error passes through unnamed (tcw/store/fs.py `read_yaml_text`)

- Mutation: `raise NotUtf8(path, error) from None` -> `raise`
- Tests: tests/test_store_provisioning.py -k utf_8
- Result: **RED** (2 failed): `[command0]` `tcw provision: 'utf-8' codec can't decode byte 0xe9 in position 17: invalid continuation byte`; `[command1]` the same for `tcw init`.
- Restored.

#### Final 7: the old "always starts in its inbox" wording (tcw/work/cli.py)

- Mutation: the last line of the refusal back to `"project always starts in its inbox")`
- Tests: tests/work/test_cli_items.py -k refuses_stage
- Result: **RED** (1 failed): `test_new_with_project_refuses_stage`: `AssertionError: tcw work new: --stage cannot be used with --project; only --priority can. An item created in another project always starts in its inbox`
- Restored.

#### Final 2, re-checked after the skill rewording

The standing guard `tests/test_shipped_text.py::test_no_shipped_text_names_git`
went red on the first wording of skills/setup/references/project.md ("git
configuration ... git command line"); the skill now says "global or system
configuration or given on the command line" (commit ac1b6ec5), and the
document test accepts "given on the git command line" or "given on the command
line" and requires "global or system".

- Mutation: the four documents checked out from aa6f94c5 (before fix 2), then restored from copies
- Tests: tests/test_store_provisioning.py -k documents_name
- Result: **RED** (4 failed), one `AssertionError` per document naming it.
- Restored; `git status` showed only the intended changes.

### Task 9

Each mutation was made with sed on the work branch and restored with
`git checkout -- tests/work/jira/fake.py` (or from a copy, for capture.py);
`git diff` was clean afterwards. Tests: tests/work/jira/test_recorded_shapes.py.

#### 9.1: the fake's search answer has no nextPageToken (fake.py `_search`)

- Mutation: `answer["nextPageToken"] = str(start + size)` -> `pass`
- Result: **RED** (3 failed): `test_the_fake_answers_in_jiras_shape[post-search-jql-200-first-page.json]` (`Jira sends ['nextPageToken'], which the fake's answer lacks`); `[...-next-page.json]` (`KeyError: 'nextPageToken'` building the next-page request); `test_the_client_asks_as_jira_was_asked[...-next-page.json]` (`the fake answered every ticket in one page`).
- Restored.

#### 9.2: the fake's search answer has no isLast (fake.py `_search`)

- Mutation: `"isLast"` removed from the answer; the token still added when more remain
- Result: **RED** (4 failed): `[post-search-jql-200-first-page.json]`, `[...-next-page.json]` and `[post-search-jql-200.json]` (`Jira sends ['isLast'], which the fake's answer lacks`); `test_the_client_asks_as_jira_was_asked` (`the fake answered every ticket in one page`: the client stops when isLast is absent, as Design 18 says).
- Restored.

#### 9.3: the fake's restricted transition has `links: []` (fake.py `_workflows`)

- Mutation: `"links": [] if t.sources is None else [...]` -> `"links": [] if True else [...]`
- Result: **RED** (1 failed): `[post-workflows-200-directed.json]`: `Jira sends ['workflows.*.transitions.*.links.*.fromStatusReference'], which the fake's answer lacks`.
- Restored.

#### 9.4: the fake's screen field map is empty (fake.py `_transitions`)

- Mutation: `for f, required in transition.screen.items()` -> `for f, required in {}.items()`
- Result: **RED** (1 failed): `[get-issue-key-transitions-200-screen-fields.json]`: `Jira sends ['transitions.*.fields.?.required'], which the fake's answer lacks`.
- Restored.

#### 9.5: no named-file option (capture.py `Recorder.named`)

- Mutation: `self.label = label` -> `self.label = None`, so a named call merges into the shared file
- Tests: tests/work/jira/test_recorded_shapes.py -k named
- Result: **RED** (1 failed): `test_a_named_call_is_recorded_apart_from_the_shared_file`: `FileNotFoundError: ... post-search-jql-200-first-page.json`.
- Restored.

#### Step 4

No difference between the recordings and what client.py and remote.py read,
so no fix and no fix mutation.
