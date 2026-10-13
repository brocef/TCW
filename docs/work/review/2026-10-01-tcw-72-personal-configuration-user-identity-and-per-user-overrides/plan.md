# Plan — Personal configuration: user identity and per-user overrides

This plan follows the spec as reviewed on 2026-10-02. Each task is one commit
on `work/2026-10-01-tcw-72-personal-configuration-user-identity-and-per-user-overrides`,
made from `epic/tcw-3.0` at `4cf97fd3`, and the tests the task names pass
after it. The order puts the loader in first with its own tests and nothing
using it (Tasks 1–2), then switches every command onto it in one isolated
step (Task 3), then builds on the origins it records (Tasks 4–8), and ends
with the records and the release entries (Tasks 9–10).

## Before the first task

**What TCW-69, TCW-70, TCW-71 and TCW-73 left, read on the branch at
`4cf97fd3`.**

- `tcw/work/config.py`: `parse_work_config(mapping, origins)` reads the
  `work:` section, never raises, returns `ConfigProblem(key_path, message)`
  values, and gives every binding of a list one `origin` label taken from
  `origins[<list's key path>]`. A list index in a key path is a string
  (`("work","stages","spec","prompt","0")`), and `ConfigProblem.__str__`
  joins the parts with dots. `builtin: true` is accepted; duplicates and
  empty lists are allowed (so TCW-69's "an empty list is not an opt-out" is
  already gone).
- `tcw/work/open.py`: `read_work_config` and `open_backend` read
  `tcw-config.yaml` alone through `tcw.store.fs.load_config(path)` (the
  refusing, duplicate-key reader of one file) and raise `BackendError` for
  problems. `open_project` calls `open_backend` for the other project, so
  without a change it would apply the person's layers there too.
  `FsWorkBackend` already takes `user_name` and `current_user()` returns it
  (or `None`); `JiraBackend.current_user()` already returns `None` with its
  variables unset (TCW-71 aligned with R3).
- `tcw/work/resolve.py:367-386` and `tcw/work/cli.py:456-464` still add the
  packaged text when a `prompt` or procedure list is absent (the fallback
  Design 3.5 removes). An empty list already composes to nothing.
- `tcw/cli.py:_dispatch` already runs one check for every command before it
  runs (`refuse_retired_config`, TCW-73 Design 9.3), skipping `validate`.
- `tcw/work/advance.py`'s `Outcome` has `code`, `stage`, `messages`,
  `overridden`; `run_bindings` (`tcw/work/hooks.py`) returns the first
  failure as a string; `tcw/work/jira/tickets.py:224` uses `run_post` too.
- `tcw/work/cli.py` has `--assignee` on `new`, `edit` and `list`, and no
  `--mine` or `--assign-me`. No `tcw config` group exists. `TCW_WORK_OWNER`
  survives only in the docstring at `tcw/store/project.py:71`; no module
  reads git's `user.name` or `user.email`.
- `tcw init` writes no `.gitignore` line at all (TCW-70 removed the
  status-folder rules); `tests/test_smoke.py::test_init_without_work_writes_no_gitignore`
  and `tests/work/test_init_provision.py` hold that.
- The duplicate-key YAML loader exists twice: `tcw/store/fs.py:692-710`
  (`_UniqueKeyLoader`) and `tcw/store/project.py:28-43`.
- `tests/test_static_guards.py` refuses a git word in any string in `tcw/`
  outside named functions; `tests/test_cli_contract.py` refuses a stderr line
  shaped `tcw <command>: …` on success.

**Which source runs.** A private virtual environment at
`<scratch>/tcw72/venv` (`python -m venv --system-site-packages`, then
`pip install -e <worktree> --no-deps`); pytest and the CLI run with the
worktree as the current folder and the venv first on `PATH`. The CLI is tried
by hand only from a scratch folder. The board on `main` is driven by the
released 2.8.1 `tcw`, never by the worktree's code.

**Tests, per the owner's rule for this epic.** The full suite is not run. Each
task runs the test files it names, the files under `tests/` that reach the
code it touched (found with `grep -rl` for the names it changes), and always
`tests/test_cli_contract.py`, `tests/test_cli_help_standard.py`,
`tests/test_static_guards.py` and `tests/test_cli_handler.py`. A 2.x test that
breaks because 2.x behavior is removed may be skipped or deleted; each one is
listed in `outcome.md`. The last task ends with `pytest --collect-only -q`
clean.

**Personal files in tests.** No test may read or write the real home folder.
Task 1's autouse fixture sets `TCW_NO_PERSONAL_CONFIG=1` and points
`XDG_CONFIG_HOME` into the test's temporary folder for every test; a test of
the personal layers removes the first and, where it needs the home-folder
path, points `HOME` into its temporary folder too.

## Where the spec predates TCW-73, and TCW-73 wins

1. **"node" is "project"**: `cli/validate-a-node` is now
   `cli/validate-a-project`, and the spec's "node" wording is read as
   "project" throughout.
2. **`connected-projects` is `projects`** (TCW-73 Design 9.3). The allowlist
   names no path under it either way; criterion 6's `connected-projects.x.path`
   case is tested as `projects.x.path` and
   `projects.x.jira.credentials.email-env`.
3. **The `init` notice outside a repository.** Design 10.2 fixes it as
   `tcw init: not inside a repository, …`. TCW-73 Design 1.3 says a stderr line
   on success never starts with the command's words, because that shape marks
   an error, and its contract test refuses it (`ERROR_SHAPE`). The notice is
   printed as `note: not inside a repository, so no ignore rule was written;
   keep tcw-config.local.yaml out of version control yourself`. A spec note is
   added at implementation.
4. **`tcw work procedure` outside a project** reads TCW's own text and loads
   no configuration (TCW-73 plan choice 3); the per-command check (Task 3)
   runs only inside a project.
5. **Validate's finding form** is TCW-73's `Finding` and `_located`: `where` is
   the file relative to the project when it is inside it, otherwise absolute.

## Choices this plan makes

1. **The loader is `tcw/config.py`; its `load_config(project_root, *,
   personal=True)` is a new function beside the existing
   `tcw.store.fs.load_config(path)`.** The older one stays as "read one
   `tcw-config.yaml`, refusing" for the readers named in choice 2, now
   implemented by `read_project_file`. Renaming its forty call sites would
   change nothing a user sees.
2. **Readers of shared keys keep reading the tracked file.** Design 2.2 asks
   every reader of a project's whole configuration to go through
   `load_config`. On this branch the readers that remain outside the work
   backend (store location, `extends`, the project registry, `provision`,
   `validate`'s store checks) read only keys the allowlist makes shared, which
   no personal layer can set, so reading the tracked file gives them exactly
   the effective value. What makes "one loader" true for a person is that
   (a) every command except `init`, `provision`, `validate` and
   `config show --origin` runs `load_config` once before anything else and
   stops on its problems (choice 4), and (b) everything a personal layer can
   change (prompts, `post` hooks, procedures, credential names, `user.name`)
   is read only through `open_backend`, which uses `load_config`. The YAML
   read itself exists once: the duplicate-key loader moves to
   `tcw/store/yaml_source.py` and `fs.py` and `project.py` import it.
   A spec note records this reading.
3. **`ConfigError(BackendError)`** in `tcw/errors.py`, exit 1, carrying its
   `problems`. A subclass, so the existing `except BackendError` sites
   (`reference_resolver` answering `broken`, `validate`'s work checks) keep
   catching a configuration problem in another project.
4. **The per-command check lives in `tcw.cli._dispatch`**, after
   `refuse_retired_config`: inside a project, `load_config(root)` runs once and
   a non-empty `problems` raises `ConfigError`. `init`, `provision`, `validate`
   and `config show` opt out through `set_defaults(own_config=True)`;
   `config show` without `--origin` raises the same error itself. The result
   is kept for the rest of the command (`tcw.config.effective(root)`, cleared
   at the start of each `_dispatch`), so `open_backend` reuses it.
5. **What the built-in layer holds:** `work.backend: filesystem`,
   `work.hooks.timeout: 300`, `work.hooks.output-cap: 65536`, a
   `prompt: [{builtin: true}]` for every stage whose table row has a prompt,
   in table order, and `procedures.<id>: [{builtin: true}]` for every
   procedure id. Empty built-in lists are not written: a `pre` or `post` list
   no layer sets stays absent, which the parser already reads as empty, and a
   side stage never gets a `pre` or `post` key it would refuse. `work.path` is
   not a built-in value, because the store resolver tells "configured" from
   "default" by its presence.
6. **`null` in `tcw-config.yaml` over a built-in mapping keeps the mapping.**
   A `work:` key with nothing under it is a common file shape; today it means
   "no work settings", which is the defaults, so it keeps the built-in
   prompts rather than replacing them with nothing. A `null` anywhere else in
   `tcw-config.yaml` replaces the value and the parser judges it, as today.
7. **Key paths carry a list index as an `int`** (Design 2.1, R8). TCW-69's
   parser builds `str(i)`; it changes to `i`, and `ConfigProblem.__str__`
   prints the spec's form, `work.stages.spec.prompt[2]`. Each binding's origin
   is looked up per entry (`origins[(…, "prompt", i)]`), falling back to the
   list's.
8. **`Origin(layer, file)`** is a frozen dataclass in `tcw/config.py`; its
   `folder` is the declaring file's folder (`None` for built-in). It is what
   `Binding.origin` holds. `str()` gives `built-in`, `project`,
   `user: <path>` or `local: <path>`.
9. **A problem's file is shown relative to the project root when it is inside
   it**, else absolute, in `ConfigError` messages as in `validate`. The
   `TCW_NO_PERSONAL_CONFIG` problem has no file and starts with the variable's
   name.
10. **`TCW_NO_PERSONAL_CONFIG` with a bad value** reads neither personal file:
    the command exits 1 on the problem anyway, and reading a file the person
    tried to switch off would only add noise.
11. **`config show` prints each list entry on one line**: a mapping with one
    plain key and value in block form (`- builtin: true`, `- file: a.md`),
    anything larger in flow form (`- {file: a.md, when: {tags: [bug]}}`), so a
    comment can follow it and the output still parses to `values`. A string
    that cannot be one plain or quoted YAML line is written in JSON's
    double-quoted form, which YAML reads the same.
12. **A refused or skipped value under a key ending in `-env` is printed as
    `(value not shown)`** in `config show --origin`'s trailing comments, by the
    same rule as Design 4.7: a token pasted by mistake must not be echoed.
13. **A failed `post` hook names its file; a `pre` gate does not** (Design
    7.2): the message becomes ``<stage> post hook `<cmd>` from <file> failed
    (exit N)``. `pre` messages are unchanged.
14. **The personal-change note** reads `note: this prompt was changed by
    personal configuration: <files>`, the `note:` form TCW-73 uses for every
    other stderr note, and is written only when the composed list belongs to
    the acting project.
15. **Reading whether the local file is tracked** is one function,
    `tcw.store.fs.personal_file_tracked(root)`, added to the static guard's
    exempt list beside `git_root`, because it runs the status command whose
    name is on the git word list. Its message and `init`'s notice contain no
    git word, as Design 10.3 requires.
16. **The documentation allowance list gets nothing** (Design 9.6): it now
    lists `work.*` keys and top-level keys, but `TCW_WORK_OWNER` is a variable
    and `builtin:` a binding form, neither of which the documented-surface test
    looks for.
17. **`HOME` is not redirected for every test**; only `XDG_CONFIG_HOME` is,
    which is enough to keep the user-wide path inside the test folder. Tests of
    the home-folder fallback set `HOME` themselves.

## Tasks

### Task 1: The isolation fixture, `ConfigError`, and one YAML read

- **Modify `tests/conftest.py`**: an autouse fixture `_no_personal_config`
  beside `_no_project_overrides` and `_cache_in_tmp`: sets
  `TCW_NO_PERSONAL_CONFIG=1` and `XDG_CONFIG_HOME=<tmp_path>/xdg-config`.
- **Modify `tcw/errors.py`**: `class ConfigError(BackendError)`, exit 1, whose
  constructor takes a list of problems and whose message is one problem per
  line.
- **Modify `tcw/store/yaml_source.py`**: `UniqueKeyLoader` (the duplicate-key
  refusal) moves here. **Modify `tcw/store/fs.py`** and
  **`tcw/store/project.py`** to import it, deleting both copies.
- **Create `tests/config/__init__.py`, `tests/config/test_isolation.py`**:
  AC 19 (both variables set in an ordinary test); the duplicate key is
  refused through `fs.load_config` and through the registry, as before.
- Proof: the new tests; `tests/test_project_registry.py`,
  `tests/test_store_nodes.py` and the four standing files.

### Task 2: The loader, `tcw/config.py` (Design 1–6 except wiring)

- **Create `tcw/config.py`**: `PERSONAL_KEYS` (the six paths, in Design 4.1's
  order), `Origin`, `ConfigProblem`-based `Problem(file, key_path, message)`,
  `user_config_path()`, `read_project_file(root)`, `load_config(root, *,
  personal=True) -> Config` with `values`, `origins`, `work`, `jira` (the
  parsed `work.jira` in Jira mode), `problems`, `skipped`, `refused`, and
  `personal_files(key_path)` (the personal files that set a key). It
  implements: the layer paths (1.3–1.7), the per-file checks (`builtin:`,
  the `inherit` rules, duplicates per list, `null` in a personal file, `user`
  in `tcw-config.yaml`, `user.name`'s shape, the allowlist walk), the merge
  with the chain (3.1–3.9), skipping personal credential names outside Jira
  mode (4.6), `parse_work_config` and, in Jira mode, `parse_jira_config` on
  the merged result, mapping each problem back to a file (5.2), and the
  `file:` confinement check against the declaring file's folder (6.1).
- **Modify `tcw/work/config.py`**: list indexes as `int`; per-entry origin
  lookup (choice 7); `ConfigProblem.__str__` in the `a.b[2]` form; `Binding.origin`
  typed as an `Origin`.
- **Create `tests/config/test_layers.py`** (AC 1, 2), **`test_merge.py`**
  (AC 3, 4 including the `when:` case, 5), **`test_allowlist.py`** (AC 6, 7,
  15, 18, and 4.6's skip), **`test_problems.py`** (5.1, 5.2's file attribution
  for a bad personal binding and for a built-in entry, the first half of
  AC 10: a user-wide `file: ../x.md` is a problem naming that file whether or
  not it exists).
- Proof: the new files; `tests/work/test_config.py` and every test that reads
  `key_path` or a binding's `origin` (found by grep), changed for the `int`
  index where they assert it.

### Task 3: Every command on the loader (Design 2.3–2.5, 3.5)

- **Modify `tcw/work/open.py`**: `read_work_config(root, *, personal=True)` and
  `open_backend(root, *, report=None, personal=True)` use `load_config`
  (through `effective` for the acting project) and raise `ConfigError`;
  `FsWorkBackend` gets `user_name` from the effective `user.name`, and
  `JiraBackend` gets the parsed `jira` from the loader; `open_project`,
  `delegate`'s target read and `open_for_update` pass `personal=False`.
- **Modify `tcw/cli.py`**: the per-command check in `_dispatch` (choice 4).
- **Modify `tcw/work/resolve.py`** and **`tcw/work/cli.py`** (`_phases`): no
  code adds the packaged text; an absent list is empty.
- **Modify the TCW-70 fixtures and tests that write `builtin: true`** in a
  `tcw-config.yaml` to write `inherit: true` (AC 20, TCW-70 criterion 21), and
  TCW-70's contract test of `current_user()` for a backend built with no
  `user_name` if it still expects a raise.
- **Create `tests/config/test_commands.py`**: AC 8 (except `validate` and
  `config show`, which arrive in Tasks 6 and 7): `work list`,
  `work stage prompt spec`, `taxonomy list`, `capabilities list` exit 1 with
  stderr naming `tcw-config.local.yaml` and `id` and nothing on stdout;
  `--version` exits 0. AC 9's first two parts (the child's broken local file
  is not read by `work new --project <child>`; `open_backend` on the parent
  answers `Brian`, `open_project` for the child answers `None`), and AC 9's
  graph-reader part (`provision` and `projects list` unaffected). AC 11's
  packaged-text cases (`[]`, `[{blob: house}]`, `[{inherit: true},
  {blob: house}]`). AC 21.
- Proof: the new file; `tests/work/test_open.py`, `tests/work/test_compose.py`,
  `tests/work/test_cli_config.py`, `tests/work/test_cli_items.py`,
  `tests/work/test_cli_surface.py`, `tests/test_procedure_verb.py`,
  `tests/test_prompt_fallback.py`, `tests/test_shipped_prompts.py`,
  `tests/test_documentation_prompt.py`, `tests/work/jira/`, and the four
  standing files.

### Task 4: Origins at work: paths, `TCW_CONFIG_DIR`, `post_failures`, the note (Design 6, 7)

- **Modify `tcw/work/resolve.py`**: a `file:` binding is read from its
  origin's folder; a `generate:` binding runs from the project root with
  `TCW_CONFIG_DIR` set to its origin's folder (the project root when it has
  none).
- **Modify `tcw/work/hooks.py`**: `run_bindings` sets `TCW_CONFIG_DIR` per
  binding and returns a `HookFailure(binding, message)` (its `str()` is the
  message, so `tickets.py` and the `pre` path read as before); with
  `name_origin=True` the message names the binding's file (choice 13).
- **Modify `tcw/work/advance.py`**: `Outcome.post_failures`, a tuple of
  `(binding, origin, detail)`; `run_post` passes `name_origin=True`.
- **Modify `tcw/work/cli.py`**: `stage prompt` and `procedure` write the
  personal-change note (choice 14).
- **Create `tests/config/test_origins.py`**: AC 10 (a user-wide
  `file: prompts/spec.md` read from `$XDG_CONFIG_HOME/tcw/`; the
  `TCW_CONFIG_DIR` and working folder of a local and a user-wide `post` hook),
  AC 11 (`advance` with a failing user-wide `post` hook: exit 6, one
  `post_failures` entry with origin `user`, the message naming the file; the
  note present with a local `prompt` list and absent without; stdout the same
  with a local `[inherit]`), and the note for `procedure`.
- Proof: the new file; `tests/work/test_advance.py`, `tests/work/test_compose.py`,
  `tests/test_generate_hook.py`, `tests/work/jira/test_jira_tickets.py`, and the
  four standing files.

### Task 5: Identity: `--mine` and `--assign-me` (Design 9)

- **Modify `tcw/work/cli.py`**: `list --mine`, and `--assign-me` on `new` and
  `edit`, each refused with `--assignee` (exit 2); `new --project <id>
  --assign-me` exit 2, saying the target project assigns its own items; a
  `None` identity raises `ConfigError` with Design 9.2's message, naming the
  user-wide path `user_config_path()` gives.
- **Modify `tcw/store/project.py`**: `override_variable`'s docstring no longer
  cites `TCW_WORK_OWNER`.
- **Modify `tests/test_cli_contract.py`**: in-project cases for `list --mine`,
  `new --assign-me` and `edit --assign-me` (stdout exactly, files named
  through `written()`/`unnamed()`), the usage errors, and a Jira-mode case
  through the real `JiraBackend` against the fake (`--mine` lists the ticket
  assigned to `acct-dev`; `new --assign-me` assigns it).
- **Create `tests/config/test_identity.py`**: AC 13 (filesystem cases, the
  no-identity case with `TCW_WORK_OWNER` and a git identity set, and the
  interface case against a recording backend over TCW-69's in-memory
  backend), AC 9's `new --project <child> --assign-me` exit 2, AC 14 (no
  module under `tcw/` names `TCW_WORK_OWNER`; none passes `user.name` or
  `user.email` to the version-control configuration command).
- Proof: the new file and the contract test; `tests/work/test_cli_items.py`,
  `tests/work/test_cli_surface.py`, `tests/test_cli_help_standard.py`.

### Task 6: `tcw validate` and `tcw init` (Design 5.5, 10)

- **Modify `tcw/validate.py`**: before the graph check, the loader's problems
  as `error` findings (`where` the file, message starting with the key path),
  and the tracked-local-file `warning` with Design 10.3's exact text; the work
  checks no longer report a configuration problem a second time.
- **Modify `tcw/store/fs.py`**: `personal_file_tracked(root)` (choice 15).
- **Modify `tests/test_static_guards.py`**: its exempt list gains that
  function.
- **Modify `tcw/cli.py` `run_init`**: write `/tcw-config.local.yaml` into the
  `.gitignore` beside `tcw-config.yaml` unless a line is exactly it or
  `tcw-config.local.yaml`, naming the file with `wrote`; outside a repository,
  the notice (TCW-73 wins, item 3 above).
- **Modify `tests/test_smoke.py::test_init_without_work_writes_no_gitignore`**
  and **`tests/work/test_init_provision.py`** to assert only that no
  status-folder rule is written (AC 20, TCW-70 criterion 18).
- **Create `tests/config/test_validate_init.py`**: AC 8's `validate` line,
  AC 9's "`validate` in the parent says nothing about the child's local file",
  AC 16 (`tags add` leaves the local file byte-for-byte unchanged and changes
  `tcw-config.yaml` only in `work.tags`; a user-wide `post` hook does not
  appear in `tcw-config.yaml`), AC 17.
- Proof: the new file; `tests/test_validate_command.py`, `tests/test_validate.py`,
  `tests/test_smoke.py`, `tests/work/test_init_provision.py`,
  `tests/test_config_edit_writers.py`, and the four standing files.

### Task 7: `tcw config show [--origin]` (Design 8)

- **Create `tcw/config_cli.py`**: the `config` group and its `show` leaf,
  built with `tcw/cli_help.py` (`Prints: the effective configuration as YAML;
  with --origin, where each value came from`, `Writes: nothing`, two
  examples); the YAML writer of choice 11; `--origin`'s comments and its
  trailing `# skipped:` / `# refused:` block; exit 1 with problems on stderr,
  and with `--origin` still printing what it can.
- **Modify `tcw/cli.py`**: register the group.
- **Modify `tests/test_cli_help_standard.py`**: `SURFACE` gains
  `config show` (43 leaves).
- **Modify `tests/test_cli_contract.py`**: the `ROWS` entry
  (`["config", "show"]`, exit 1 outside a project) and an in-project case
  (stdout parses to `load_config(...).values`, nothing written).
- **Create `tests/config/test_config_show.py`**: AC 12 (all four bullets),
  AC 8's `config show` case.
- Proof: the new file and the two changed tests; the four standing files.

### Task 8: Mutation checks and collection

No new behavior. Each guard named under "Mutation checks" below is broken on
purpose, its test seen red for the stated reason, and the code restored; the
results go to `outcome.md`. Then `pytest --collect-only -q` with no errors.
This task has no commit of its own unless a mutation exposes a gap, in which
case the fix and its test are the commit.

### Task 9: Ledger and taxonomy records

- **Create** under `docs/taxonomy/`: vocabulary `config-layer`, `user-identity`;
  feature `personal-configuration` (vocabulary `config-layer`,
  `user-identity`, `work-item/lifecycle-stage`, `work-item/lifecycle-hook`;
  relates to `configurable-work-lifecycle` and `configure-skill`).
- **Create** under `docs/capabilities/`: `cli/override-the-team-configuration-for-myself`,
  `cli/show-the-effective-configuration`, `work/tell-tcw-who-i-am`
  (Feature `personal-configuration`, status `Supported`).
- **Modify**: `work/configure-the-work-lifecycle`, `work/configure-procedures`,
  `work/run-a-lifecycle-stage`, `work/run-a-procedure` (`builtin: true`
  becomes `inherit: true`; the last two gain the personal-change note),
  `cli/validate-a-project` (the tracked-file warning and personal-file
  problems), `cli/scaffold-the-doc-trees` (the `.gitignore` line). No record
  carries `Planning doc` or `Tracker`.
- **Write `capabilities.yaml`** in the item folder on `main` listing these.
- Proof: `tests/test_ledger_3_0.py`; `records_problems(..., finished=True)` over
  the item's `capabilities.yaml` against the branch's ledger reports nothing.

### Task 10: Release notes and changelog

- **Create `docs/release-notes/upcoming/<slug>.md`**, starting with its first
  `##` heading (Design 12), in plain language: the two personal files and
  what they may set, `inherit: true` in place of `builtin: true`,
  `tcw config show`, `user.name`, `--mine`, `--assign-me`, `TCW_CONFIG_DIR`,
  the ignore line `init` writes and the warning `validate` gives,
  `TCW_WORK_OWNER` gone.
- **Create `docs/changelogs/upcoming/<slug>.md`** under Added / Changed /
  Removed / Internal.
- Proof: `tests/test_upcoming_entries.py`.

## Documentation Sync

| Entry | Fires | Handled |
| --- | --- | --- |
| `README.md` [Public-API] | Yes: a new command and new flags | Deferred to TCW-75, which rewrites the README for 3.0 (spec Design 12). |
| `docs/guide/jira.md` [Tracker-Change] | Yes: the credential names may now come from a personal file | Deferred to TCW-75 (user guides are its, spec Design 12). |
| `docs/guide/<topic>.md` [Guide-Topic-Change] | Yes: new files TCW reads, a new `.gitignore` line | Deferred to TCW-75. |
| `docs/release-notes/upcoming/<slug>.md` [Public-API] | Yes | Task 10. |
| `docs/changelogs/upcoming/<slug>.md` [Any-Code-Change] | Yes | Task 10. |
| `skills/<component>/SKILL.md` [Skill-Driven-Component] | Yes: the `work` skill names `builtin: true` and the old identity | Deferred to TCW-74 (every skill but `configure`). |
| `skills/configure/references/<document>.md` [Configuration-Key-Change] | Yes: `user.name`, the two personal files, `inherit` | Deferred to TCW-75, which writes `personal.md` and the shared/overridable table against `PERSONAL_KEYS` (spec Design 12, epic decision 3). |

## Mutation checks (Task 8)

- The allowlist walk accepting every key: AC 6's tests go red.
- `inherit` resolved as "replace": AC 4's chain table goes red.
- Personal layers applied in `open_project`: AC 9's `current_user() is None`
  goes red.
- The per-command check removed from `_dispatch`: AC 8's taxonomy and
  capabilities cases go red.
- The built-in fallback restored in `resolve.py`: AC 11's `[]` case goes red.
- `TCW_CONFIG_DIR` set to the project root for every binding: AC 10's
  user-wide case goes red.
- `current_user()`'s `None` turned into an empty `Query.assignee`: AC 13's
  no-identity case goes red.
- `config show --origin` printing a refused key as a key: AC 12's parse-back
  equality goes red.
- The tracked check reading `??` as tracked: AC 17's warning cases go red.
- The credential-name message echoing the value: AC 18 goes red.

## Verification

What the suite cannot see, checked by hand in a scratch folder with the
branch's code and recorded in `outcome.md`:

- `tcw init --id walk` in a fresh git repository: `.gitignore` holds
  `/tcw-config.local.yaml`, named on stderr; outside a repository the `note:`
  line.
- With a `tcw-config.local.yaml` holding `user: {name: Walker}` and a
  `prompt` list `[{blob: mine}, {inherit: true}]` for `spec`: `tcw config show`
  reads plainly; `--origin` marks the `local` entries; `tcw work stage prompt
  spec` prints `mine` above the packaged text and the note on stderr;
  `tcw work new --assign-me x` then `tcw work list --mine` prints the item.
- Adding `id: other` to the local file: `tcw work list` exits 1 naming the
  file and key; `tcw config show --origin` exits 1, prints the configuration
  and a `# refused:` line.
- `tcw --help` lists `config`; `tcw config show --help` reads plainly.

## Notes

- **Self-hosting.** This changes `tcw/`; the board is driven by the released
  2.8.1 `tcw` from the primary checkout, and outcome, capabilities and spec
  notes are committed on `main`.
- **Not done here, by the spec:** the configure skill and its table (TCW-75),
  other skills and prompts (TCW-74), the guides and README (TCW-75), the
  migration guide's entries for `builtin` → `inherit`, `TCW_WORK_OWNER` →
  `user.name`, `TCW_CONFIG_DIR` and the ignore line (TCW-76), and the viewer's
  `user` field (TCW-77).
