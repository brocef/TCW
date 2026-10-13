# Outcome — TCW-72: personal configuration, user identity and per-user overrides

Implemented on `work/2026-10-01-tcw-72-personal-configuration-user-identity-and-per-user-overrides`,
made from `epic/tcw-3.0` at `4cf97fd3`, one commit per plan task, `f5c64295`
to `39cdea8e`. Task 8 (mutation checks) found no gap, so it has no commit.
The spec's implement-finding notes (`a1a54d77`), `capabilities.yaml`
(`50ea374e`) and this file are on main.

Tests were run per task against the changed areas, never as a full suite, in a
private virtual environment pointed at the worktree, with the worktree as the
current folder. The final run covered `tests/config/`, `tests/work/`, the four
standing files (`test_cli_contract.py`, `test_cli_help_standard.py`,
`test_static_guards.py`, `test_cli_handler.py`) and every other file this item
touched: 2205 passed, 28 skipped. `pytest --collect-only -q` on the branch
collects 3823 tests with no error. No test reads or writes the real home
folder: an autouse fixture sets `TCW_NO_PERSONAL_CONFIG=1` and points
`XDG_CONFIG_HOME` into each test's temporary folder, and the personal-layer
tests also point `HOME` there.

## What was built

| Task | Commit | What |
| --- | --- | --- |
| 1 | `f5c64295` | The test isolation fixture; `ConfigError(BackendError)`, exit 1, carrying its problems; the duplicate-key YAML loader in one place (`tcw/store/yaml_source.py`). |
| 2 | `ed6ce2c1` | `tcw/config.py`: the four layers, the `inherit` chain, the allowlist (`PERSONAL_KEYS`), origins for every value and list entry, problems mapped back to the file that caused them, `file:` confinement checked at load. List indexes in key paths are integers, printed `prompt[2]`. |
| 3 | `1abe809a` | Every command checks the merged configuration before it runs (`tcw.cli._dispatch`; `init`, `provision`, `validate` and `config show` opt out) and keeps it for the command (`effective`). `open_backend` builds from it; another project is opened with `personal=False`. TCW's own text comes only from built-in entries: the fallbacks in `resolve.py` and `tcw work lifecycle` are gone. |
| 4 | `6e9fbac0` | A `file:` is read from its declaring file's folder; `TCW_CONFIG_DIR` for every command and `generate` binding; `HookFailure` and `Outcome.post_failures`, so a failed `post` hook names its file; the `note:` line when personal files changed a composed list. |
| 5 | `42916cb5` | `tcw work list --mine`, `--assign-me` on `new` and `edit`, through `current_user()`; one message naming every remedy when no identity is set; the last `TCW_WORK_OWNER` mention removed. |
| 6 | `6b742739` | `tcw validate` reports every layer's problems as findings and warns when `tcw-config.local.yaml` is tracked; `tcw init` writes `/tcw-config.local.yaml` to `.gitignore`, or prints the `note:` line outside a repository. |
| 7 | `a608a605` | `tcw config show [--origin]` (`tcw/config_cli.py`), 43 leaf commands. |
| 9 | `4e2daede` | Taxonomy terms `config-layer`, `user-identity`, `personal-configuration`; three new capability records and six changed ones. |
| 10 | `39cdea8e` | Release-notes and changelog entries. |

## Acceptance criteria

| AC | Evidence |
| --- | --- |
| 1 Finding the layers | `tests/config/test_personal_layers.py` |
| 2 Skipping personal layers | `test_personal_layers.py` |
| 3 Mappings merge | `tests/config/test_personal_merge.py` |
| 4 The chain | `test_personal_merge.py` (the `CHAIN` table, origins per entry, `when:` kept) |
| 5 `inherit` and `builtin` errors | `test_personal_merge.py` |
| 6 The allowlist | `tests/config/test_personal_allowlist.py::test_a_shared_key_in_a_personal_file_is_one_problem` (17 keys, including `projects.x.path` and `projects.x.jira.credentials.email-env`) |
| 7 `user` is personal | `test_personal_allowlist.py` |
| 8 Every command refuses | `tests/config/test_personal_commands.py` (work list, stage prompt, taxonomy, capabilities, projects, lifecycle, `--version`); `test_config_show.py::test_a_refused_key_stops_plain_show`; `test_personal_validate_init.py::test_validate_names_a_shared_key_in_the_local_file` |
| 9 Other projects ignore personal layers | `test_personal_commands.py` (delegation, `current_user()` per project, graph readers with a broken local file); `test_personal_identity.py::test_assign_me_with_another_project_is_a_usage_error`; `test_personal_validate_init.py::test_validate_in_the_parent_ignores_the_childs_local_file` |
| 10 Paths and commands | `tests/config/test_personal_origins.py`, `tests/config/test_personal_problems.py` |
| 11 Origins | `test_personal_origins.py`; the packaged-text cases in `test_personal_commands.py` |
| 12 `config show` | `tests/config/test_config_show.py`; `test_cli_contract.py::test_config_show_in_a_project` |
| 13 Identity | `tests/config/test_personal_identity.py` (filesystem, no identity with `TCW_WORK_OWNER` and a git identity set, a recording backend over the in-memory one); `test_cli_contract.py::test_the_identity_flags_in_a_project` and `::test_jira_identity_flags` (the real `JiraBackend` against the fake) |
| 14 No fallback left | `test_personal_identity.py` (no `TCW_WORK_OWNER` under `tcw/`; no read of the version-control identity, with a test that the pattern sees one) |
| 15 Allowlist importable | `test_personal_allowlist.py::test_the_allowlist_is_importable_and_exact` |
| 16 Writers | `test_personal_validate_init.py::test_tags_add_leaves_the_personal_files_alone` |
| 17 `init` and `validate` | `test_personal_validate_init.py` |
| 18 Secrets | `test_personal_allowlist.py::test_a_credential_name_that_is_not_a_name_is_reported_without_its_value` |
| 19 Test isolation | `tests/config/test_personal_isolation.py` |
| 20 Nothing else changes | The full suite was not run, by the epic's instruction. TCW-70's `init` test already asserted only the status-folder rule; its contract test already expects `current_user()` to return `None`; its `stage prompt` fixtures now write `inherit: true`. |
| 21 `open_backend` uses the loader | `test_personal_commands.py` (`ConfigError`, the skip variable, `current_user() == "Brian"`) |

## Verification by hand

In a scratch folder with the branch's code, `XDG_CONFIG_HOME` and `HOME` in
the scratch folder: `tcw init --id walk` in a fresh git repository named
`.gitignore` on stderr, and the file held `/tcw-config.local.yaml`; outside a
repository the `note:` line printed instead. With a local file holding
`user: {name: Walker}` and a spec `prompt` list `[{blob: mine}, {inherit:
true}]`: `tcw config show` printed `- blob: mine` above `- builtin: true  #
tcw/work/prompts/spec.md`; `--origin` marked the entry `# local:
tcw-config.local.yaml`; `tcw work stage prompt spec` printed `mine` above the
packaged text, with the note on stderr; `tcw work new x --assign-me` then
`tcw work list --mine` printed `walk/2026-10-13-x`. Adding `id: other`:
`tcw work list` exited 1 with `tcw work list: tcw-config.local.yaml: id: a
shared key; a personal file cannot set it`; `tcw config show --origin` exited
1, printed `id: walk  # project` and `# refused: id: other (shared key,
tcw-config.local.yaml)`. `tcw --help` lists `config`, and `tcw config show
--help` reads plainly with its `Prints:` and `Writes:` lines.

## Mutation checks

Each guard below was broken on purpose; the named tests went red, and the
code was restored (checked with `git diff` afterwards).

- The isolation fixture without its `setenv`: `test_personal_isolation.py` red.
- The allowlist walk accepting every key: 25 tests red.
- `inherit` resolved as "replace": 6 red (the chain table).
- Credential names never skipped outside Jira mode: 1 red.
- Every problem blamed on `tcw-config.yaml`: 4 red.
- No `file:` confinement at load: 2 red.
- A refused key merged anyway: 6 red, including `config show`'s parse-back.
- The per-command check removed from `_dispatch`: the taxonomy,
  capabilities and projects cases of AC 8 red.
- `open_project` built with personal layers: AC 9's `current_user() is None`
  red.
- The built-in fallback put back in `resolve.py`: AC 11's `[]` case red.
- `TCW_CONFIG_DIR` and the file root always the project root: 3 red.
- A failed `post` hook not naming its file: 2 red.
- The personal note never printed: 3 red.
- `--mine` ignored: 6 red. `--mine` or `--assign-me` allowed with
  `--assignee`: 3 red. `--assign-me` allowed with `--project`: 1 red.
  `current_user()`'s `None` turned into an empty assignee: 3 red.
- The tracked check always false: 1 red; always true: 1 red; the ignore rule
  checking only the spelling with `/`: 1 red; `validate` without the
  configuration findings: 2 red.
- `config show` without quoting: 15 red; without the set-aside block: 2 red;
  plain `show` printing despite problems: 1 red; a `-env` value printed: 1 red.
- The Jira credential message echoing the value: AC 18 red.

## 2.x tests deleted or rewritten

None deleted. Rewritten, keeping what they test:

- `tests/work/test_compose.py`: the three tests that relied on the built-in
  fallback (`test_no_prompt_key_is_the_packaged_text`,
  `test_a_missing_packaged_prompt_names_the_file`,
  `test_a_procedure_composes_the_same_way`) now read the configuration
  through the loader; a new test asserts that without the loader an absent
  list composes to nothing.
- `tests/work/test_cli_config.py::test_builtin_then_a_file` →
  `test_inherit_then_a_file`, and `tests/test_procedure_verb.py`'s
  composition test: `inherit: true` in place of `builtin: true`.
- `tests/test_config_edit_writers.py`: its annotated fixture held 2.x
  `work.lifecycle` and `work.tracker` blocks; every command now reads the work
  configuration, so it holds a 3.0 `work.stages` block and `work.tags` instead,
  still with comments and odd formatting for the writers to keep.
- `tests/test_no_node.py`: the kept-function list names
  `store/yaml_source.py::_no_dup_keys` in place of the two copies removed.
- `tests/test_smoke.py::test_init_without_work_writes_no_gitignore` →
  `test_init_without_work_writes_no_work_ignore_rule`: the only line is the
  personal file's.
- `tests/test_init_provision_contract.py::test_init_prints_nothing_and_names_every_path`:
  outside a repository it now expects the `note:` line, on both runs.
- `tests/work/test_validate_work.py::test_a_config_error_is_one_finding`:
  the finding now comes from `config_findings`, and the work checks report
  nothing for it.
- `tests/test_cli_contract.py`: three identity rows and a `config show` row
  in `ROWS`; the outside-a-project test drops `--flag` words when it builds
  the expected error prefix.
- `tests/test_cli_help_standard.py`: `SURFACE` gains `config show` (43).
- `tests/test_static_guards.py`: `EXEMPT` gains
  `store/fs.py::personal_file_tracked`, the read-only status check.

## Where the work differs from the plan

1. **A refused mapping is reported once per value under it**, by its whole
   key path (`projects.x.path`), not once for the mapping's first key (spec
   note added).
2. **`validate`'s configuration findings come from the library function
   `validate()`**, not only from the command, so every caller gets them; the
   plan put them in the command alone. The work checks no longer repeat a
   configuration problem (spec note added).
3. **The `init` notice is printed on every run outside a repository**,
   including a run with nothing else to do (spec note added, with the
   TCW-73-wins wording the plan already chose).
4. **The identity rows in `ROWS` carry their flag in the key**
   (`work list --mine`), since the contract test keys rows by name and a
   flag is not a leaf command.
5. **`edit --assign-me` asks the item's own backend for the identity after
   `_own`**, so editing another project's item is still refused with exit 3
   rather than reported as a missing identity.
6. **`work/configure-procedures` lost its `Planning doc` line**, since this
   item changed the record and records carry neither retired field.

## Records gate

`records_problems(..., finished=True)` over this item's `capabilities.yaml`,
against a copy of the branch's ledger and taxonomy, reports no problem.
Declaring a record that does not exist (`cli/no-such-thing`) makes it report
one.

## Found and not fixed here

- **This repository's own `tcw-config.yaml` is still in the 2.x shape.**
  `tcw validate` with the branch's code reports its `work.lifecycle`,
  `work.tracker` and `work.retain` keys, as it did before, and now also the
  `builtin: true` entries under `work.lifecycle` and `work.procedures`.
  Because every command now checks the whole configuration first, the
  taxonomy and capabilities commands also stop on these in this repository
  when run with the branch's code. Migrating the repository's own
  configuration is not this item's.
- **`tests/test_tree_store_raises.py` fails two tests on `epic/tcw-3.0`
  itself** (`4cf97fd3`, checked against an unpacked copy): a `raise TcwError`
  in `fs.py`'s partial-removal message predates this item.

## Documentation

| Entry | Handled |
| --- | --- |
| `README.md` | Deferred to TCW-75. |
| `docs/guide/jira.md` | Deferred to TCW-75 (credential names may now come from a personal file). |
| `docs/guide/<topic>.md` | Deferred to TCW-75. |
| Release notes (upcoming) | Written (Task 10). |
| Changelog (upcoming) | Written (Task 10). |
| `skills/<component>/SKILL.md` | Deferred to TCW-74 (the `work` skill names `builtin: true` and the old identity). |
| `skills/configure/references/` | Deferred to TCW-75, which writes `personal.md` and the shared/overridable table against `PERSONAL_KEYS`. |

## For later children

- **TCW-74:** every skill but `configure` that names `builtin: true`,
  `TCW_WORK_OWNER` or `--owner`.
- **TCW-75:** `README.md`, the guides (`jira.md` included), `personal.md`, the
  table and its test against `PERSONAL_KEYS` written from scratch, the router
  line, and a note that a linked worktree has no local file.
- **TCW-76:** the migration guide maps `TCW_WORK_OWNER` and the git identity
  to `user.name`, `builtin: true` to `inherit: true` (a list without it
  replaces the packaged text), lists `TCW_CONFIG_DIR`, and tells existing
  projects to add `/tcw-config.local.yaml` to `.gitignore`.
- **TCW-77:** the viewer's project `user` field can come from
  `current_user()` in both modes.
- **Originating issue:** none; TCW-72 came from Jira, not GitHub.

## Review fixes (2026-10-13)

An adversarial review found fourteen problems. All were fixed on the branch in
three commits: `12a7c1c7` (loader), `7c3bccd2` (commands) and `f8ec7f45`
(records). Every fix began with a test that failed for the reason the review
gave.

| Finding | Commit | Test |
| --- | --- | --- |
| L1: delegating into an on-disk Jira-mode project read the person's own files into the target | `12a7c1c7` | `tests/work/jira/test_jira_delegation.py::test_the_targets_local_file_is_not_read`, `::test_a_user_wide_token_name_does_not_reach_the_target` |
| L2: a mapping no lower layer holds kept a literal `inherit` entry | `12a7c1c7` | `tests/config/test_personal_merge.py::test_a_new_stage_mapping_resolves_its_chain_lists` (completed, discarded), `::test_a_local_stage_mapping_resolves_when_the_project_sets_nothing` |
| L3: an empty mapping had no origin; Design 5.2's third rule was untested | `12a7c1c7` | `test_personal_merge.py::test_an_empty_mapping_is_blamed_on_the_file_that_wrote_it`, `::test_a_mapping_problem_is_blamed_on_the_highest_layer_under_it` |
| L4: a file that is not UTF-8 raised out of `load_config` | `12a7c1c7` | `tests/config/test_personal_problems.py::test_a_local_file_that_is_not_utf8_is_a_problem_naming_it`, `::test_a_project_file_that_is_not_utf8_is_unreadable`, `::test_config_show_origin_names_a_file_that_is_not_utf8` |
| L5: `tcw serve` kept the once-per-command configuration for its whole life | `12a7c1c7` | `tests/test_serve.py::test_the_resolver_sees_a_configuration_change_while_serving` |
| L6: lines 2 and later of several problems had no `tcw <words>: ` prefix | `12a7c1c7` | `test_personal_problems.py::test_every_problem_is_its_own_prefixed_line` |
| C1: `config show` could print a token pasted into a `-env` key | `7c3bccd2` | `tests/config/test_config_show.py::test_a_pasted_token_is_never_printed` (project, local), `::test_a_variable_name_is_printed_as_itself`, `::test_a_refused_token_is_never_printed` |
| C2: a blob of `...` made `config show` fail with a parser error | `7c3bccd2` | `test_config_show.py::test_config_show_prints_a_blob_of_three_dots`, `::test_a_hostile_string_reads_back_as_itself[...]` |
| C3: emoji written as surrogate pairs; `.inf` and dates lost their type | `7c3bccd2` | `test_config_show.py::test_a_hostile_string_reads_back_as_itself` (47 strings), `::test_values_of_unknown_keys_keep_their_type` |
| C4: a broken `tcw-config.yaml` gave two `validate` errors | `7c3bccd2` | `tests/config/test_personal_validate_init.py::test_a_broken_project_file_is_one_validate_error` (duplicate key, bad YAML, a list, not UTF-8) |
| C5: `--mine` said "no identity" when Jira was the problem | `7c3bccd2` | `tests/work/jira/test_jira_read.py::test_current_user_raises_when_jira_cannot_say`, `::test_mine_says_jira_was_the_problem` |
| C6: false "tracked" warning under `status.showUntrackedFiles=no` | `7c3bccd2` | `test_personal_validate_init.py::test_validate_ignores_the_setting_that_hides_untracked_files` |
| C7: records out of step with the fixes | `f8ec7f45` | records; `tests/test_ledger_3_0.py` and `tests/test_capability_ref_wording.py` pass |
| C8: `edit <missing> --assign-me` exited 1, not 4; `new --project` usage errors waited for piped input | `7c3bccd2` | `tests/config/test_personal_identity.py::test_edit_of_a_missing_item_says_it_is_missing_before_who`, `::test_a_project_usage_error_does_not_wait_for_piped_input` |

**Narrowed.** C4: the second error came from the project graph's check
(`tcw/store/project.py`), not from the file scan. `config_findings` now leaves
out its own copy when `tcw-config.yaml` cannot be read, so the line from before
TCW-72 is kept. That check also now names a file that is not UTF-8 instead of
failing. C6: the suggested command, `--untracked-files=all` without
`--ignored`, prints nothing for an ignored file and would call it tracked,
which is the usual case after `tcw init`. The command keeps `--ignored`. A
mutation that dropped it turned both tracked-file tests red.

**Left as noted.** C3: a `!!binary` value from an unknown key would be written
over several lines. Nothing TCW reads takes one, so it was not fixed.

**Mutation checks** (each broke the guard, went red for the reason given, and
was put back):
- L1, L2, L4, L5, L6, C4, C5, C6, C8: the new tests failed against the
  unfixed code, each with the fault the review described.
- L3: with the origin of an empty mapping not recorded,
  `test_an_empty_mapping_is_blamed_on_the_file_that_wrote_it` failed. With
  `_origin_for`'s third rule changed to "lowest layer",
  `test_a_mapping_problem_is_blamed_on_the_highest_layer_under_it` failed.
- C1: without the mask on the configuration, both pasted-token tests failed.
  Without the mask on set-aside values, the refused-token test failed.
- C2: with the YAML error no longer caught, the `...` cases failed. C3: with
  quoting by `json.dumps` again, the emoji cases failed.
- C4: with the filter turned off, all four broken-file cases failed.
- C5: with Jira errors swallowed, the raise tests failed.
- C6: with `--ignored` dropped, both tracked-file tests failed.

One mutation run reused a stale `.pyc` (the `min`/`max` swap kept the file
size and the restore landed in the same second). Clearing the cache confirmed
the restored code passes. Later mutation runs used `PYTHONDONTWRITEBYTECODE=1`.

**Decisions taken in review.**
- C1: `config show` prints `(value not shown)` for a value under a key ending
  in `-env` that is not shaped like a variable's name, in the configuration
  and in the set-aside block. That is the one place its output does not read
  back as the effective configuration (spec Design 8.4).
- C5: `JiraBackend.current_user()` returns None only when a credential
  variable is unset. Otherwise it raises `Unreachable` (exit 5) or
  `BackendError` (exit 1) with Jira's reason. TCW-71's
  `test_current_user_never_raises` was replaced (spec Design 9.2 note).
- C6: the tracked check runs `git --no-optional-locks status --porcelain
  --ignored --untracked-files=all -- tcw-config.local.yaml` (spec Design 10.3
  note).

The spec notes are in `a1b028d6` on `main`, along with `capabilities.yaml`
adding `work/open-a-work-item` and `work/view-the-board` to `changed`.

**Tests run** (worktree, private venv): the standing guard files,
`tests/config/`, `tests/work/` (with `tests/work/jira/`), `tests/test_serve.py`,
`tests/test_refs.py`, `tests/test_validate*.py` and `tests/test_project*.py`
gave 2361 passed and 17 skipped. The capability, wording and init tests gave
94 passed and 9 skipped. `pytest --collect-only` collected 3899 tests with no
errors.

**Out of scope, as directed:** the unhashable-key `TypeError` in
`UniqueKeyLoader` and `yaml_source._no_dup_keys`, which predates this change.
