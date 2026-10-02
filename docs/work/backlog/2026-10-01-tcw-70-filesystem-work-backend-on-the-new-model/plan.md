# Plan — Filesystem work backend on the new model, wired into `tcw work`

This plan follows the spec as revised after the 2026-10-02 review, plus one
correction made at the plan stage (the four extra capability records under
"Changed", committed just before this plan). Each task below is one commit, and
the suite is green after each one.

## Before the first task

**TCW-69 must be finished first.** This item is blocked by TCW-69, and every
task below imports TCW-69's modules (`tcw/work/model.py`, `layout.py`,
`backend.py`, `advance.py`, `gates.py`, `references.py`, `config.py`,
`tcw/errors.py`, `tcw/exit.py`) and extends its tests under `tests/work/`. None
of them exists on `main` today. Before Task 1, re-read TCW-69's finished code
against the names this plan uses, the spec's Risks say. Where a name or a
signature differs, TCW-69's code wins: fix the name in this plan in the
same commit as the first task that uses it, and say so in the implement round.

**Which source runs.** Work happens on the epic branch, in the virtual
environment TCW-69's plan sets up (`python -m venv .venv && .venv/bin/pip
install -e '.[dev]'`), with the checkout as the current directory. The `tcw` on
`PATH` runs `main`'s code and must not be used to test this branch.

**How the board is driven.** From the first edit to `tcw/` on, the board is
maintained by editing files (`CLAUDE.md`, "Exception"; spec Design 15.3). This
slice is the point after which the branch's own `tcw` cannot read this
repository at all (spec Design 8), so that stays true until TCW-76. Move this
item to `active` by hand (folder and `state.yaml`) before Task 1, and move its
Jira ticket, TCW-70, to In Progress by hand: the tracker sync is one of the
things this slice deletes (the epic's decision 7).

**How the suite stays green across the switch.** The 2.x work store refuses
to open a store that lacks its six status folders (`FsWorkStore._open_at`,
`tcw/store/fs.py:4502`). So the moment `init` stops creating them, every 2.x
code path fails at once, and the change to `init`, the new commands and the
rewired `validate`, `tcw://` references and `drift` have to land in one
commit. The plan keeps that commit (Task 10) as small as it can be:

- Tasks 1–3 remove what has no future (tests of deleted behavior, the moved
  Jira client, skips for later slices), with no behavior change.
- Tasks 4–9 add the new code **beside** the old code, each with its own
  tests. The new command module is written as `tcw/work/cli_next.py` and is
  not registered with `tcw` until Task 10.
- Task 10 switches over: it renames `cli_next.py` to `cli.py`, changes `init`,
  points every caller at the new code, and ports the tests that reached the
  old code at run time.
- Task 11 deletes the 2.x code nothing calls any more, and ports the tests
  that imported its names directly.
- Tasks 12–13 write the records and the documentation entries.

**When a test is ported.** A test of surviving behavior is rewritten in the
commit where what it depends on disappears: at Task 10 if it reaches the 2.x
store through `init`, the CLI or `FsWorkStore`; at Task 11 if it only imports
a 2.x name (`parse_lifecycle_policy`, `WorkItem`, `STAGE_IDS`). A ported test
stays in its file unless a new test under `tests/work/` already covers the same
case, in which case it is deleted and the implement round names the test that
covers it. The full fate of every test file is in the table at the end of this
plan.

**Test helpers.** New test files go under `tests/work/` (TCW-69's rule: no
`__init__.py`; import as `tests.work.<module>`). One shared helper module,
`tests/work/projects.py`, created in Task 4, builds fixture projects:
`make_project(tmp_path, project_id, *, config=None)` runs `git init`, writes
`tcw-config.yaml`, and creates the work folder. Until Task 10 it creates the
folder itself, because the 2.x `init` still writes status folders. Task 10
changes it to call the branch's `init` (spec Design 15.1). `connect(a, b,
relation)` adds a `connected-projects` entry, and `commit_all(root)` makes the
one commit a git-state comparison needs.

**Every new subprocess call passes `stdin=subprocess.DEVNULL`**, because
`tests/test_subprocess_stdin.py` checks every process `tcw/` starts.

## Task 1: Move the Jira HTTP client (spec Design 9)

- **Move**, with `git mv`, `tcw/tracker/jira.py` to
  `tcw/work/jira/client.py`, unchanged except for its docstring, which gains
  the note now in `tcw/tracker/__init__.py:9-11` (the client is the single
  home of Jira HTTP work). **Create** `tcw/work/jira/__init__.py` (empty).
- **Modify** every importer of `tcw.tracker.jira` to import
  `tcw.work.jira.client`: the other `tcw/tracker/*.py` modules,
  `tcw/work/cli.py`, and any other module `grep -rn "tracker.jira\|tracker import jira" tcw/`
  finds. The 2.x tracker keeps working through the new path until Task 11.
- **Move** `tests/tracker_fake.py` to `tests/work/jira/fake.py` and
  `tests/test_tracker_client.py` to `tests/work/jira/test_client.py`. In the
  moved test, replace `TrackerConfig` (`tests/test_tracker_client.py:26`,
  `:29-37`) with a small local dataclass `_Config` carrying the same attribute
  names, because the client reads its configuration only through attributes
  (`jira.py:115-124`) and `TrackerConfig` is deleted in Task 11.
- **Move** `test_a_response_of_the_wrong_shape_is_a_tracker_error` and
  `test_nulls_the_code_already_treats_as_absent_still_read` from
  `tests/test_tracker_hardening.py` into `tests/work/jira/test_client.py`;
  they test only the client's response handling.
- **Modify** every test importing `tests.tracker_fake` to import
  `tests.work.jira.fake`.
- **Proof:** `pytest tests/work/jira tests/test_tracker_*.py -q`, then the full
  suite, `pytest -q`.

## Task 2: Skip the tests a later slice rewrites (spec Design 9)

- **Modify** each of these to start with a module-level skip, placed before
  any import of a TCW name:
  `pytest.skip("<reason>", allow_module_level=True)`. The reason names the
  slice and says it removes the skip when it rewrites the file.
  - TCW-74: `tests/test_skill_flow.py`, `tests/test_prompt_fallback.py`,
    `tests/test_eval_coverage.py`, `tests/test_eval_files_changed.py`,
    `tests/test_eval_fixture.py`, `tests/test_eval_grading.py`,
    `tests/test_eval_runner.py`.
  - TCW-74: `tests/test_skill_lifecycle_parity.py`. The spec does not name it,
    but it checks skill text against `LIFECYCLE_STEPS` and the
    `stage gate`/`stage validate` wording, which is TCW-74's subject; the
    spec's rule for "any other test of a later slice's subject" applies.
- `tests/cli/scenarios/` holds only Markdown; pytest collects nothing there,
  so TCW-73's rewrite needs no marker.
- **Proof:** `pytest -q`; the skipped modules report as skipped, with their
  reasons, under `pytest -rs`.

## Task 3: Delete the tests of behavior this slice deletes (spec Design 9)

- **Delete** each test file the table at the end marks **Delete (T3)**, and,
  in each file marked **Split**, the test functions the table names as
  deleted.
- **Delete** the fixture folders only those tests read:
  `tests/fixtures/lifecycle_baseline/`, `tests/fixtures/tracker/` and
  `tests/fixtures/show_baseline/`.
- **Before deleting a file, check its importers:**
  `grep -rn "tests.<module>\|from tests.<module>" tests/`. Two files are known to
  supply helpers to a file that survives, so they are **not** deleted here but
  in Task 10, after their helpers move: `tests/test_epic_completable.py`
  (`mk_node`, `_partial_graph`, used by `tests/test_edit_refusal.py`) and
  `tests/test_cross_node_blocker_cycles.py` (used by
  `tests/test_damaged_state_on_edit.py`). If the grep finds another, defer
  that file the same way and record it in the implement round.
- The serve test files are not touched here; Task 9 handles them with the
  routes.
- **Proof:** `pytest -q`. Record in the implement round the number of tests
  collected before and after (`pytest --collect-only -q | tail -1`).

## Task 4: The filesystem backend (spec Design 3, 4, 5; AC 1, and the backend half of AC 3–8)

- **Create** `tcw/work/fs_backend.py` with:
  - `FsWorkBackend(project, work_path, config, user_name=None, *,
    report=None)`, implementing TCW-69's `WorkBackend` with
    `external_stages = frozenset()` and `inbox_items = True`. `report` is a
    callable taking one line of text, defaulting to printing on stderr. The
    adapter calls it for every file it writes, moves or removes (Design 4.4)
    and for each "not rewritten" mention a rename finds (Design 5). It is an
    adapter detail: the protocol does not change, and tests pass
    `list.append`.
  - `ITEM_FOLDER = re.compile(r"^\d{4}-\d{2}-\d{2}-[a-z0-9]+(-[a-z0-9]+)*$")`,
    and `is_item_folder(path)`: the name matches, is at most
    `model.FOLDER_LIMIT` characters, starts with a real date
    (`date.fromisoformat`), and holds `item.yaml` (3.1).
  - Reading and writing `item.yaml` as private functions: the key order of
    3.2.1; strict reading (3.2.3) raising `BackendError` naming the file and
    the key; a `stage` that is not an enabled flow or terminal stage read as
    `None` with the raw string kept; an absent `priority` read as `medium`;
    unregistered tags kept; bare `parent` and `blocked-by` entries read
    through `Slug.parse`. Writes go to a temporary file in the item folder
    and `os.replace` it; every write except `set_stage` writes back the raw
    `stage` string it read (3.2.2).
  - The eleven operations as in Design 3.3:
    - `create` validates through `validate_changes`, makes the folder named
      `<local date>-<title_words(title)>`, refuses an existing name with
      `Refused` naming it, writes `item.yaml` then the request, and on any
      failure after making the folder removes that folder with
      `shutil.rmtree`. Empty request text writes no request. The request
      path is `layout.document(slug, model.start_stage())`; the module holds
      no stage name.
    - `read`, `update` (checks only the tags the change adds), `set_stage`
      (writes `stage`, then the note as a comment; raises
      `MovedWithoutNote` when the comment cannot be written; returns the
      stage it reads back), `comment` (the `YYYYMMDDTHHMMSSZ` name; the next
      free second when taken; `UsageError` for blank text), `rename`
      (Design 5, below), `lookup` (always `None`), `read_request`,
      `read_comments` (only names matching the timestamp pattern;
      `BackendError` for one that is not UTF-8; no folder means none), and
      `current_user` (returns `user_name`; never raises).
    - `list` reads through `read_all`, raises `BackendError` naming every
      unreadable `item.yaml` when there is any, then applies TCW-69's `Query`
      rules in folder-name order. `Query.tags` matches when the item carries
      any given tag, both sides through `normalize_tag`.
  - `read_all(work_path, ...) -> tuple[list[Item], list[Unreadable]]`, a
    plain function: every item folder directly inside the work path, read
    one by one, with each unreadable one set aside as `Unreadable(path, key,
    message)`.
  - `rename(folder, title_words)`, the five steps of Design 5.3 in order:
    refuse an existing target (`Refused`); read every item and refuse
    (`BackendError`) when any is unreadable, before moving anything; one
    `os.rename`; rewrite each referencing `item.yaml` (`parent` and
    `blocked-by` naming the old slug in either written form) with the new
    slug in full and the raw `stage` kept; then search the text files under
    the work path for the old folder name and `report` each match as
    `path:line … not rewritten`. A failure after the move stops, lists the
    items not rewritten, and raises `BackendError`. The new-name checks of
    Design 5.1 (same date, words already in folder form, a suggestion built
    with `title_words`) raise `UsageError`.
  - `work_store_problems(work_path, registered_tags) -> list[Finding]`, the
    first five checks of Design 10.1 as one plain function: unreadable
    `item.yaml` (error, file and key); no-stage value (error, the value
    found); a directory that is not an item folder (error); a plain file
    other than a hidden one (warning); an unregistered tag (warning). Both
    "not part of a work store" messages end with "see
    `docs/migration-guide-2.8-to-3.0.0.md` for the work store layout", using
    TCW-69's `MIGRATION_GUIDE`. `Finding` is a small frozen dataclass
    (`level`, `path`, `key`, `message`) local to this module; TCW-73
    replaces it with its own type (spec 10.2).
- **Create** `tcw/work/record.py` with `item_record(item, items, layout) ->
  dict`, the record of Design 7.1 with exactly its keys (`slug`, `title`,
  `stage`, `created`, `priority`, `effort`, `complexity`, `tags`,
  `assignee`, `parent`, `blocked-by`, `blocks`, `children`, `path`,
  `untracked`); `blocks` from `blocks_of`, `children` from the `parent` of
  `items`. It is backend-neutral, so both backends and the viewer use it.
- **Create** `tests/work/projects.py` (see "Test helpers" above).
- **Create** `tests/work/test_backend_contract.py` from TCW-69's
  `tests/work/test_memory_backend.py`: every case that is not specific to the
  memory backend becomes a test parametrized over a `backend` fixture yielding
  `MemoryBackend` and `FsWorkBackend`. **Modify** `test_memory_backend.py` to
  keep only the memory-specific cases (the call log, the injected failures).
  The contract adds the AC 1 checks for `FsWorkBackend` (`untracked == ()`,
  `priority` never `None`) and `current_user` for both backends, built with
  and without a name. TCW-71 adds a third parameter.
- **Create** `tests/work/test_fs_backend.py` for what only the filesystem
  shows, through the backend, with no CLI:
  - AC 2's file content (`item.yaml` exactly `title`, `stage`, `priority`;
    no `created`, `slug`, `history`; no `request/` for no text), the refusal
    of an existing name, and `untitled`;
  - AC 3 through `create` and `read_request` (text verbatim, `""` writes
    nothing, an inbox item keeps its text in the same place, no `intake.md`);
  - AC 4's strict reading cases, no-stage reading, raw `stage` kept by
    `update` and by a rename's rewrite, and the tag rule for removed
    registry tags;
  - AC 6 through `comment` and `read_comments` with a fixed clock (two in one
    second, the newest two of three, `notes.txt` ignored);
  - AC 7's comment-cannot-be-written case through `set_stage` (`comments`
    made a plain file → `MovedWithoutNote`, `item.yaml` already changed);
  - AC 8 through `rename`;
  - `list` failing on one unreadable item and naming it, and `read_all`
    returning the rest;
  - atomic replacement: monkeypatch `os.replace` to raise after the temporary
    file is written, and assert the old `item.yaml` is intact (spec
    "Coverage");
  - `create` removing its folder when the request write fails;
  - each `work_store_problems` finding, including `inbox/` naming the
    migration guide and a leftover `dod.yaml` as a warning.
- **Proof:** `pytest tests/work -q`.

## Task 5: Opening a backend and delegation (spec Design 2, 3.5, 6; the library half of AC 9 and AC 20)

- **Create** `tcw/work/open.py` with:
  - `open_backend(project_root) -> WorkBackend`: reads the tracked
    `tcw-config.yaml` with `load_config`, parses `work` with TCW-69's
    `parse_work_config`, raises `BackendError` naming every problem (and,
    for a removed key, `MIGRATION_GUIDE`, which the parser already puts in
    the message), resolves the work path with `resolve_store` (3.4), and
    returns `FsWorkBackend` for `filesystem`. For `jira` it raises
    `BackendError("… the Jira backend arrives with TCW-71")`.
  - `open_project(project_id, here) -> WorkBackend`, through
    `FsProjectRegistry`: `NotFound` (exit 4) when no declaration names the ID,
    `Unreachable` (exit 5) when it is declared but not on this machine,
    otherwise `open_backend` of its root.
  - `delegate(project_id, title, request, priority, *, here) -> str` and
    `open_for_update(project_id, here) -> WorkBackend`, both checking Design
    6.3's five conditions in order through one private `_check_target`, and
    raising `Refused` naming the first that fails. For a declared project
    whose checkout is absent and whose entry carries a `jira` block,
    `delegate` raises `BackendError("Jira delegation arrives with the Jira
    backend")` and `open_for_update` raises `Refused`. On success `delegate`
    creates the item at `model.inbox_stage()` with only `priority`, reports
    each file written as uncommitted in the target's repository, and returns
    the full slug.
  - `uncommitted_changes(path) -> list[str]`: runs
    `git --no-optional-locks status --porcelain --untracked-files=all -- <path>`
    in the repository that holds `path`, and raises `Refused` with the "not in
    a git repository" message of 6.3 when there is none. The refusal message
    for changes is exactly the one 6.3 fixes.
  - "The work store is present" (3.5) is `work_path.is_dir()`; this module
    asks that question directly. The 2.x `_has_work_store` and
    `_is_store_layout` change in Task 10.
- **Modify** `tcw/store/project.py` `read_only_reason` (around line 364) so
  that an ID the registry has not loaded still answers: when
  `self._upstream_reader(project_id)` finds a declarer, return the existing
  upstream message; otherwise keep returning `None`. This lets an absent
  upstream project be refused before the `jira` branch (spec 6.2).
- **Create** `tests/work/test_open.py`, using `make_project` and `connect`:
  - AC 20 at the library level: a config with `work.tracker` makes
    `open_backend` raise `BackendError` naming `work.tracker` and the guide;
  - `jira` as `work.backend` raises `BackendError`;
  - `open_project`: exit 4 for an undeclared ID, exit 5 for a declared,
    absent one;
  - AC 9 through `delegate` and `open_for_update`: the success case (inbox,
    `priority: high`, reported files, target `HEAD` and index unchanged),
    every refusal in turn with nothing written in Q, the upstream refusal
    both with R's checkout present and absent with a `jira` block, the
    Jira-block branch for each function, and the index modification time
    unchanged by a refused delegation;
  - `uncommitted_changes` for a clean store, an untracked file, an ignored
    file (not counted), and a store outside git.
- **Proof:** `pytest tests/work tests/test_upstream_projects.py
  tests/test_project_registry.py -q`.

## Task 6: Prompt composition on the 3.0 configuration (spec Design 7.1, 7.2, 8; the library half of AC 21)

- **Modify** TCW-69's `tcw/work/advance.py` to make its local hook
  environment builder and its `when:` matcher public as `hook_env` and
  `binding_applies`, unchanged, so composition and `advance` share one
  definition. (If TCW-69 already made them public, nothing changes.)
- **Modify** `tcw/work/resolve.py`, **adding** beside the 2.x functions,
  which stay until Task 11:
  - `packaged_text(kind, name) -> str`, reading `tcw/work/prompts/<name>.md`
    or `tcw/work/procedures/<name>.md` from the package, and raising
    `BackendError` naming the missing file;
  - `substitute_request(text, request)`, the port of `substitute_body`
    (`resolve.py:333-384`) for `{{tcw:request}}…{{/tcw:request}}`, with the
    span's inner text as the fallback. `{{tcw:body}}` is not touched;
  - `generate_payload(record, request, role, kind, hook_id, phase) -> tuple[str,
    bool]`, giving the one JSON object of 7.1 (`schema`, `item`, `request`,
    `hook`) with the request capped as `hook_payload` caps `body` today;
  - `compose(bindings, *, role, hook_id, item, record, request, project_root,
    config, documentation, execute) -> Resolution`, the 3.0 counterpart of
    `_compose`: each binding filtered by `binding_applies`, then `blob`,
    `skill`, `file` (through the existing `_read_file` confinement),
    `builtin` (through `packaged_text`) and `generate` (through
    `run_generate`, with `hook_env` plus `TCW_HOOK_ROLE`, `TCW_HOOK_KIND`,
    `TCW_HOOK_ID`, `TCW_HOOK_PHASE`, run in `project_root`), then
    `substitute_documentation` and `substitute_request`;
  - `stage_prompt(config, stage, ...)`, composing exactly
    `config.stages[stage].prompt`, which is `[builtin: true]` when the stage
    sets no `prompt` key and nothing for an explicit empty list (7.2), and
    `procedure_prompt(config, procedure_id, ...)`;
  - `stage_header(stage, target)`, the header naming `tcw work advance
    <slug> --dry-run` in place of `stage gate`.
- **Create** `tests/work/test_compose.py`, covering AC 21 without the CLI:
  the four prompt-list cases; request substitution and the fallback; no
  `{{tcw:request}}` left in the output; `review` failing with `BackendError`
  naming `tcw/work/prompts/review.md`; a `generate` script that saves its
  stdin, `$PWD` and environment, checked for the exact keys, the project
  root, the full `TCW_SLUG` and `TCW_HOOK_ROLE`; and a long request arriving
  cut with `body_truncated` true. It also covers `when:` filtering by tags.
- **Proof:** `pytest tests/work tests/test_generate_hook.py -q`.

## Task 7: The rewired checks, written beside the old ones (spec Design 10, 12.1; the library half of AC 15–17)

Each function below is added and tested here and called by nothing until
Task 10.

- **Modify** `tcw/validate.py`, adding `_work_findings(project_root,
  registry) -> list[Finding]`. For a filesystem-mode project it opens the
  backend with `open_backend`, then returns: `work_store_problems`; TCW-69's
  `reference_problems` over every readable item, with a `resolve` callback
  answering `found`, `missing` (also for `NotFound` from `open_project`) or
  `unresolved` (for `Unreachable`); `stage_problems`; and
  `records_problems(finished=False)` for each readable unfinished item, with
  `ledger_reader` and `<item>/capabilities.yaml`. A note naming the files
  whose references could not be checked is returned once, for stderr (R16).
  Also add `_shared_work_paths(registry) -> list[str]`, the same-work-path
  check rebuilt on `resolve_store`, for filesystem-mode projects only.
- **Modify** `tcw/refs.py`, adding `_resolve_work(node_root, namespace, ref)`:
  `open_backend` or `open_project`, then `read`; found at any stage is OK;
  `NotFound` is missing; `Unreachable` is unresolved.
- **Modify** `tcw/capabilities/cli.py`, adding `_completed_but_missing(node,
  st)`: the readable items at `model.completion_stage()`, through TCW-69's
  `drift_problems`, plus one finding per unreadable `item.yaml`. It never
  reads a `Planning doc` field.
- **Create** `tests/work/test_validate_work.py`,
  `tests/work/test_refs_work.py` and `tests/work/test_drift_work.py`, calling
  these functions on `make_project` fixtures with hand-written item folders.
  They cover AC 15's cases (each fault; three warnings and no error; the
  unresolved and missing references; `inbox/` naming the guide; an
  `implement` item with a bad `capabilities.yaml`; one unreadable item not
  hiding the other two findings; the same work path naming both IDs and the
  path), AC 16 and AC 17. Assertions check that each finding names its file
  and key, not the layout of the line.
- **Proof:** `pytest tests/work -q`.

## Task 8: The new `tcw work` item commands, not yet registered (spec Design 1, 6.1, 7; the in-process half of AC 2–9 and 11)

- **Create** `tcw/work/cli_next.py`, which becomes `tcw/work/cli.py` in
  Task 10. It exposes the same module interface `tcw/cli.py` expects of a
  command group (`NAME = "work"`, `SUBCOMMANDS`, `DEFAULT_SUBCOMMAND`,
  `add_subparser`; `tcw/cli.py:38`, `:529-530`). This task adds:
  - `resolve_item(arg, here) -> tuple[Slug, WorkBackend]`: `Slug.parse`
    against the current project, exact match only; another project's slug
    opens that project with `open_project`.
  - The commands, with these flags (TCW-73's surface table, minus
    `--assign-me`, and with `--tag` parsed as 2.8 parses it,
    `tcw/work/cli.py:78-105`, `:5016-5017`: the `--tags` alias, `extend`,
    comma-separated values):
    - `new <title> [--project <id>] [--stage <first flow stage>] [--priority]
      [--effort] [--complexity] [--tag]… [--assignee] [--parent]
      [--blocked-by]…`, reading request text with `read_piped_stdin`. With
      `--project`, any property flag other than `--priority` is a usage
      error naming the flag.
    - `list [--stage]… [--tag]… [--parent] [--assignee] [--all] [--json]`,
      keeping the unregistered-tag warning of `tcw/work/cli.py:1209-1213`.
    - `show <slug> [--json]`: the record, with `blocks` and `children` from
      `read_all`'s readable items and one stderr warning naming the
      unreadable ones. Plain `show` prints one `key: value` line per field.
    - `path [<slug> [<stage> [--next | --handoff]]]`: TCW-69's
      `layout.path`; with no slug, the work store folder.
    - `edit <slug> [--title] [--priority] [--effort] [--complexity] [--tag]…
      [--untag]… [--assignee] [--parent] [--blocked-by]… [--unblocked-by]…
      [--blocks]…`. `--untag` keeps the `--untags` alias. An empty value
      clears an optional property. `--blocks` into another project goes
      through `open_for_update`; every other write to another project's item
      is refused (exit 3).
    - `advance <slug> [--to] [--force --reason] [--dry-run]` and
      `discard <slug> --reason`, through TCW-69's `advance` and `discard`,
      printing the outcome's stage (nothing for a refused dry run) and
      returning its code.
    - `comment <slug>`, text from stdin.
    - `rename <slug> <new name>`, printing the new slug.
  - `run(argv) -> int` for tests: a parser holding only this group, with the
    `TcwError` handling Task 10 adds to `tcw/cli.py`'s `main` (print
    `tcw: <message>` on stderr, return `error.code`).
  - Every stdout line is a full slug or a stage, as the spec's table says;
    every narrative line goes to stderr.
- **Create** `tests/work/test_cli_items.py`, using a helper
  `tcw(argv, cwd, stdin="")` that calls `cli_next.run` with captured streams
  (Task 10 points it at `tcw.cli.main`). It covers, through the commands:
  AC 2 (stdout, refusal of a second same-day `new`, `untitled`), AC 3, AC 4
  (each strict-reading exit 1 naming the key; `stage: verify` and a disabled
  `plan` reading as no stage, `show --json` `null`, bare `advance` exit 3,
  forced `advance` moving it; the R12 writes; `show` with another item
  unreadable), AC 5 (default listing, `--stage`, `--all`, `--stage inbox
  --all` exit 2, `notes/` and `README.md` ignored, an unreadable item exit 1,
  every tag-filter case), AC 6, AC 7 (the forced move writing one comment;
  exit 6 with the trace message; the `pre` hook recording `$PWD` and
  `$TCW_SLUG` when run from a subfolder), AC 8 (including the second
  project's item left alone and the exit codes), and AC 9 through
  `new --project` and `edit --blocks` (including `--tag` with `--project`
  exiting 2, and `show` exiting 5 and 4).
- **Proof:** `pytest tests/work -q`.

## Task 9: `tcw serve` keeps two stub routes (spec Design 12.2; AC 19)

This task is independent of the backend, and lands before the switch so that
Task 10 does not also carry it.

- **Modify** `tcw/serve/__init__.py`:
  - delete every `/api/work…` handler branch in `_get`, `_post`, `_patch`,
    `_put` and `_delete` (lines 650-886, 953-1113, 1265-1321, 1401-1542,
    1543-1600 as of `2b3de62a`), the two open handlers (`_handle_open` at 1603,
    `_handle_plan_stage_open` at 1644), `_open_locator` and its `subprocess`
    use, `_strict_refuses`, `_board`, the work-only helpers, and the
    work-only imports (lines 20-30, 228, 241, 273, 1063);
  - add, at the top of `_get`'s work branch: `GET /api/work` → 200 `[]`,
    `GET /api/work/tags` → 200 `[]`, and any other `/api/work…` request
    (every method) → 404.
- **Modify** `tcw/validate.py`: `ValidationTarget.axis` loses `"work"`, and
  `_target_roots` raises `ValueError` for an axis it does not handle.
- **Modify** `tests/conftest.py`: remove the desktop-opener half of
  `_no_desktop_opener` and the `stub_desktop_opener` fixture, which patch
  `tcw.serve.subprocess`; keep the other autouse fixtures. Reword the comment
  that mentions `tcw work start`.
- **Modify** the serve tests as the table at the end says:
  `tests/test_serve.py`, `tests/test_serve_write.py` (the CSRF,
  oversized-body and malformed-JSON tests move to a taxonomy route),
  `tests/test_serve_resolve.py`, `tests/test_validate_target.py`. **Delete**
  `tests/test_serve_descendants.py`, `tests/test_serve_duplicate_slug.py`,
  `tests/test_serve_projection.py`. **Add** to `tests/test_serve.py` the AC 19
  route checks.
- **Modify** `web/e2e/parity.spec.ts`: delete the work-only tests (at lines
  181, 212, 244, 454, 528, 632, 687 and 704 as of `2b3de62a`) and the setup steps that
  create a work item; the setup still polls `/api/work`, which now answers
  `[]`. Adjust the mixed tests at 95 and 410 to expect an empty board, and
  regenerate only the snapshots those two change.
- **Not changed:** anything under `web/client/src` or `tcw/serve/dist`.
- **Proof:** `pytest tests/test_serve*.py tests/test_validate_target.py -q`,
  then `pytest -q`; `git diff --stat 2b3de62a -- web/client/src tcw/serve/dist`
  is empty; the Playwright suite run by hand (see Verification).

## Task 10: Switch `tcw work`, `init`, `validate`, references and drift to the 3.0 model (spec Design 1, 3.5, 7, 8, 10, 11, 12.1, 14; AC 2, 10, 11, 15–18, 20, 21, 22)

This is the one large commit, for the reason given in "How the suite stays
green". Everything it switches to was written and tested in Tasks 4–8, so
this task changes callers and tests, and adds no new logic except the
commands of the first bullet below.

- **Finish `tcw/work/cli_next.py`** with the remaining commands, each
  through `open_backend` and TCW-69's configuration:
  - `stage prompt <stage> [<slug>] [--no-exec]`, through `stage_prompt` and
    `stage_header`; `stage` has no other subcommand, and the hidden 2.x
    forms (`_stage_removed_form`) go.
  - `procedure prompt <id> [<slug>] [--no-exec]`, through
    `procedure_prompt`. Outside any project it still prints the packaged
    procedure, as `tcw/work/cli.py:2264-2270` does today.
  - `lifecycle [<slug>] [--json] [--stage <s>] [--phase pre|prompt|post]
    [--directive]`: the enabled stage table with each stage's `prompt`,
    `pre` and `post` bindings. **Removed:** `--transition` and the
    transition path of `--directive` (`tcw/work/cli.py:2577-2632`); `--phase
    post` now applies to a stage.
  - `docs [--json]`, from `config.documentation`.
  - `tags list | add | rm`: `list` from `config.tags`; `add` and `rm` edit
    `work.tags` with `config_edit.SetList` and write the file with
    `_atomic_write_all`, unstaged, inside or outside a git repository
    (spec Design 7, R10).
  - `nodes`, copied from `tcw/work/cli.py:293` unchanged.
  - `init [--id] [--path]`, calling `tcw.cli.run_init`, as today.
- **Rename** `tcw/work/cli_next.py` to `tcw/work/cli.py`, replacing the 2.x
  module. **Modify** `tcw/cli.py`: `main` catches `TcwError` and returns its
  `code` after printing `tcw: <message>` on stderr; `FsWorkStore` leaves its
  imports.
- **Modify** `tcw/store/fs.py`:
  - `init` (1327-1572): the work component makes the work path and a
    `.gitkeep`, and nothing else; the status folders (1468-1469), the
    gitignore probe (1516-1525) and the ignore rules (1553-1571) go; the
    `--work-path` relocation check (1387-1432) refuses when the old store
    holds any item folder (`is_item_folder`).
  - `_has_work_store` (546-562) and the work branch of `_is_store_layout`
    (3978-3979), and `FsStoreProvisioner._require_store_layout`'s status
    list (4306-4309), answer "the work path is a directory" (3.5).
  - `find_node`'s `component == "work"` shortcut (357) uses the same test.
  - `OWNED_YAML_NAMES` (1622-1624) becomes `meta.yaml` and `item.yaml`.
- **Modify** `tcw/validate.py`: `validate` calls `_work_findings` and
  `_shared_work_paths` in place of `_open_sidecar_problems`, the retention
  and tracker checks and the work store's `check()` (lines 268-295,
  343-351, 365-385, 452-456); `_scan_roots`, `_claims_work` and
  `_components_to_check` find the work path through `resolve_store` rather
  than `FsWorkStore`. Warnings print as `warning: …` and unresolved
  references as `unresolved: …` on stderr and do not count toward the exit
  code (`tcw/cli.py:463-469`); errors keep exit 1.
- **Modify** `tcw/refs.py`: the work branch (132-169) calls `_resolve_work`.
- **Modify** `tcw/capabilities/cli.py`: `_drift` calls
  `_completed_but_missing` in place of `_shipped_but_missing` (200-254),
  which is deleted.
- **Modify** the packaged prompts `tcw/work/prompts/spec.md:6` and
  `tcw/work/prompts/plan.md:6`: rename `{{tcw:body}}`/`{{/tcw:body}}` to
  `{{tcw:request}}`/`{{/tcw:request}}`. Nothing else in them changes.
- **Modify** `tcw/cli_suggest.py`: the docstring and comments at lines 4, 12,
  17-18 and 41, and the examples at 125-127, name surviving commands
  (`tcw work show`, `tcw work tags list`) or are removed; the mechanism stays.
- **Documentation allowance** (spec Design 14):
  - **Create** `tests/doc_allowance.py` with two lists:
    `REMOVED_COMMANDS` (`tcw work start`, `submit`, `rework`, `complete`,
    `drop`, `delete`, `inbox`, `tracker`, `tombstone`, `reconcile`,
    `delegate`, `escalate`, `scaffold`, `stage gate`, `stage validate`) and
    `REFUSED_KEYS` (`work.lifecycle`, `work.tracker`, `work.retain`,
    `work.auto-commit-transitions`, `work.publish-transitions`,
    `work.trunk-branch`), each with a comment saying which slices shrink it
    and that TCW-76 requires it empty before 3.0.0.
  - **Modify** `tests/test_documented_cli_surface.py`: a backtick span or
    fenced line whose command starts with an entry of `REMOVED_COMMANDS` is
    skipped in `test_documented_verbs_and_flags_exist` (line 243);
    `DOCUMENTED_VERBS` (261-262) loses `tcw work stage gate`,
    `tcw work scaffold` and `tcw work tracker`.
  - The test does not check configuration keys today. So that the key list
    means something, **add** `test_documents_name_no_refused_key`: it scans
    the same `DOC_FILES` for `work.<key>` spellings of the keys TCW-69's
    parser removes, and fails on any key not in `REFUSED_KEYS`. (All six
    are named somewhere today, so it passes with the full list.)
  - **Add** the two guard tests: every `REMOVED_COMMANDS` entry is absent
    from the CLI's `--help` tree, and every `REFUSED_KEYS` entry is refused
    by `parse_work_config`. Mutation-check each by adding `tcw work list` to
    the first list and `work.tags` to the second.
- **Tests:**
  - Point `tests/work/test_cli_items.py`'s helper at `tcw.cli.main`, and
    `tests/work/projects.py`'s `make_project` at the branch's `init`.
  - **Create** `tests/work/test_cli_installed.py` for the **(installed)**
    criteria: a subprocess running `sys.executable -c` with this checkout first
    on `sys.path`, calling `tcw.cli.main`, as
    `tests/test_documented_cli_surface.py:145-148` does; stdin
    `subprocess.DEVNULL` unless text is piped. It covers AC 2's first line
    and AC 11.
  - **Create** `tests/work/test_cli_config.py`: AC 20 through `tcw work list`
    (exit 1 naming `work.tracker` and the guide), AC 21 through
    `tcw work stage prompt` (the four list cases, request substitution, no
    removed command named in the output, `review` exiting 1), and `lifecycle`
    listing the enabled stages with their bindings.
  - **Create** `tests/work/test_removed_commands.py`: AC 10, each removed
    command exiting 2 with the parser's unknown-command message and writing
    nothing.
  - **Create** `tests/work/test_init_provision.py`: AC 18.
  - Extend `tests/work/test_validate_work.py`,
    `tests/work/test_refs_work.py` and `tests/work/test_drift_work.py` with
    one case each through the commands (`tcw validate`, a `tcw://W/<folder>`
    link in a capability description, `tcw capabilities drift`), reading
    stdout and stderr together.
  - **Port** every test the table marks **Port (T10)** or **Split** with a
    T10 port, and **delete** `tests/test_epic_completable.py` and
    `tests/test_cross_node_blocker_cycles.py` after moving what
    `tests/test_edit_refusal.py` and `tests/test_damaged_state_on_edit.py`
    need into `tests/work/projects.py`. Re-capture
    `tests/fixtures/non_git_reads/work-list.txt`, `work-nodes.txt` and
    `validate.txt`, and read each diff before committing it.
- **Proof:** `pytest -q`, bare, as CI runs it.

## Task 11: Delete the 2.x work code (spec Design 9; AC 10, 12, 13, 14)

- **Delete** from `tcw/store/fs.py` (line numbers as of `2b3de62a`; re-read
  before deleting, since Task 10 shifted them):
  - `FsWorkStore` (4419 to the end of the file) and `STORE_LAYOUT` (3895);
  - `_git_error` (155-159); the work topology helpers that only
    `tcw/work/recursion.py` used (`nearest_work_ancestor`, `descendant_nodes`
    and any other with no remaining caller; `child_nodes`, `parent_node`,
    `registered_parent`, `registered_children`, `unreachable_parent`,
    `unreachable_children` and `registered_project_id` **stay**, because
    `tcw work nodes` uses them);
  - `resolve_qualified_work_ref`, `qualified_work_ref_read_only`,
    `resolve_qualified_work_ref_for_write`, `qualified_work_ref_problem`
    (595-737);
  - `git_mv`, `WORKTREES_DIR`, `_Moved`, `git_commit`,
    `_has_committable_changes`, `git_commit_result`, `git_current_branch`,
    `ensure_ignored` and the worktree and merge helpers (850-1305),
    `RESOLVED_IGNORE_COMMENT` and `resolved_ignore_rules` (1308-1324),
    `dump_yaml` and `_is_under` (1693-1702), and `FsTreeStore._mv`
    (2393-2395);
  - from `COMPONENTS` and `STORE_CLASSES` (74-104), the `FsWorkStore` entry.
    `"work"` stays a component name for `init` and `provision`; their callers
    (`tcw/cli.py`, `tcw/validate.py` `_tree_roots`) handle it without a
    store class;
  - `_warn_hidden`'s `RESOLVED_STATUSES` case (764).
- **Delete** from `tcw/store/base.py` every range the map tags as work-only:
  `SidecarError`; the sidecar limits and `declared_capabilities`; the
  tracker binding types (403-658); the work resources (768-819); the status,
  resolution and level tables (989-1056); `read_tags`, `frontmatter_end`,
  `body_title`; `STAGE_IDS`, `TRANSITION_IDS`, `WORK_TYPES`, `Condition`,
  `TransitionBindings`; the tracker configuration (1255-2008);
  `StageBindings`, `LifecyclePolicy`, the lifecycle step tables and next-step
  texts (2111-2399); `rename_slug`, `start_next_stage`; the 2.x binding
  parser (`_parse_condition`, `_parse_binding`, `_parse_binding_list`,
  2459-2628) and `_check_artifact_list`, `_empty_prompt`, `_parse_stage`;
  `parse_retention`, `parse_lifecycle_policy`, `parse_procedures`; `DEFAULT_DOD`,
  `WORK_ARTIFACTS`, `BODY_ORDER`, `WORK_SIDECARS`; and 3145 to the end
  (`WorkItem`, `Tombstone`, `WorkStore` and their errors). **Kept:**
  `normalize_tag`, `PROCEDURE_IDS`, `DEFAULT_OUTPUT_CAP`, `Binding` (the
  type `run_bindings` reads), `DocEntry`, `parse_documentation_entries`,
  `slugify`, `_UNSET`, `MultipleMatch` (caught at `tcw/cli.py:554`, and still
  raised by tree stores) and every taxonomy, capabilities, registry and
  provisioning name. Because `base.py` survives, the three helpers TCW-69's
  plan lists stay where they are (spec Design 8: they move only "if it is
  cut down" to nothing). Where a name the map tags as work-only turns out
  to have a surviving caller, keep it and record why in the implement round.
- **Delete** the package `tcw/tracker/`, and `tcw/work/recursion.py`,
  `tcw/work/projection.py`, `tcw/work/templates.py`, `tcw/harness.py`.
- **Modify** `tcw/work/hooks.py` to keep only `run_bindings` and what it
  needs; `hook_env`, `run_pre` and `run_post` go.
- **Modify** `tcw/work/resolve.py` to delete the 2.x functions (`Builtins`,
  `select`, `hook_payload`, `_hook_env`, `_resolve_one`, `resolved_body`,
  `substitute_body`, `bookend`, `resolve_prompts`, `resolve_procedure`,
  `_compose`, `resolve_artifact`). `load_builtins` stays, rebuilt on
  `packaged_text` over the stage names in TCW-69's table that have a
  packaged file, so `load_builtins().stage_prompts["implement"]` and
  `.procedures` keep working for `tests/test_falsification_rule.py` and
  `tests/test_shipped_procedures.py`.
- **Modify** `tcw/store/project.py`: `RESERVED_PROJECT_IDS` is
  `{"t", "c", "w", "local"}` and the `WORK_STATUSES` import goes.
- **Tests:**
  - **Port** every test the table marks **Port (T11)**.
  - **Create** `tests/work/test_git_state_unchanged.py` (AC 12, behavior): the
    commands of AC 12 across P and Q, comparing `git rev-parse HEAD`,
    `git for-each-ref`, `git ls-files --stage` and
    `git diff --cached --name-only` before and after; and `tags add x` /
    `tags rm x` in a project outside git exiting 0 and changing the file.
  - **Create** `tests/work/test_git_write_scan.py` (AC 12, the scan): an `ast`
    walk of `tcw/work/`, `tcw/validate.py`, `tcw/refs.py`,
    `tcw/capabilities/cli.py` and `tcw/store/`, finding each list or tuple
    literal whose first element is `"git"`, skipping `-C <path>` pairs and
    options starting with `-`, and failing on a writing verb. Allowances: the
    class `FsStoreProvisioner` for `clone`, `checkout`, `fetch`; and, until
    TCW-73, `git_stage`, `git_rm` and their callers in the taxonomy and
    capabilities store classes for `add` and `rm`, named by function. Each
    allowance names the enclosing class or function, found from the `ast`
    parents, never a file.
  - **Create** `tests/work/test_no_2x_names.py` (AC 13): no `.py` file under
    `tcw/` contains the strings of AC 13, `tcw/harness.py` does not exist,
    and `import tcw.tracker` raises `ModuleNotFoundError` (AC 10).
  - **Modify** TCW-69's `tests/work/test_model_guards.py` (AC 14): the
    stage-literal scan also covers `tcw/work/fs_backend.py`,
    `tcw/work/open.py`, `tcw/work/record.py` and `tcw/work/cli.py`.
    (`record.py` is this plan's module; the spec's rule covers it in spirit.)
  - **Mutation checks**, by hand, each reverted after it goes red and the
    reason is read: `["git", "-C", str(root), "add", "x"]` in
    `tcw/work/open.py`; the same call in a function of `tcw/store/fs.py`
    outside `FsStoreProvisioner`; `"request/request.md"` in
    `tcw/work/fs_backend.py`; `"graveyard.yaml"` in `tcw/validate.py`.
    Record the results in the implement round.
- **Proof:** `pytest -q`; `python -c "import tcw.cli, tcw.serve, tcw.validate,
  tcw.refs, tcw.capabilities.cli"`; and
  `grep -rn "FsWorkStore\|WORK_STATUSES\|tcw.tracker" tcw/` prints nothing.

## Task 12: Capability and taxonomy records (spec "Capability changes")

The `tcw capabilities` and `tcw taxonomy` commands are in this tree but the
branch's `tcw` refuses this repository's 2.x config, so the records are written
by editing files. Each record is a folder with `meta.yaml` (`id`, `name`,
`Status`, `Subject`) and `description.md`.

- **Delete** the 23 folders under `docs/capabilities/work/` that the spec
  lists as Removed.
- **Create** `docs/capabilities/work/advance-a-work-item/`,
  `comment-on-a-work-item/` and
  `delegate-a-work-item-to-another-project/`, each with a new `cap-` id of six
  lowercase hex digits that `grep -rn "id: cap-<hex>" docs/capabilities`
  shows is unused, `Status: Supported`, `Subject: [work-item]`, and no
  `Planning doc` field. The descriptions say what the spec's table says,
  in the first person, as the existing records do.
- **Modify** the 34 changed records: the 21 under `work/` and the 13
  elsewhere, each for the reason the spec gives. Every `tcw://C/work/…`
  link to a removed record is removed or pointed at its replacement
  (`advance-a-work-item` for start/submit/rework/complete,
  `delegate-a-work-item-to-another-project` for delegate/escalate).
- **Taxonomy:** **create** `docs/taxonomy/work-item/round/`, `handoff/` and
  `comment/` (`kind: Vocabulary`); **modify** `work-item`,
  `work-item/transition`, `work-item/lifecycle-stage`,
  `work-item/lifecycle-hook`, the features `work-inbox` and
  `configurable-work-lifecycle`, and, only to drop references to removed
  terms, `configure-skill`, `extras-triage-issues-skill`,
  `commands-process-inbox-skill` and `work-create-skill`; **delete**
  `work-item/definition-of-done`, `work-item/intake`,
  `work-item/body-surface`, `published-store-writes` and
  `external-work-tracker`.
- **Check:** `grep -rn` over `docs/capabilities` and `docs/taxonomy` for
  every removed record's path and id, and every removed term's path, prints
  nothing. Then run the released 2.8 `tcw validate` from the branch checkout,
  installed outside it (`pipx run --spec tcw-cli==2.8.1 tcw validate`, spec
  Design 15.3). It reads the records, and its 2.x work checks read the
  unchanged 2.x board, so its result is meaningful for both; record it in
  the implement round. The branch's own suite does not read these records.
- **Proof:** `pytest -q` (the documentation-surface test scans capability
  descriptions, and a record whose `Status` is `Missing` is skipped, so the
  new ones are checked).

## Task 13: Documentation sync and the full suite (spec Design 14; AC 22, 23)

**Documentation Sync.** Each documentation entry, evaluated against this
change:

| Entry | Trigger | Fires? | Action |
| --- | --- | --- | --- |
| `README.md` | Public-API | Yes: commands are removed and added. | Deferred to TCW-75 (spec Design 14). The documentation allowance lists what it still names. |
| `docs/guide/jira.md` | Tracker-Change | Yes: every `tcw work tracker` command and `work.tracker` key goes. | Deferred to TCW-75. |
| `docs/guide/<topic>.md` | Guide-Topic-Change | Yes: what `init` writes, where an item's files live, and which files TCW owns all change. | Deferred to TCW-75. |
| `docs/release-notes/upcoming/<slug>.md` | Public-API | Yes | **Create** `docs/release-notes/upcoming/2026-10-01-tcw-70-filesystem-work-backend-on-the-new-model.md`, following that folder's `README.md`. Its first non-blank line is a `##` heading; no 3.0.0 introduction (the epic's decision 15). Plain language: items are folders that never move, one `advance` command, comments, rename, delegation to another project, inbox items, what was removed and that the migration guide covers it. |
| `docs/changelogs/upcoming/<slug>.md` | Any-Code-Change | Yes | **Create** `docs/changelogs/upcoming/2026-10-01-tcw-70-filesystem-work-backend-on-the-new-model.md` with `## Added` (the backend, `open.py`, `record.py`, the new commands), `## Changed` (`validate`, `drift`, `tcw://` work references, `init`, `provision`, `tags add/rm` no longer staging, `stage prompt` composition, `{{tcw:request}}`, the `generate:` payload, `RESERVED_PROJECT_IDS`), `## Removed` (each removed command, the 2.x store files, `tcw/tracker/`, `tcw/harness.py`, the serve work routes) and `## Internal` (the Jira client move, the documentation allowance). |
| `skills/<component>/SKILL.md` | Skill-Driven-Component | Yes: the work component's commands change. | Deferred to TCW-74 (`skills/configure/` to TCW-75). |
| `skills/configure/references/<document>.md` | Configuration-Key-Change | Yes: `work.stages`, `work.hooks` and `work.backend` go live, and six keys go. | Deferred to TCW-75. |

Then:

- run the `documentation-sync` skill over the finished diff, and confirm the
  table;
- run `pytest -q` bare from the branch checkout (AC 23), with this
  repository's `tcw-config.yaml` and board unchanged;
- AC 22's last line: **create** `tests/test_upcoming_entries.py`, which
  checks that every file in `docs/release-notes/upcoming/` other than
  `README.md` has a first non-blank line starting with `##`. It is general
  rather than about this item's file, so it still passes after
  `scripts/cut_version.py` folds the entries away, and it holds every later
  slice to the epic's decision 15. Mutation-check it by putting a line of
  text above the heading.

**Commit:** the two entry files and the test.

## Verification

**What the suite cannot check:**

- **AC 23's throwaway copy.** Copy the checkout (`git worktree add` is not
  enough, because it shares the repository's `tcw-config.yaml` history; use
  `cp -R` of the working tree to the scratchpad), delete its root
  `tcw-config.yaml` and its `docs/work/`, and run `pytest -q` there with the
  branch's virtual environment. Record the result in the implement round.
- **The Playwright suite** (Task 9) is not part of the pytest run. Run it by
  hand once (`pnpm exec playwright test`, or the script `package.json`
  names) against the branch, and record the result.
- **The guards are only as good as their mutation checks** (Tasks 10 and
  11). Record each mutation and why it went red.
- **A hand trace of the new commands** in a scratch project built with the
  branch's `tcw init`: `new` with piped text, `list`, `advance` through to
  completion with a `pre` hook, a forced skip and its comment, `rename` with
  a referencing item, `new --project` into a second project, and
  `tcw validate`. Paste the session into the implement round. This is what
  shows the commands fit together, which per-criterion tests do not.
- **Re-read `fs_backend.py` and `open.py` against TCW-71's spec** and list,
  in the implement round, anything TCW-71's four seams (the `jira` branches
  of `open_backend` and `delegate`, Jira projects through `open_project`, a
  third contract parameter) would still have to change outside those seams.

## Notes

- **Blockers.** This item is already blocked by TCW-69, and TCW-71 by this
  item; nothing new to record.
- **Completing this item.** By hand, as TCW-69's plan describes: write the
  implement and verify artifacts, move the folder to `docs/work/completed/`,
  and move the Jira ticket, TCW-70, by hand.
- **Choices this plan makes that the spec leaves open**, for review:
  1. The new command module is staged as `tcw/work/cli_next.py` (Tasks 8–9)
     and renamed to `cli.py` in Task 10, so the switch-over commit carries no
     new command logic beyond the configuration commands.
  2. `FsWorkBackend` takes a `report` callable for its stderr lines (an
     adapter detail; the protocol is unchanged).
  3. The item record lives in its own module, `tcw/work/record.py`, because
     both backends and TCW-77's viewer use it; the stage-literal scan covers
     it.
  4. `test_documented_cli_surface.py` gains a check that documents name no
     refused key outside `REFUSED_KEYS`; without it the spec's key list
     would not be checked by anything until TCW-76.
  5. `tests/test_skill_lifecycle_parity.py` is skipped for TCW-74 under the
     spec's "any other test of a later slice's subject" rule.
  6. `normalize_tag`, `parse_documentation_entries` and `PROCEDURE_IDS` stay
     in `base.py`, which survives with the taxonomy and capabilities types.
  7. The spec was corrected at this stage: four records outside `work/`
     (`capabilities/remove-a-capability`, `cli/run-from-a-git-worktree`,
     `cli/point-tcw-at-a-project-i-already-have`,
     `skills/extras-triage-issues`) link to removed records, and
     `work/inspect-the-node-topology` moved from Unchanged to Changed for the
     same reason.
- **Self-review.** Every acceptance criterion maps to a task:
  - AC 1: Task 4;
  - AC 2–8: Task 4 (backend) and Task 8 (commands); AC 2's installed line in
    Task 10;
  - AC 9: Task 5 (library) and Task 8 (commands);
  - AC 10: Task 10 (commands) and Task 11 (`tcw.tracker`); the client move
    in Task 1;
  - AC 11: Task 10;
  - AC 12–14: Task 11;
  - AC 15–17: Task 7 (functions) and Task 10 (through the commands);
  - AC 18: Task 10;
  - AC 19: Task 9;
  - AC 20: Task 5 (library) and Task 10 (command);
  - AC 21: Task 6 (library) and Task 10 (command);
  - AC 22: Task 10, and Task 13 for the release-notes line
    (`tests/test_upcoming_entries.py`);
  - AC 23: Task 13 and Verification.

  Tasks 1–3 are clearing work for these; Task 12 is the spec's Capability
  changes section, which has no numbered criterion.

## Test files: fate of each

`T3` deletes, `T9` handles serve, `T10` ports at the switch, `T11` ports when
the 2.x names go. "Unchanged" means the file is not edited; it still runs at
every task. For **Split** files, the named tests are deleted in T3 and the
rest are ported in the task given.

### Moved (T1)

| File | Note |
| --- | --- |
| `tests/test_tracker_client.py` | To `tests/work/jira/test_client.py`, with a local `_Config` in place of `TrackerConfig`. |
| `tests/tracker_fake.py` | To `tests/work/jira/fake.py`, importing `tcw.work.jira.client`. |

### Skipped (T2)

TCW-74: `test_skill_flow.py`, `test_prompt_fallback.py`, `test_eval_coverage.py`,
`test_eval_files_changed.py`, `test_eval_fixture.py`, `test_eval_grading.py`,
`test_eval_runner.py`, `test_skill_lifecycle_parity.py`. Their fixtures
(`tests/fixtures/prompt_fallback/`, `tests/fixtures/eval_grading/`) stay.
TCW-73: `tests/cli/` (Markdown only; nothing to mark).

### Deleted

| File | Task | What it tests |
| --- | --- | --- |
| `test_already_integrated_check.py` | T3 | `complete --already-integrated`, merge helpers |
| `test_blocker_cycles_through_unreadable_items.py` | T3 | blocker-cycle refusal (3.0 refuses only parent cycles) |
| `test_boardless_delegate_and_slices.py` | T3 | `recursion.delegate`, epic slices |
| `test_capabilities_sidecar.py` | T3 | `declared_capabilities`, superseded by TCW-69's reader |
| `test_child_status.py` | T3 | status folders, claims, 2.x `parent` in `state.yaml` |
| `test_creation_commits.py` | T3 | auto-commit on creation |
| `test_cross_node_blocker_cycles.py` | T10 | blocker cycles; deferred because `test_damaged_state_on_edit.py` imports its helpers |
| `test_cross_node_blockers.py` | T3 | 2.x external blockers, tombstones, `reconcile` |
| `test_detached_worktree_teardown.py` | T3 | worktree teardown |
| `test_duplicate_slug_refusals.py` | T3 | a slug in two status folders |
| `test_edit_type.py` | T3 | `edit --type` |
| `test_epic_completability_across_checkouts.py` | T3 | tombstones, `reconcile` |
| `test_epic_completable.py` | T10 | `epic_completable`; deferred because `test_edit_refusal.py` imports `mk_node` |
| `test_harness.py` | T3 | `tcw/harness.py` |
| `test_inbox_title.py` | T3 | `body_title` for `inbox accept` |
| `test_initiative_node_qualified.py` | T3 | `initiative`, `delegate`, graveyard |
| `test_interrupted_claim.py` | T3 | `.claiming/` claims |
| `test_lifecycle_baseline.py` | T3 | 2.x `work.lifecycle` rendering, including the `self` case |
| `test_lifecycle_policy.py` | T3 | `parse_lifecycle_policy`, step tables |
| `test_local_qualified_blockers.py` | T3 | status paths, text blockers |
| `test_planning_gates_after_start.py` | T3 | `stage gate` after transitions |
| `test_projection.py` | T3 | `tcw/work/projection.py` |
| `test_recursion.py` | T3 | `tcw/work/recursion.py` |
| `test_repo_lifecycle.py` | T3 | this repository's 2.x config (spec 15.1) |
| `test_retention.py` | T3 | retention, `work delete`, publication |
| `test_scaffold.py` | T3 | `work scaffold` |
| `test_serve_descendants.py` | T9 | serve work board with descendants |
| `test_serve_duplicate_slug.py` | T9 | serve work routes |
| `test_serve_projection.py` | T9 | serve work detail |
| `test_stage_validate.py` | T3 | `stage validate` |
| `test_stale_item_path.py` | T3 | `submit`/`complete`, merge-back |
| `test_status_parity.py` | T3 | the client mirroring `WORK_STATUSES` (TCW-77 owns the client) |
| `test_store_lock.py` | T3 | the store lock |
| `test_store_publication.py` | T3 | publication, transition commits |
| `test_tombstone.py` | T3 | graveyard |
| `test_tracker_absent.py`, `test_tracker_binding.py`, `test_tracker_catch_up_moves.py`, `test_tracker_claim.py`, `test_tracker_claimability.py`, `test_tracker_cli.py`, `test_tracker_comment.py`, `test_tracker_config.py`, `test_tracker_create.py`, `test_tracker_gate.py`, `test_tracker_help.py`, `test_tracker_hold.py`, `test_tracker_import_returns.py`, `test_tracker_import.py`, `test_tracker_inheritance.py`, `test_tracker_link.py`, `test_tracker_message_tidy.py`, `test_tracker_ownership.py`, `test_tracker_pre_backlog.py`, `test_tracker_replay.py`, `test_tracker_strict_gate.py`, `test_tracker_strict.py`, `test_tracker_surface.py`, `test_tracker_sync_config.py`, `test_tracker_sync.py`, `test_tracker_validate.py` | T3 | the 2.x tracker integration (TCW-71 writes the Jira backend's tests) |
| `test_tracker_hardening.py` | T3 | after T1 moves its two client tests out, the rest is the 2.x tracker |
| `test_transition_hints.py` | T3 | next-step hints after transitions |
| `test_unplanned_start.py` | T3 | `work start` warnings |
| `test_unreadable_state_gates.py` | T3 | 2.x gates over a damaged `state.yaml` |
| `test_work_autocommit.py` | T3 | auto-commit of transitions |
| `test_work_review.py` | T3 | the review status; its reserved-ID case is reversed by the spec |
| `test_work_start.py` | T3 | `work start` releasing a claim |
| `test_worktree_completion.py` | T3 | worktree completion |

Fixture folders deleted in T3: `tests/fixtures/lifecycle_baseline/`,
`tests/fixtures/tracker/`, `tests/fixtures/show_baseline/`.

### Ported or split

| File | Deleted in T3 | Ported | What the port does |
| --- | --- | --- | --- |
| `tests/conftest.py` | — | T9 | Drop the desktop-opener patch and `stub_desktop_opener`. |
| `test_body_prompt.py` | `BODY_ORDER` and intake tests (order, request_wins_when_both, intake_is_named, intake_only, request_still_wins_with_intake, postmortem_spine_names_the_intake) | T10 | Span mechanics onto `{{tcw:request}}` and `substitute_request`; end-to-end cases through `stage prompt`. |
| `test_capabilities.py` | the nine `Planning doc` drift tests | — | The rest is unchanged; drift is covered by `tests/work/test_drift_work.py`. |
| `test_capabilities_rm.py` | — | T10 | `test_gate_removed_ignores_an_inherited_capability_at_the_same_path` onto `ledger_reader().removal()`. |
| `test_capability_gate_children.py` | the discard, merge-back, `reconcile` and complete-hint tests | T10 | Child-qualified path checks onto `records_problems` and `validate`. |
| `test_cli_help_coverage.py` | — | T10 | `tcw work tracker link` becomes `tcw work tags add`. |
| `test_command_suggestions.py` | the stage-gate and transition suggestion tests | T10 | Mechanism tests use surviving commands, matching the `cli_suggest.py` edit. |
| `test_config_edit_writers.py` | — | T10 | `tags add/rm` assert an unstaged file; fixtures lose `work.lifecycle`/`work.tracker`. |
| `test_damaged_state_on_edit.py` | the `start`, definition-of-done and sidecar tests | T10 | Onto an unreadable `item.yaml`, with helpers from `tests/work/projects.py`. |
| `test_documentation_config.py` | — | T10 | `test_a_malformed_block_does_not_break_the_board` onto the new parser's refusal. |
| `test_documentation_prompt.py` | the artifact-template span test | T10 | End-to-end tests onto `advance` and `work.stages`. |
| `test_documented_cli_surface.py` | — | T10 | The allowance, the key check and the guards (Task 10). |
| `test_edit_refusal.py` | the cycle, `update_work` and `check_blocker_edits` tests | T10 | "A refused edit writes nothing" onto `item.yaml`. |
| `test_environment_hardness.py` | transitions, blocker gating, board order, drop, escalate, delegate, reconcile, complete-in-worktree, the corrupt-`state.yaml` pair | T10 | Worktree work-path tests onto `resolve_store`; the rest unchanged. |
| `test_external_work_store.py` | claim, race, take-over, transition, worktree and vanish tests; `registering_a_tag_stages_the_config` | T10 | Location tests onto the backend; `incomplete_default_store_is_not_discoverable` inverted (3.5). |
| `test_item_tags_read.py` | the `state.yaml` tag-reading and `_parse_condition` tests | T10 | Registry tests onto `validate` and `edit`; the `list --tag` filter. |
| `test_lifecycle_config_tags.py` | condition, plan-stage-tag, skill-binding and policy tests | T10 | Registry normalization onto `validate`; the `--tag` warning; its `node` helper writes 3.0 keys. |
| `test_lifecycle_hooks.py` | the transition-id tests | T10 | Hook execution onto `advance` with stage `pre`/`post`; `lifecycle` listing onto the stage table. |
| `test_lifecycle_inert.py` | the `--transition --phase` and 2.x json tests | T10 | Onto the stage table. |
| `test_lifecycle_validation.py` | roles/kinds, empty-prompt fallback, rejected spelling, corpus | T10 | The four `file`-binding confinement tests onto 3.0 `file` bindings. |
| `test_literal_store_names.py` | the web 404 test | T10, T11 | `a_path_shaped_slug_is_no_such_item` onto `resolve_item` (T10); `stage_and_commit…` narrowed to `git_stage` (T11). |
| `test_multiproject.py` | epic, initiative, escalate and delegate-to-absent tests | — | The rest unchanged. |
| `test_non_git_writes.py` | every_work_write_refused, start/claiming, merge-back, refused_stage, ignore-rule and `.claiming` init tests | T10 | Work commands succeed outside git; re-captured read baselines. |
| `test_override_letter_case.py` | the two worktree-completion tests | — | The rest unchanged. |
| `test_procedure_config.py` | — | T10 | Onto TCW-69's procedure parsing and `validate`. |
| `test_procedure_verb.py` | — | T10 | Items made through the backend. |
| `test_project_overrides.py` | — | T10 | `list --include-descendants` becomes `list` and `nodes`. |
| `test_project_registry.py` | — | T11 | `"active"` moves from reserved to valid. |
| `test_qualified_ref.py` | status-prefixed refs | T10 | Project-qualified resolution onto `open_project` and `tcw://`. |
| `test_refs.py` | the three graveyard tests | T10 | Work resolve tests onto the backend. |
| `test_rename_work_item.py` | aliases, graveyard, commit/undo, tracker, cross-project rewrite, planning-doc rewrite, rollback | T10 | Folder move, reference rewrite, refusals. |
| `test_resolve.py` | the three artifact-template tests | T11 | Composition, conditions, `file`, `builtin`, `generate`, cap and plan mode onto `compose`. |
| `test_resolve_procedure.py` | — | T11 | Onto `procedure_prompt`. |
| `test_routing_nodes.py` | the `delegate`/`reconcile` tests | T10 | `test_nodes_still_prints_the_direct_topology` with a 3.0 fixture. |
| `test_serve.py` | work detail, open endpoint (4), blank artifact (3), pending removal | T9 | `seeded_node` without `FsWorkStore`; the AC 19 checks added. |
| `test_serve_resolve.py` | archived work, descendant and ancestor work hosting | T9 | Fixtures without the 2.x store; re-check the never-existed case. |
| `test_serve_write.py` | every work route test | T9 | CSRF, oversized body and malformed JSON onto a taxonomy route. |
| `test_shipped_prompts.py` | — | T11 | Keyed on TCW-69's stages; `review` and `qa` skipped naming TCW-74. |
| `test_show_json.py` | the 2.x schema, artifacts and blob tests, the two plain-show baseline tests | T10 | Error paths onto the new `show`. |
| `test_sidecar_paths_in_validate.py` | `test_a_work_target_checks_only_that_item` | T10 | Onto `records_problems` by stage, with the file at the item root. |
| `test_smoke.py` | `test_init_ignores_resolved_work_folders` | T10 | `init` asserts the work path's `.gitkeep`. |
| `test_stage_verb.py` | legality and next-step tables, hints, `start_next_stage`, every `stage gate` test, the 2.0 bare form | T10 | `stage prompt` tests onto TCW-69's config; the header names `advance --dry-run`. |
| `test_stdin_cli.py` | — | T10 | Work path in place of `backlog/`; the hook stdin test onto a stage `pre` and `advance`. |
| `test_store_bounds.py` | the work section and `FsWorkStore` in the parametrize | — | The rest unchanged. |
| `test_store_editor.py` | every `FsWorkStore` test | — | The rest unchanged. |
| `test_store_provisioning.py` | publication and auto-commit tests; the `reconcile`/`escalate` argv | T10 | Work commands onto the backend; the layout check inverted (3.5). |
| `test_unreadable_capabilities_sidecar.py` | board, projection, web-detail and `capability_gate` tests | T10 | Size, alias and depth limits onto TCW-69's reader; the completion refusal onto `advance`. |
| `test_unreadable_item_files.py` | guarded saves, revisions, web detail, transitions, plan stages, claims | T10 | "One damaged item does not break the board" onto `item.yaml` and `read_all`. |
| `test_untag_invalid_tags.py` | — | T10 | Onto `item.yaml` and `edit --untag`. |
| `test_upstream_projects.py` | serve upstream, tracker-hint, `--include-descendants`/`reconcile`/`/api/work` parts | T10 | The read-only rule through surviving commands; delegation through `new --project`; no commit counting. Re-check the Proposit migration test, which edits `work.tracker`. |
| `test_validate.py` | the two graveyard tests | T10 | `state.yaml` cases onto `item.yaml`; a leftover `dod.yaml` becomes a warning. |
| `test_validate_target.py` | the `work` axis tests | T9 | The rest onto a taxonomy or capability target. |
| `test_work.py` | inbox, transitions, statuses, gating, DoD, drop, discarded status, descendants, stage letters, `check()`, plan stages, artifacts, worktree, blocker cycles | T10 | Creation, collisions, properties, blockers, parent cycle, list, path, stdin, qualified show/path onto the new commands. |
| `test_work_tags.py` | `test_cli_list_include_descendants_splits_the_tag_filter` | T10 | Registry edits without `git add`; tag apply and filter onto `item.yaml`. |
| `tests/fixtures/non_git_reads/` | — | T10 | Re-capture `work-list.txt`, `work-nodes.txt`, `validate.txt`. |

### Unchanged

`tests/nodeconfig.py`, `test_capabilities_federation.py`,
`test_capabilities_reset.py`, `test_capability_ref_wording.py`,
`test_check_versions.py`, `test_committed_paths.py`, `test_config_edit.py`,
`test_configuration_text_home.py`, `test_cut_version.py`,
`test_documentation_sync_wiring.py`, `test_dynamic_skill_marker.py`,
`test_falsification_rule.py` (relies on `load_builtins` keeping its shape,
Task 11), `test_generate_hook.py`, `test_init_configured_tree_path.py`,
`test_legacy_store_config.py`, `test_override_in_linked_worktree.py`,
`test_override_references.py`, `test_plugin_manifests.py`,
`test_project_graph_paths.py`, `test_remote_session_setup.py`,
`test_serve_runtime.py`, `test_session_bootstrap.py`,
`test_shipped_procedures.py`, `test_skill_path_pointers.py`, `test_stdin.py`,
`test_store_nodes.py`, `test_subprocess_stdin.py`, `test_taxonomy_rm_gaps.py`,
`test_taxonomy.py`, `test_unattended_work_skill.py`,
`test_unpushed_version_script.py`, `test_validate_moved_stores.py`,
`test_worktree_sibling_nodes.py`.
