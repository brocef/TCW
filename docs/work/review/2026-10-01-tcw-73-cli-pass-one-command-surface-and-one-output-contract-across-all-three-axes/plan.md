# Plan — CLI pass: one command surface and one output contract across all three axes

This plan follows the spec as revised after the 2026-10-02 review. Each task is
one commit on `work/<this item>`, made from `epic/tcw-3.0` at `89ff245d`, and
the tests the task names pass after it. The order is the spec's three phases
(Risks, "This is large for one item"):

- **Phase A, the contract and the work surface** (Tasks 1–4): the top-level
  handler and the output helpers, the `tcw work` surface, `tcw projects list`,
  and the exit classes in the tree stores.
- **Phase B, taxonomy, capabilities and the top-level commands** (Tasks 5–16):
  files only, the two axes' commands on the contract, the finding type,
  `validate`, `drift`, `init`, `provision`, the help standard, the static
  guards, the contract test and the shell scenarios.
- **Phase C, the renames** (Tasks 17–19): the `projects:` key, "node" out of
  the code, and the ledger and taxonomy records. Then the release-notes entries
  (Task 20).

## Before the first task

**What TCW-69, TCW-70 and TCW-71 left, read on the branch at `89ff245d`.**
`tcw/errors.py`, `tcw/exit.py` and `tcw/findings.py` exist; `TcwError.name`
exists as a class attribute but only `Refused` takes it in its constructor.
`tcw/work/cli.py` is the 3.0 work surface with `resolve_item` (Jira key first,
then `Slug.parse`, exact match), `_own` refusing writes to another project, and
`new` printing `error.name` itself. `tcw validate` already prints the work
findings as `error:`/`warning:`/`unresolved:` lines, but on stderr, beside
2.x-shaped string problems, with recursion over descendants and a `[path]`
selector. `capabilities drift` already uses `drift_problems`, for filesystem
mode only. The tree stores still stage with `git add`/`git rm`, and
`tests/work/test_git_write_scan.py` allows that "until TCW-73".

**Which source runs.** A private virtual environment at
`<scratch>/tcw73/venv` (`python -m venv --system-site-packages`, then
`pip install -e <worktree> --no-deps`); pytest and the CLI run from the
worktree root. The board on `main` is driven by the released 2.8.1 `tcw`, never
by the worktree's code.

**Tests, per the owner's rule for this epic.** The full suite is not run per
task. Each task runs the test files it names, plus every 2.x test file that
reaches code it touched, found with `grep -rl` over `tests/` for the names it
changes. A 2.x test that breaks because 2.x behavior is removed may be deleted
or skipped rather than ported; each one is listed in `outcome.md`. The last
task ends with `pytest --collect-only -q` clean.

**The documentation allowance.** `tests/test_documented_cli_surface.py` fails
when live Markdown names a command or flag that does not exist. Every task that
removes a command, a flag or a key adds it to `tests/doc_allowance.py` in the
same commit (spec Design 9.4), so the surface test stays green at every commit.
The guard test `tests/test_doc_allowance.py` checks each entry really is gone.

## Choices this plan makes

Where the spec leaves a decision open, or where the code the earlier slices
left forces one, this plan chooses as follows. Each is recorded again in
`outcome.md`.

1. **The contract test runs Jira-mode rows in-process.** Design 10 asks for
   subprocesses, and the filesystem rows are subprocesses. TCW-71's fake Jira
   replaces the client's `_request` inside the running interpreter
   (`FakeJira.install`); a subprocess could receive it only through a startup
   hook planted in the interpreter, which would put test-only code in the
   package. The Jira rows call `tcw.cli.main` with the fake installed and
   `capsys` capturing both streams, which observes the same contract.
2. **The contract test lands at the end of phase B, not in phase A.** Its rows
   assert the taxonomy and capabilities outputs, which phase B builds. Phase A
   ends instead with its own tests of the work surface and the handler.
3. **`tcw work procedure` keeps working outside a project.** Criterion 10 asks
   every leaf command except `init` to exit 1 outside a project, but the
   `documentation-sync` skill reads `tcw work procedure` outside TCW projects,
   and TCW-70 kept that on purpose (`tcw/work/cli.py:399-403`). The contract
   test's table marks the row as working outside a project; the spec gets an
   implement finding.
4. **A refused `raise` in the tree stores may also name `StoreLocationUnusable`
   or `StaleRevision`.** Criterion 25 asks every `raise` in the tree-store
   classes to name `UsageError`, `Refused`, `NotFound` or a subclass. Those two
   are not answers to a user's request: the first is the resolution ladder's
   "no store here" signal, which callers catch as a `ValueError`; the second is
   the viewer's concurrency signal. The static test forbids `ValueError`,
   `RefError` and `AmbiguousRef`, and allows exactly these two by name, plus a
   bare re-raise.
5. **`AmbiguousRef` becomes `class AmbiguousRef(UsageError, RefError)`.** It
   keeps being caught by every `except RefError`, and its code resolves to 2
   through the class order.
6. **No abbreviated options.** `SuggestingParser` passes `allow_abbrev=False`,
   so `--ta` is not `--tag`. Without it, "each option has one spelling"
   (Design 5.5) is false.
7. **The error prefix comes from the parser path.** `attach_index` already
   walks every parser with its path; it also sets a default `_command` on each
   (`"tcw work advance"`), and `main` prints `<_command>: <message>`.
8. **A broken pipe exits quietly with 1** (TCW-70 deferral 3). `main` catches
   `BrokenPipeError`, points stdout at the null device so the interpreter's own
   flush at exit cannot fail again, prints nothing, and returns 1, as the
   Python documentation's note on SIGPIPE recommends.
9. **A `BackendError` from another project is a `warning`** in `validate`
   (TCW-70 deferral 1). The project is present, so the finding is not
   `unresolved` (Design 6.2, R16); and the fault is that project's
   configuration, which this project's run must not fail for. The warning names
   the project and says to run `tcw validate` there.
10. **Quoting in messages** (TCW-70 deferral 2): a name (a project ID, a slug, a
    key, a stage) is in single quotes; a command the user can run is in
    backticks. `open.py:157` is the one that breaks it.
11. **`_Unreadable` and `Unreadable` merge** (TCW-70 deferral 4) into one
    exception class, `Unreadable(path, key, message)`, which `read_all` collects
    instead of copying.
12. **`tcw init` with no `--id` for a new project is a usage error (2)**, not 1:
    a required value is missing from the command line (Design 4's row 2).
13. **`lifecycle` prints every stage of the table**, enabled or not, each with
    its kind and an `enabled` flag, so "the stage table with each stage's
    enabled state" (Design 2, decision 4) is literal. `--stage` with a disabled
    stage prints it rather than refusing.
14. **`tcw projects list`** prints the current project, then its parent, its
    children and the upstream projects it may read (declared by it or an
    ancestor), each once, present or not. `--json` gives each its `id`,
    `relation` (`current`, `parent`, `child`, `upstream`), `present` and `path`
    (`null` when absent).
15. **`tickets list --json`** is `{"schema": 1, "tickets": [...]}`, the named
    key Design 1.6 asks for.
16. **Misdirected locators** (`registry.misdirected()`) become `warning`
    findings in `validate`; they were stderr notes that never failed.
17. **Shell scenarios**: `06-stdin-and-process-boundaries.md` and
    `13-release-integrity.md` are rewritten to 3.0, because they cover what an
    in-process or per-command test cannot (an inherited open stdin; the
    installed wheel). The other twelve are deleted (Task 16 gives each reason).
18. **`drift_problems` returns structured problems.** TCW-69's function returns
    strings shaped `drift (by): …`; Design 7.3 needs
    `<kind>: <path or term>: <message>`. It returns `DriftProblem(kind, where,
    message)` values instead, whose `str()` is that line, and its tests change
    with it.

## Phase A — the contract and the work surface

### Task 1: The top-level handler and the output helpers (Design 1.2, 1.3, 1.8, 4; AC 26 in part)

- **Modify `tcw/errors.py`**: `TcwError.__init__(self, message, *, name=None)`
  sets `self.name` on every class, so a `BackendError` can carry the name of
  what was created (Design 1.8). `Refused` loses its own `__init__`.
- **Create `tcw/output.py`**, the one place stderr narration is shaped:
  `say(line)` (stderr), `shown(path)` (relative to the current directory when
  inside it, else absolute; Design 1.2), `wrote(path)`, `removed(path)`,
  `created(path)` (prints `created <path>/`), and `print_json(key_or_none,
  value)` which prints one object with `"schema": 1` first.
- **Modify `tcw/cli_suggest.py`**: `SuggestingParser.__init__` defaults
  `allow_abbrev=False` (choice 6); `attach_index` sets `_command` on each parser
  to its path joined by spaces (choice 7); `SYNONYMS` gains `start`, `submit`,
  `rework` and `complete` → `advance` (Design 2, decision 1).
- **Modify `tcw/cli.py` `main`**: on `TcwError`, print `error.name` on stdout
  when set, then `<_command>: <message>` on stderr, and return its code; the
  `ValueError`, `MultipleMatch`, YAML and `OSError` branches print with the same
  prefix and return 1; a `BrokenPipeError` exits quietly with 1 (choice 8). The
  `CalledProcessError` branch stays until Task 6 removes the staging that
  raises it.
- **Modify `tcw/work/cli.py`**: `_new` stops printing `error.name` itself (the
  handler does). **Modify `tcw/work/fs_backend.py` `rename`**: a failure after
  the folder moved raises `BackendError(..., name=<new slug>)`; check that
  TCW-71's Jira `create` failures after step 5 carry the slug, and add `name=`
  where one does not. The `wrote`, `created` and `removed` lines both
  backends report name their paths through `shown()`, so they are relative to
  the current directory when inside it (Design 1.2).
- **Tests**, new `tests/test_cli_handler.py`: the prefix for a failing
  `tcw work show` and a failing `tcw taxonomy show`; a stubbed `create` raising
  `BackendError(name="fx/2026-10-02-x")` prints exactly that on stdout and exits
  1; one raising with no name prints nothing on stdout; `rename` failing after
  the move prints the new slug and exits 1 (AC 26); `--ta` for `--tag` exits 2;
  a broken pipe on stdout returns 1 with nothing on stderr. Update every test
  asserting a `tcw: ` prefix (`grep -rln '"tcw: ' tests`).
- **Proof:** `pytest tests/test_cli_handler.py tests/test_command_suggestions.py tests/work -q`.

### Task 2: The `tcw work` surface (Design 1.6, 1.7, 1.9, 2 decisions 1, 4–7; AC 3, 8 in part, 10 in part, 11 in part, 19, 28)

- **Modify `tcw/work/cli.py`**:
  - `--tag`, `--untag` and `tags add|rm`'s values: one tag per use, no
    `--tags`/`--untags` alias; a value containing a comma is a usage error
    saying to repeat the option (Design 2, decision 6).
  - `list --json` prints `{"schema": 1, "items": [...]}`; `show --json` prints
    `{"schema": 1, "item": …, "request": …, "comments": [...]}` with comments
    newest first, each `{"at", "author", "text"}`, `at` in
    `YYYY-MM-DDTHH:MM:SSZ`; `tickets list --json` prints
    `{"schema": 1, "tickets": [...]}` (choice 15).
  - `show`'s text form: the record lines (`untracked:` only when not empty),
    a blank line, `request:` with the text indented two spaces or
    `request: none`, then `comments:` and each comment as `- <at> <author>` and
    its indented text. In Jira mode the assignee and each author are display
    names through TCW-71's `user_name`, falling back to the account ID; `--json`
    keeps the IDs (Design 1.9, R15).
  - `procedure prompt <id>` becomes `procedure <id> [<slug>] [--no-exec]`.
  - `lifecycle` loses its slug, `--directive` and `--phase`; prints every stage
    with kind and enabled state and its `pre`, `prompt`, `post` bindings;
    `--json` gains `"schema": 1` and an `"enabled"` per stage (choice 13).
  - `tags add` and `tags rm` print nothing on stdout and name
    `wrote tcw-config.yaml` on stderr when it changed.
  - `nodes` and `init` are removed (Task 3 adds `tcw projects list`; Task 12
    finishes `tcw init <axis>`).
  - `new --stage inbox` in Jira mode is a usage error (Design 4).
  - `SUBCOMMANDS` and `DEFAULT_SUBCOMMAND` go (Design 2, decision 2).
- **Modify `tcw/work/model.py` `stage()`** only if an unknown stage is not
  already a `UsageError` listing the valid names (Design 2, decision 7); same
  for the procedure ID check in `_procedure_prompt`.
- **Modify `tests/doc_allowance.py`**: `tcw work procedure prompt`,
  `tcw work nodes`, `tcw work init` in `REMOVED_COMMANDS`;
  `("tcw work lifecycle", "--directive")`, `("tcw work lifecycle", "--phase")`,
  `("tcw work list", "--tags")`, `("tcw work new", "--tags")`,
  `("tcw work edit", "--tags")`, `("tcw work edit", "--untags")` in
  `REMOVED_FLAGS`.
- **Tests**: new `tests/work/test_cli_surface.py` for the show text and JSON
  forms with request and comments (AC 8's bullet), `request: none` and `null`,
  `list --tag a --tag b`, `--tag a --stage spec`, `--tag zzz` warning and exit
  0, `--tag a,b` → 2 naming `--tag`, `--tags a` → 2, `procedure create-work`,
  `lifecycle --json` with `"schema": 1`, `lifecycle --directive` → 2,
  `tcw work start x` → 2 naming `tcw work advance`, `tcw work drop x` → 2 with
  no suggestion (AC 3), the Jira display names against the fake (AC 28), and
  `new --stage inbox` in Jira mode → 2. Update `tests/work/test_cli_items.py`,
  `tests/work/test_cli_config.py`, `tests/work/jira/test_jira_tickets.py`,
  `tests/test_procedure_verb.py`, `tests/test_shipped_procedures.py`,
  `tests/test_skill_lifecycle_parity.py`, `tests/test_command_suggestions.py`,
  `tests/test_lifecycle_config_tags.py` for the JSON wrappers and removed
  spellings.
- **Proof:** `pytest tests/work tests/test_procedure_verb.py tests/test_shipped_procedures.py tests/test_command_suggestions.py tests/test_documented_cli_surface.py tests/test_doc_allowance.py -q`.

### Task 3: `tcw projects list` (Design 2; AC 7 in part)

- **Create `tcw/projects_cli.py`** with `add_subparser`: `tcw projects list
  [--json]` (choice 14), built on `FsProjectRegistry` (`current`, `parent`,
  `children`, `declared_upstream_ids`, `unreachable()` for absent entries).
- **Modify `tcw/cli.py`** to register it.
- **Tests**: new `tests/test_projects_list.py`: one-line-per-ID order with a
  parent, two children, an upstream and an absent child; `--json` schema and
  relations; outside a project → 1. Rewrite the `tcw work nodes` cases in
  `tests/test_multiproject.py`, `tests/test_upstream_projects.py`,
  `tests/test_routing_nodes.py`, `tests/test_store_provisioning.py`,
  `tests/test_environment_hardness.py` and `tests/test_project_overrides.py`
  against `projects list --json`; delete a case whose subject was the 2.8 text
  layout only.
- **Proof:** `pytest tests/test_projects_list.py` and the six files above.

### Task 4: The exit classes in the tree stores (Design 4; AC 25)

- **Modify `tcw/store/base.py`**: `RefError(NotFound)`;
  `AmbiguousRef(UsageError, RefError)` (choice 5); the `TaxonomyStore` and
  `CapabilitiesStore` docstrings say which class each operation raises, by
  Design 4's table.
- **Modify `tcw/store/fs.py`**: every `raise ValueError` in `FsTreeStore`,
  `FsTaxonomyStore`, `FsCapabilitiesStore` and the module functions from
  `_revision` (line 1116) to the end of `FsCapabilitiesStore` becomes
  `NotFound`, `UsageError` or `Refused` by Design 4's table. The
  classification, by the line numbers at `89ff245d`:
  - **`NotFound`**: 1918, 2199, 2548, 2579, 2646, 2726, 2745 (no such entry);
    2057, 2796 (an `extends` ID not in the list).
  - **`UsageError`**: 1169, 1171, 1174 (`_safe_store_id`); 1886, 1896 (a parent
    that names nothing); 1889, 2242 (a kind outside the list); 1903, 2252 (a
    Feature with no vocabulary); 2086, 2088, 2090, 2108 (a reference value that
    does not resolve, is ambiguous or is the wrong kind); 2212 (a field that is
    not editable); 2544, 2665 (a Status outside the list); 2660 (a field outside
    `CAP_FIELDS`); 2690 (the joined field problems); 2045, 2784 (a project ID
    nothing registers); 2049, 2788 (a project with no store).
  - **`Refused`**: 1898, 2550 (a name already taken); 1920, 2201, 2581, 2642,
    2738 (an inherited entry where only a local one may change, or a local one
    where only an override may); 1944, 2591 (nested entries); 1961, 2595, 1990
    (still referenced, or the referrers cannot be read); 2652 (`reset` with no
    override); 2040, 2779 (already extended); 2047, 2786 (extends itself); 1505
    (a config section that is not a mapping, which the user must fix first).
  - **`BackendError`**: 1151 (a record that could not be read back), a fault
    rather than an answer.
  - 1939, 1955 and 1969 are deleted by Task 6, not classified.
  Every caller in `tcw/` that caught `ValueError` from one of these methods
  catches the class it now raises: found with `grep -n "except (ValueError"`
  and `except ValueError` over `tcw/`, read one by one. `tcw/serve/__init__.py`'s
  write handlers catch `TcwError` beside `ValueError` and keep their HTTP
  status (R14 allows this one adaptation).
- **Tests**: new `tests/test_tree_store_raises.py`, the static test of AC 25
  (choice 4), parsing `tcw/store/fs.py` with `ast`. Mutation check: restore one
  `raise ValueError` and see it fail. Update assertions on `ValueError` in
  `tests/test_taxonomy.py`, `tests/test_capabilities.py`,
  `tests/test_capabilities_rm.py`, `tests/test_capabilities_reset.py`,
  `tests/test_capabilities_federation.py`, `tests/test_taxonomy_rm_gaps.py`,
  `tests/test_store_editor.py`, `tests/test_serve_write.py` (found with
  `grep -ln "ValueError" tests`).
- **Proof:** those files and `tests/test_tree_store_raises.py`.

## Phase B — taxonomy, capabilities and the top-level commands

### Task 5: The finding type through `check()` and `validate()` (Design 6.3; AC 27)

- **Modify `tcw/store/base.py`**: `ProjectRegistry.check`,
  `TaxonomyStore.check` and `CapabilitiesStore.check` return `list[Finding]`.
- **Modify `tcw/store/project.py`**: `_problem(path, message)` keeps the path
  and message apart; `check()` returns `Finding("error", <path>, <message>)`;
  `warnings()` stays strings, turned into `warning` findings by `validate`.
- **Modify `tcw/store/fs.py`**: `FsTaxonomyStore.check` and
  `FsCapabilitiesStore.check` build `Finding("error", <entry's path relative
  to the project root>, <message>)`; `_legacy_config_problems` likewise.
- **Modify `tcw/validate.py`**: `validate()` returns `list[Finding]`; every
  string problem becomes a finding with a `where` (graph and config problems:
  the config file; YAML and link problems: the file; component checks: the
  check's own `where`). `is_failure` and `NOT_FAILING` go;
  `severity == "error"` replaces them. The `(component checks skipped …)` line
  becomes stderr narration returned beside the findings.
- **Modify the callers**: `tcw/cli.py` `_cmd_validate` (interim: still prints
  as today, but from findings), `tcw/work/cli.py` if TCW-70 kept a stale-tag
  check, and `tcw/serve/__init__.py` `_validation_warnings`, which renders each
  with `str()` so the viewer's response stays a list of strings.
- **Tests**: new `tests/test_findings_type.py` (AC 27: each of the four returns
  only `Finding` values over a fixture with a problem of each; a serve save
  leaving a dangling reference gives `warnings` strings shaped
  `<severity>: <where>: <message>`). Update `tests/test_validate.py`,
  `tests/test_validate_target.py`, `tests/test_validate_moved_stores.py`,
  `tests/test_legacy_store_config.py`, `tests/test_project_registry.py`,
  `tests/test_capability_ref_wording.py`, `tests/test_taxonomy.py`,
  `tests/test_capabilities.py`, `tests/test_capabilities_federation.py`,
  `tests/test_upstream_projects.py`, `tests/test_environment_hardness.py`,
  `tests/test_override_references.py`, `tests/test_override_letter_case.py`,
  `tests/test_override_in_linked_worktree.py`, `tests/test_project_graph_paths.py`,
  `tests/test_worktree_sibling_nodes.py`, `tests/test_documentation_config.py`,
  `tests/test_store_provisioning.py`, `tests/work/test_validate_work.py`,
  `tests/work/test_properties.py`, `tests/work/jira/test_jira_validate_offline.py`
  to compare `str(f)` or the finding's fields, asserting the message text.
- **Proof:** the files above.

### Task 6: Taxonomy and capabilities write files only (Design 8.1, 8.2, 8.5; AC 17)

- **Modify `tcw/store/fs.py`**:
  - `FsTreeStore` gains `self.changed: list[tuple[str, Path]]` (`"wrote"`,
    `"removed"`, `"created"`), the filesystem adapter's own record of what it
    changed (Design 1.2). `_stage` is deleted; `_write_staged` becomes
    `_write_files`, keeping its rollback and recording each path it wrote;
    `_rm(path)` deletes the folder from disk and records one `removed` line
    per file it held; `_write_node_config` writes without staging and records
    the config file.
  - `require_repository`, `_require_repository`, `NOT_A_REPOSITORY`,
    `git_stage`, `git_rm`, `_git_index`, `INDEX_LOCK_RETRY`, `_warn_hidden`,
    `git_ignored` and `_untracked_under` go when nothing else calls them
    (checked with `grep -rn` over `tcw/`).
  - `FsTaxonomyStore.remove` decides from the disk (Design 8.2): nested terms
    are the subfolders holding a `meta.yaml`; an untracked term is removed like
    any other; operating-system files (`OS_METADATA_FILES`) go with the folder.
  - `init` no longer refuses a `work.path` outside a repository.
- **Modify `tcw/cli.py`**: `run_init` no longer refuses outside a repository;
  the `CalledProcessError` branch in `main` goes (Design 4).
- **Modify `tests/work/test_git_write_scan.py`**: `git_stage` and `git_rm`
  leave `ALLOWED`; `taxonomy/cli.py` and `store/` stay scanned.
- **Tests**: new `tests/test_tree_store_files_only.py` (AC 17): inside a
  temporary repository, every taxonomy and capabilities write and `tcw init`
  leave `HEAD`, `for-each-ref` and `git diff --cached` unchanged; `taxonomy rm`
  removes a term whose files were never added; the same commands succeed in a
  directory that is not a repository. Rewrite or delete the tests that pinned
  staging or the refusal outside a repository: `tests/test_literal_store_names.py`,
  `tests/test_config_edit_writers.py`, `tests/test_taxonomy_rm_gaps.py`,
  `tests/test_capabilities_rm.py`, `tests/test_taxonomy.py`,
  `tests/test_capabilities.py`, `tests/test_serve_write.py` (found with
  `grep -ln "diff.*--cached\|ls-files\|staged\|not inside a git" tests`).
- **Proof:** the files above and `tests/work/test_git_write_scan.py`.

### Task 7: The `tcw taxonomy` commands on the contract (Design 1, 2, 4, 8; AC 2, 8, 9, 10, 14 in part)

- **Modify `tcw/taxonomy/cli.py`**:
  - no `init`, `check`, `SUBCOMMANDS`, `DEFAULT_SUBCOMMAND`; no positional
    description and no `-s`/`-p` on `add`; the description comes from stdin
    only;
  - errors raise (`BackendError` for no project here; the store's classes
    otherwise), no command prints its own error line;
  - stdout: `add` prints the new term's qualified path; `list` and `search`
    print one qualified path per line, or `--json`
    (`{"schema": 1, "terms": [...]}` with `path`, `name`, `kind`, `origin`);
    `show` prints the record, or `--json` (`{"schema": 1, "term": {...}}`);
    `rm` and `extends add|rm` print nothing;
  - after every write, each line of the store's `changed` list on stderr
    through `tcw.output`.
- **Modify `tcw/cli.py`**: `_normalize` goes (Design 2, decision 2).
- **Modify `tests/doc_allowance.py`**: `tcw taxonomy init`,
  `tcw taxonomy check`; the flags `("tcw taxonomy add", "-s")`,
  `("tcw taxonomy add", "-p")`; the shorthand, as a list of shorthand
  invocations the surface test skips (`tcw taxonomy <path>`), with its guard.
- **Tests**: rewrite `tests/test_taxonomy.py`'s CLI cases and
  `tests/test_taxonomy_rm_gaps.py` to the new outputs; new cases in
  `tests/test_taxonomy_cli_contract.py`: `tcw taxonomy lst` → 2 suggesting
  `list` and not "no such term" (AC 2); `add Widget` prints `widget`, twice → 3;
  `show nosuch` → 4; `rm` of a term another names in `relatesTo` → 3; `rm` of
  a term with two files prints exactly two `removed` lines (AC 9); `extends
  add` prints nothing and names `tcw-config.yaml`.
- **Proof:** `pytest tests/test_taxonomy*.py tests/test_smoke.py tests/test_documented_cli_surface.py tests/test_doc_allowance.py -q`.

### Task 8: The `tcw capabilities` commands on the contract (Design 1, 2, 4, 5.5, 8.6; AC 8, 9, 10, 15 in part, 16 last bullet)

- **Modify `tcw/capabilities/cli.py`**: as Task 7 for its commands; `list
  --local` replaces `--local-only`; `extends add <id>` and `extends rm <id>`
  replace `extends <id> [--rm]`; `add --status` without `-s`, and the body from
  stdin; `set --field K=V`: a repeated key is a usage error, as is a value with
  no `=`; `--status` and `--field Status=` together count as a repeated key;
  `--json` on `list`, `search` (`"capabilities"`) and `show`
  (`"capability"`); `drift` is left to Task 11.
- **Modify `tcw/store/base.py`**: `Planning doc` and `Tracker` leave
  `CAP_FIELDS`. **Modify `tcw/store/fs.py` `FsCapabilitiesStore.check`**: a
  record carrying either is an error whose message names
  `docs/migration-guide-2.8-to-3.0.0.md` (Design 8.6). `tcw/serve/` follows
  the smaller set unchanged.
- **Modify `tests/doc_allowance.py`**: `tcw capabilities init`,
  `tcw capabilities check`; `("tcw capabilities list", "--local-only")`,
  `("tcw capabilities add", "-s")`, `("tcw capabilities extends", "--rm")`.
- **Tests**: rewrite `tests/test_capabilities.py`,
  `tests/test_capabilities_rm.py`, `tests/test_capabilities_reset.py`,
  `tests/test_capabilities_federation.py`, `tests/test_store_bounds.py`,
  `tests/test_skill_flow.py` (its `Planning doc` lines) to the new surface; new
  `tests/test_capabilities_cli_contract.py`: `add ns/do-a-thing` prints
  `ns/do-a-thing`; `set --status Supported` prints nothing; `set --field
  Subject=nosuch` → 2; `--field Subject=a,b` with both registered → 0 and
  `show` lists both; a repeated `--field Status` → 2; `--field Status` → 2;
  `reset` on a local capability → 3; `show nosuch` → 4; `--field "Planning
  doc=x"` and `--field Tracker=x` → 2; a record carrying `Planning doc:` gives a
  check error naming the migration guide.
- **Proof:** `pytest tests/test_capabilit*.py tests/test_store_bounds.py tests/test_skill_flow.py tests/test_documented_cli_surface.py tests/test_doc_allowance.py -q`.

### Task 9: `tcw validate` (Design 6.1–6.3; AC 7 in part, 14, 15)

- **Modify `tcw/cli.py`**: `validate [--remote]` only. The current project
  only (no `[path]`, `--no-recurse` or descendant walk). Overrides are stderr
  narration; graph problems are `error` findings and stop the run; each
  unreachable project is an `unresolved` finding; each misdirected locator and
  each registry warning a `warning` (choice 16). Findings go to stdout, one per
  line; the closing count `N errors, N warnings, N unresolved` to stderr;
  exit 1 when any `error`, else 0. `--remote` in filesystem mode → 2; with it,
  the remote findings join the same list and an unreachable Jira exits 5.
- **Modify `tcw/validate.py`**:
  - drop the `path` selector and `_scan_roots`'s path branch,
    `_components_to_check`'s path branch and `_checks_work`'s path argument;
  - an unreadable `item.yaml` is an `error` and the run continues (R11);
  - a `BackendError` from another project's backend in `reference_resolver`
    (`tcw/work/open.py`) is a `warning` (choice 9);
  - the verdict-round check (Design 6.1.7): for each item and each verdict
    stage, `layout.current_verdict(slug, stage) == "invalid"` gives a warning
    naming the latest round file; run offline in both modes;
  - in Jira mode the records check runs only under `--remote`: confirm that
    `tcw/work/jira/remote.py` runs `records_problems(..., finished=False)` over
    non-terminal items (TCW-71's outcome says it does) and add it if not.
- **Modify `tcw/work/fs_backend.py`**: `_Unreadable` and `Unreadable` merge
  (choice 11).
- **Modify `tests/doc_allowance.py`**: `("tcw validate", "--no-recurse")` and
  the `[path]` form.
- **Tests**: new `tests/test_validate_command.py` for every bullet of AC 15
  that is not Jira (warning for a missing `blocked-by`, `unresolved` for an
  unreachable project's reference and for a declared absent project, error for
  an unknown key in an item-at-spec `capabilities.yaml`, nothing for an
  undelivered `new:` path, malformed YAML on a completed item reported by the
  file scan only, an invalid latest round warning and no line for an older
  one, `Planning doc:` error, an unparsable `item.yaml` error with another
  item's missing reference still reported, closing count on stderr), AC 14 (a
  dangling `relatesTo`; an unresolvable `Subject`), AC 7's first half (a clean
  fixture under `projects:` passes — the old key's refusal is Task 17). Jira
  bullets of AC 15 go to `tests/work/jira/test_jira_validate_remote.py`
  (records under `--remote`, none offline and no request to the fake; a passed
  check prints nothing and an unsampled move is one `warning`, exit 0). Rewrite
  or delete the `[path]`/`--no-recurse`/recursion cases in
  `tests/test_validate.py` and `tests/test_upstream_projects.py`.
- **Proof:** `pytest tests/test_validate*.py tests/test_upstream_projects.py tests/work/test_validate_work.py tests/work/jira/test_jira_validate_*.py -q`.

### Task 10: Validating one work item (Design 6.4; AC 24)

- **Modify `tcw/validate.py`**: `ValidationTarget` accepts `axis="work"`, with
  `ref` the folder and an optional `item: Item`. With it, run only the checks
  Design 6.4 lists: YAML and `tcw://` links over the item's own folder; the
  backend's offline check restricted to that folder; invalid latest rounds;
  and, when the stage is known (the `Item` is given, or filesystem mode reads
  `item.yaml`), the records check when not terminal and the reference check on
  `parent` and `blocked-by` within this project. Jira mode with no `Item`
  skips the last two and never opens a client. The docstring names which
  checks need the `Item`.
- **Tests**: `tests/test_validate_target.py` gains AC 24: a fixture item at spec
  with a broken `tcw://` link, an invalid latest review round and an unknown
  `capabilities.yaml` key gives one finding each and none for another item; a
  Jira-mode configuration with no `Item` gives no records finding, no
  `unresolved`, and the fake records no request; every value is a `Finding`.
- **Proof:** `pytest tests/test_validate_target.py -q`.

### Task 11: `tcw capabilities drift` (Design 7; AC 16)

- **Modify `tcw/work/gates.py`**: `drift_problems` returns
  `DriftProblem(kind, where, message)` (choice 18), `kind` one of `drift`,
  `ambiguous`, `unchecked`; a malformed `capabilities.yaml` is `unchecked` at
  the item's slug.
- **Modify `tcw/capabilities/cli.py` `_drift`**: `unreviewed: <path>: …` lines
  then the completed-work findings, all on stdout; nothing when clean; exit 1
  on any. With no work component: only unreviewed, and stderr says
  completed-work drift was not checked. In Jira mode the completed items come
  from `backend.list(Query(stages={completion stage}))` and each item's
  `<item>/capabilities.yaml` through the backend's layout; the unreviewed lines
  are printed before an `Unreachable` propagates to exit 5.
- **Tests**: rewrite `tests/work/test_drift_work.py` and update
  `tests/work/test_gates.py`-equivalents found with `grep -rln drift_problems
  tests`; new cases for AC 16: absent `x/y` declared `new` → `drift: x/y: …`
  and exit 1; a later `removed: [x/y]` clears it; `unreviewed: …`; no work
  component; Jira unreachable → 5 with the unreviewed lines printed first; no
  `Planning doc` read under `tcw/capabilities/` (static).
- **Proof:** `pytest tests/work/test_drift_work.py` and the gates tests.

### Task 12: `tcw init` and `tcw provision` (Design 1.7, 2, 8.3, 8.4; AC 8 `init`, 17 `init`, 18)

- **Modify `tcw/cli.py`**:
  - `run_init`: stdout empty; each written or created path on stderr
    (`wrote tcw-config.yaml`, `created docs/taxonomy/`, `wrote
    docs/taxonomy/.gitkeep`, …), from a list `fs.init` returns; unknown axis → 2
    listing the valid names; missing `--id` for a new project → 2 (choice 12);
    errors raised rather than printed.
  - `provision`: no `--refresh`; every line it prints goes to stderr,
    `--dry-run` included; any failure exits 1.
- **Modify `tcw/store/fs.py`**: `init` returns what it wrote and created;
  `FsStoreProvisioner.ensure_available` loses `refresh` and the fetch,
  checkout and merge that served it.
- **Modify `tests/work/test_git_write_scan.py`**: `FsStoreProvisioner`'s
  allowance shrinks to the verbs the remaining code uses.
- **Modify `tests/doc_allowance.py`**: `("tcw provision", "--refresh")`.
- **Tests**: `tests/test_store_provisioning.py` loses its `--refresh` cases and
  asserts stderr for its narration; new cases: `tcw provision --refresh` → 2; a
  declared store already present prints nothing on stdout and contacts
  nothing; `tcw init` prints nothing on stdout and names every written path;
  `tcw init nosuch` → 2. Update `tests/work/test_init_provision.py`,
  `tests/test_init_configured_tree_path.py`, `tests/test_config_edit_writers.py`.
- **Proof:** those files.

### Task 13: The `--help` standard (Design 5; AC 1, 4)

- **Create `tcw/cli_help.py`**: `command(sub, name, *, help, prints, writes,
  examples, description="")` builds a leaf parser with a raw-text formatter,
  a description ending in `Prints: …` and `Writes: …`, and an epilog of
  `  tcw …` example lines; `group(sub, name, help)` builds a group parser with
  a description.
- **Modify every parser** in `tcw/cli.py`, `tcw/projects_cli.py`,
  `tcw/taxonomy/cli.py`, `tcw/capabilities/cli.py`, `tcw/work/cli.py` to use
  it, with help on every positional and option (including `--priority`,
  `--effort`, `--complexity`, `--assignee`, `--parent`, `--blocked-by`,
  `--project`, `--stage`, `--to`, `--force`, `--reason`, `--dry-run`, `--json`,
  `--status`, `--namespace`) and choices shown. `tcw --help`'s epilog is the
  exit-code table and one sentence on stdout and stderr.
- **Tests**: new `tests/test_cli_help_standard.py`: AC 1 (the 42 leaf
  commands exactly, and none of the removed list) and AC 4 (every bullet,
  including that every example line parses through `build_parser()`); it
  absorbs `tests/test_cli_help_coverage.py`, which is deleted.
- **Proof:** `pytest tests/test_cli_help_standard.py tests/test_command_suggestions.py -q`.

### Task 14: The static guards: git words, prompts, quoting (Design 1.4, 9.1, 9.2; AC 5, 13)

- **Reword** every user-visible string under `tcw/` (not `tcw/serve/`) that a
  git-list word appears in, outside the exempt functions: today
  `tcw/cli.py` (the `init` help, removed by Task 13), `tcw/work/config.py:52-54`
  (the removed-key reasons), `tcw/work/jira/backend.py:463` and
  `tcw/work/jira/remote.py:498` ("may exist in another copy of this
  repository", Design 9.2), `tcw/work/open.py:158`, and whatever else the new
  test finds. `open.py:157` uses single quotes (choice 10).
- **Tests**: new `tests/test_static_guards.py`:
  - the git-word test of AC 5, with the exempt functions listed by module and
    name (`git_root`; `uncommitted_changes` and the delegation check that uses
    it in `tcw/work/open.py`; `_other_branch_warning`, whose sentence it
    matches; every function of `FsStoreProvisioner` and the provisioning
    functions of `tcw/cli.py`), failing when one no longer exists; mutation
    check: `"run git commit first"` added to a `tcw/taxonomy/` function fails it;
  - AC 13: no `.py` under `tcw/` other than `tcw/stdin.py` calls `input(` or
    reads `sys.stdin`;
  - the quoting rule over `tcw/work/open.py`'s messages.
- **Proof:** `pytest tests/test_static_guards.py -q`, and the files of every
  reworded message.

### Task 15: The contract test (Design 10; AC 8, 9, 10, 11, 12, 20, 26, 28)

- **Create `tests/test_cli_contract.py`**: a table with one row per leaf
  command (its argv in a fixture, its expected stdout shape, the paths it may
  write, its exit code), run as a subprocess (`python -m tcw.cli`) in a
  fixture project built by `tcw init --id fx` itself; the Jira rows in-process
  against TCW-71's fake (choice 1). Cases:
  - AC 8 and 9: every bullet, with the fixture's listing and file contents
    compared before and after each writing command against its stderr lines;
  - AC 10: every bullet, including the table-driven "no project here" case for
    every row except `init` and `procedure` (choice 3), and `--version`,
    `--help` and an argument that does not parse there;
  - AC 11, 12, 26 and 28 against the stub or the fake;
  - AC 20: a dummy subparser added in the test makes the coverage check fail.
- **Fix** in the command any deviation the test finds, in this commit, and
  list each in `outcome.md`.
- **Proof:** `pytest tests/test_cli_contract.py -q`.

### Task 16: The shell scenarios (Design 10; choice 17)

- **Rewrite** `tests/cli/scenarios/06-stdin-and-process-boundaries.md` (its
  entry points become `work new`, `work comment`, `taxonomy add`,
  `capabilities add`) and `13-release-integrity.md` (no 2.x names) to 3.0.
- **Delete** the other twelve: `01` (bootstrap, `<axis> init`: the contract
  test covers `init`, `--version`, `--help` and `path`), `02` and `03` (status
  folders and 2.x transitions), `04` (`stage gate`, `--directive`,
  `--transition`; stage prompts and hooks are in `tests/work`), `05` (docs:
  `tests/work/test_cli_config.py` and the contract test), `07` (inbox and
  `--initiative`), `08` (taxonomy and capabilities: the contract test), `09`
  (worktree merge-back, gone), `10` (cross-node epics, `reconcile`, gone),
  `11` (`scaffold`, gone), `12` (serve's 2.x routes; TCW-77 rewrites serve),
  `14` (writes outside a repository, reversed by Task 6 and covered by AC 17).
- **Modify `tests/cli/README.md`** to list the two that remain and say why.
- **Proof:** none in the suite; these are specifications with no scripts yet.

## Phase C — the renames

### Task 17: The `projects:` key (Design 9.3; AC 7)

- **Modify `tcw/store/project.py`, `tcw/store/base.py`, `tcw/store/fs.py`
  (`declared_connected_projects` becomes `declared_projects`),
  `tcw/work/jira/config.py`, `tcw/work/open.py`, `tcw/store/config_edit.py`**,
  and any other reader found by `grep -rn "connected-projects" tcw`: the key is
  `projects`, with the same `parent`, `children`, `upstream` entries and the
  optional `jira` block. A config holding `connected-projects` gets one graph
  error naming `docs/migration-guide-2.8-to-3.0.0.md` and the key `projects`.
- **Modify the tests**: every `connected-projects` in `tests/` becomes
  `projects` (`tests/work/projects.py`'s `connect`, `tests/nodeconfig.py`, and
  the 32 files `grep -rl` lists); one new case keeps the old key and asserts the
  error.
- **Modify `tests/doc_allowance.py`**: `connected-projects` in `REFUSED_KEYS`.
- **Tests**: AC 7: the old key makes `tcw validate` exit 1 naming the guide;
  the same graph under `projects:` passes; `tcw projects list` prints the
  current ID then the others.
- **Proof:** every file changed.

### Task 18: "Project" in place of "node" in the code (Design 9.3; AC 6)

- **Rename**, everywhere under `tcw/` except `tcw/serve/`, in code, strings,
  comments and docstrings: the project sense to "project" (`find_node_root` →
  `find_project_root`, `find_node` → `find_component_project`, `child_nodes` →
  `child_projects`, `parent_node` → `parent_project`, `descendant_nodes` →
  `descendant_projects`, `node_root` → `project_root`, `NODE_TARGET = "node"` →
  `PROJECT_TARGET = "project"` and its "node at …" text, and the rest); the
  tree sense to "entry" (`_load_node` → `_load_entry`, `_write_node` →
  `_write_entry`, `_node_texts` → `_entry_texts`, `_node_readable` →
  `_entry_readable`, `_node_reserved` → `_entry_reserved`); YAML parse-tree
  prose to "YAML node". The ADF comment at `tcw/work/jira/mapping.py:20` is
  reworded. `tcw/serve/` changes only the imported names it calls.
- **Modify the tests** that import a renamed name (`grep -rln` over `tests/`
  for each old name).
- **Tests**: new `tests/test_no_node.py`, AC 6, with the allow-list by module
  and function (`_unique_mapping` in `tcw/store/project.py`, `_no_dup_keys` in
  `tcw/store/fs.py`, the YAML functions of `tcw/store/config_edit.py`, and
  `text_document`, `_children`, `_inline_text`, `_block_text`,
  `document_text` in `tcw/work/jira/mapping.py`), failing when a listed
  function is missing or names none of the PyYAML classes, `construct_object`
  or a Jira document; and `TCW_NODE_ROOT` absent.
- **Proof:** `pytest tests/test_no_node.py` and every test file changed.

### Task 19: The ledger and taxonomy records (Capability changes; AC 21)

- **On the branch, in `docs/taxonomy/`**: `node` becomes `project`
  (Vocabulary); `connected-project-registry` becomes `project-registry`
  (Feature); every entry citing either is updated; the descriptions of the
  `changed` entries say "project".
- **On the branch, in `docs/capabilities/`**: the three `new` records written
  (`cli/rely-on-one-output-contract`, `cli/list-connected-projects`,
  `cli/validate-a-project`), each `Supported`; every `changed` record
  rewritten for the surface it describes; the three `removed` records deleted;
  `web/meta.yaml`'s `Feature` set to `local-web-app`; every surviving record
  whose path says "node" renamed (`grep -rliw node docs/capabilities/work`),
  and every `Subject: node` or `Feature: connected-project-registry` updated.
- **On `main`, in this item's folder**: `capabilities.yaml` with the
  declaration from the spec's Capability changes, plus the sweep's renamed
  paths found above.
- **Tests**: new `tests/test_ledger_3_0.py` (AC 21) over the repository's own
  ledger: each `new` path exists and is not `Missing`; each `removed` path and
  the two taxonomy entries are gone; no `meta.yaml` under `docs/capabilities`
  names `node` or `connected-project-registry` as a whole word.
- **Proof:** `pytest tests/test_ledger_3_0.py` and, with the released 2.8.1
  `tcw` from the branch checkout, `tcw validate` reporting no broken
  `tcw://` link or reference introduced by the renames.

### Task 20: Release notes and changelog (Design 12; AC 23)

- **Create** `docs/release-notes/upcoming/<this item>.md` and
  `docs/changelogs/upcoming/<this item>.md`, each starting with a `##`
  heading. They say what a 2.8 user notices (Design 12's list).
- **Proof:** `pytest tests/test_upcoming_entries.py -q`, then the closing
  `pytest --collect-only -q` with no errors.

## Documentation Sync

Each of this project's documentation entries, evaluated:

| Entry | Fires? | Where it is handled |
| --- | --- | --- |
| `README.md` [Public-API] | Yes: the public CLI surface changes | Deferred to TCW-75 (spec Non-goals; README is TCW-75's). The allowance lists what it may still name. |
| `docs/guide/jira.md` [Tracker-Change] | No: no tracker command or `work.jira` key changes here | — |
| `docs/guide/<topic>.md` [Guide-Topic-Change] | Yes: commands, `projects:`, what writes stage | Deferred to TCW-75 (spec Non-goals) |
| `docs/release-notes/upcoming/<slug>.md` [Public-API] | Yes | Task 20 |
| `docs/changelogs/upcoming/<slug>.md` [Any-Code-Change] | Yes | Task 20 |
| `skills/<component>/SKILL.md` [Skill-Driven-Component] | Yes: every component's CLI surface changes | Deferred to TCW-74 (spec Design 0, epic decision 3); the allowance keeps the surface test honest meanwhile |
| `skills/configure/references/<document>.md` [Configuration-Key-Change] | Yes: `connected-projects` becomes `projects` | Deferred to TCW-75, which owns `skills/configure/` (spec Design 0) |

## Verification

What the suite cannot check:

- **The installed command reads right.** With the private environment, run
  `tcw --help`, `tcw work --help`, `tcw taxonomy add --help` and
  `tcw capabilities set --help`, and read them for plain wording, the
  `Prints:`/`Writes:` lines and the exit-code table.
- **A short walk in a throwaway directory that is not a git repository**:
  `tcw init --id walk`, `printf 'Need X\n' | tcw work new "A b"`,
  `tcw work advance <slug>`, `echo hi | tcw work comment <slug>`,
  `tcw work show <slug>`, `tcw taxonomy add Widget`, `tcw capabilities add
  ns/do-a-thing`, `tcw validate`, `tcw projects list`, checking stdout and
  stderr by eye. Recorded in `outcome.md`.
- **This repository's own `tcw validate`** stays red until TCW-76 (spec
  Risks); it is not a gate here.

## Abstraction litmus test

Every operation this plan changes, against `docs/lifecycle/abstraction.md`:
the output helpers, the handler and the help standard are the CLI layer; the
`changed` list of written paths is a filesystem-adapter attribute, not a
`TaxonomyStore` or `CapabilitiesStore` operation; the exit classes and
`Finding` are abstract return and error types any store can produce;
`projects list` reads `ProjectRegistry`; drift and the one-item selector read
the backend's `list` and the shared layout; the `projects:` key and the
renames change no operation.

## Notes

- **Deferred to later children**: README, guides, `skills/configure/` (TCW-75);
  every other skill, the agents, prompts and `evals/` (TCW-74); the migration
  guide and its table (TCW-76); `config show`, `--mine`, `--assign-me` and their
  contract rows (TCW-72); serve's rewrite and its contract row (TCW-77).
- The `REMOVED_COMMANDS`, `REMOVED_FLAGS` and `REFUSED_KEYS` lists grow here
  and must be empty before 3.0.0 (TCW-76).
