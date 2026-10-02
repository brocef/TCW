# Plan — Core work model: stage table, item folders that never move, and advance

This plan follows the revised spec (the version after the 2026-10-01 multi
review). Each task below is one commit, and the suite is green after each.

The new code is additive: no 2.x module changes behavior. The one exception is
Task 7, which moves `route_capability_path` and `Route` from `recursion.py`
into `gates.py`; `recursion.py` keeps working by importing them back. Task 7
therefore runs every test that reaches the moved code, not only the new ones.

Every task's tests live in `tests/work/` and run with `pytest tests/work -q`,
which takes seconds. The full suite (about half an hour) runs twice: after
Task 7, because that is the only task that touches 2.x code, and in Task 11.

## Before the first task

**How the board is driven.** This plan's tasks edit `tcw/`, so from the first
code edit on, the board is maintained by editing files, not through the `tcw`
CLI (`CLAUDE.md`, "Exception"). Before that edit, while the CLI is still the
released code, run `tcw work start <slug>` once to move the item to `active`.
Completion is done by hand at the end (see Notes).

**Which source runs.** Implementation happens on the epic branch, not on
`main`. The editable install points at the primary checkout, so it would run
`main`'s code. Use a virtual environment for the branch's checkout
(`python -m venv .venv && .venv/bin/pip install -e '.[dev]'`) and run `pytest`
and `tcw` from it, with the checkout as the current directory.

**Test layout.** `tests/` has no `__init__.py`; tests import shared helpers as
`tests.<module>` (for example `tests/test_child_status.py:14`). `tests/work/`
follows the same rule: no `__init__.py`, and the memory backend is imported as
`from tests.work.memory_backend import MemoryBackend`. New test file names must
not repeat a name already in `tests/`; none of the names below do.

**What the new code imports from 2.x, and what happens to it.** TCW-70 deletes
the 2.x work store, so the 3.0 modules import as little as possible, and each
import is listed here so TCW-70 knows what it must keep:

| Import | Used by | Fate |
| --- | --- | --- |
| `tcw.work.hooks.run_bindings` | `advance.py` | Kept. It runs a command with a timeout and reads only `binding.kind` and `binding.ref`, so it takes 3.0 bindings unchanged. TCW-70 keeps it when it deletes the rest of `hooks.py`. |
| `tcw.store.project.PROJECT_ID_PATTERN` | `model.py` | Kept: the project registry survives 3.0. |
| `tcw.store.base.normalize_tag` | `model.py`, `config.py` | Kept: tags survive. TCW-70 moves it if `base.py` goes. |
| `tcw.store.base.parse_documentation_entries`, `PROCEDURE_IDS` | `config.py` | Kept: both are pure and public. TCW-70 moves them if `base.py` goes. |
| `tcw.store.fs.FsCapabilitiesStore` | `gates.py` (production reader only) | Kept: the capabilities axis is not part of this redesign. |

Nothing else from `tcw.store.base`, `tcw.work.resolve` or `tcw.work.cli` is
imported. In particular, `resolve.select` and the 2.x binding parser
(`base.py:2459-2630`) are **not** reused: they accept `when: {type: …}`, which
3.0 refuses, and `select` reads `item.type`, which a 3.0 item does not have.

## Task 1: Exit codes and errors

- **Create** `tcw/exit.py` with the code constants `OK=0`, `ERROR=1`,
  `USAGE=2`, `REFUSED=3`, `NOT_FOUND=4`, `UNREACHABLE=5`, `MOVED_WITH_PROBLEM=6`.
- **Create** `tcw/errors.py` with a base `TcwError(Exception)` carrying a
  `code` attribute, and its subclasses `UsageError` (2), `Refused` (3),
  `NotFound` (4), `Unreachable` (5), `MovedWithoutNote` (6) and
  `BackendError` (1). `Refused` takes an optional `name` (a backend name such
  as a Jira ticket key) for a refusal after the backend created a record. The
  errors live at the top of the package so that `model.py` and `backend.py`
  can both raise them without importing each other, and so that the taxonomy
  and capabilities commands can use them later (TCW-73).
- **Create** `tests/work/test_errors.py`: each error carries its code, and the
  codes equal the `tcw/exit.py` constants. (TCW-73's table is not in the
  repository, so the test pins the numbers the spec states.)
- **Proof:** `pytest tests/work -q`.

## Task 2: Identity and properties (spec Design 1–2; AC 1–4)

- **Create** `tcw/work/model.py` with:
  - `FOLDER_LIMIT = 128`, the folder regex, and `Slug`, a frozen dataclass with
    `parse(text, current_project)` and `__str__`. The project part is checked
    against `PROJECT_ID_PATTERN` only, not `validate_project_id`, so the 2.x
    reserved names do not apply (spec Design 1.1).
  - `title_words(title, limit)`: lowercase, runs outside `[a-z0-9]` become one
    `-`, ends trimmed, cut back to the last `-` boundary within `limit`, and
    `untitled` when nothing is left. It does not reuse `base.slugify`
    (`base.py:2400`), so that `model.py` does not depend on 2.x for it; the
    rule is the same, plus the length cut and the fallback.
  - `PRIORITIES` and `SIZES`.
  - `Item`, a frozen dataclass with the spec's fields.
  - `UNSET`, a sentinel, and `Changes`, a dataclass with `title`, `priority`,
    `effort`, `complexity`, `assignee` and `parent` (each `UNSET` by default;
    `None` clears), plus `add_tags`, `remove_tags`, `add_blocked_by` and
    `remove_blocked_by`.
  - `validate_changes(changes, *, item_slug, registered_tags, current_project,
    parent_of) -> None`, raising `UsageError` for every case in spec Design
    2.4. `parent_of(slug) -> Slug | None` is a callable the caller supplies
    (backends pass a function over their own reads), and the cycle check
    walks it from the proposed parent, stopping at a slug in another project,
    at `None`, or on reaching `item_slug` (a cycle). It also stops after
    visiting as many slugs as exist, so a cycle already present in the data
    cannot loop forever.
  - `apply_changes(item, changes) -> Item`, a pure function backends may use.
  - `blocks_of(slug, items)`.
- **Create** `tests/work/test_identity.py` (AC 1, 2) and
  `tests/work/test_properties.py` (AC 3, 4). AC 4 runs through
  `apply_changes` and `blocks_of`. AC 3's cycle case uses a two-item
  `parent_of` table.
- **Proof:** `pytest tests/work -q`.

## Task 3: The stage table (spec Design 3; AC 5 table part, AC 6 navigation part)

- **Modify** `tcw/work/model.py` to add:
  - `Stage`, a frozen dataclass with the columns `name`, `kind`, `artifact`,
    `optional`, `verdict`, `on_reject`, `completion`, `discard`, `prompt` and
    `gates`;
  - `STAGES`, the table exactly as in the spec;
  - `stage(name)`, which raises `UsageError` for an unknown name.
- **Add** the pure navigation helpers. Each that depends on configuration
  takes `enabled: frozenset[str]`:
  - `completion_stage()` and `discard_stage()`, found by their columns;
  - `start_stage()`, the first flow stage whose artifact is not `none`, and
    `inbox_stage()`, the first flow stage;
  - `flow_order(enabled)`, the enabled flow stages in order;
  - `next_stage(current, enabled)`, the next enabled flow stage after
    `current`, or else the completion stage. It raises `ValueError` when
    `current` is a terminal or side stage; `advance` never calls it then,
    and the error makes a wrong call loud.
  - `position(name)`, the table index, with the completion stage treated as
    later than every flow stage;
  - `is_skip(current, target, enabled)`, true when `target` is later than
    `current` and an enabled flow stage lies strictly between them; the
    discard stage is never a skip;
  - `records_gate_stage(enabled)`, the stage following the last rounds stage
    whose `verdict` is no, worked out with `next_stage`;
  - `gates_for(target, enabled)`, the built-in gate names for a target: the
    table's `gates`, plus `records` when the target is `records_gate_stage`.
- **Create** `tests/work/test_stage_table.py`. It covers:
  - the table rows, and exactly one row with `completion` and one with
    `discard`;
  - `next_stage` with plan disabled (spec→implement) and with review and qa
    disabled (implement→completed);
  - `next_stage` on a terminal stage raising;
  - `is_skip` for spec→implement, spec→completed (review and qa disabled),
    review→spec (not a skip) and anything→discarded (not a skip);
  - `records_gate_stage` as review, as qa with review disabled, and as
    completed with both disabled;
  - `start_stage()` is request and `inbox_stage()` is inbox;
  - `stage("bogus")` raising `UsageError`.
- **Proof:** `pytest tests/work -q`.

## Task 4: Configuration (spec Design 8; AC 6 config part, AC 16)

- **Create** `tcw/work/config.py` with:
  - `When(tags, not_tags)` and `Binding(kind, value, when, origin=None)`, both
    frozen, with a `ref` property returning `value` (what `run_bindings`
    reads); `origin` is an opaque label TCW-72 uses to say which file a
    binding came from;
  - `parse_bindings(raw, where, role, problems) -> list[Binding]`, written for
    3.0 rather than reusing `_parse_binding_list`. Its rules:
    - each binding is a mapping with exactly one kind key and an optional
      `when`;
    - the legal kinds by role are `prompt` and procedures: `blob`, `file`,
      `generate`, `builtin`, `skill`; `pre`: `command`; `post`: `command`,
      `skill`. A `skill` in `pre` gets its own message saying why;
    - `builtin` must be the literal `true`; every other value is a non-blank
      string, except that a `blob` may be blank (an explicit "say nothing");
    - a skill name has no whitespace or path separator;
    - `when` is a non-empty mapping with only `tags` and `not_tags`, each a
      list of non-blank strings without commas, normalized with
      `normalize_tag`. `type` gets its own message saying 3.0 items have no
      type;
    - duplicates (same kind, value and `when`) are allowed, unlike today's
      parser: after TCW-72 merges a person's list with the team's, the same
      binding may legitimately appear twice.

    These rules match today's parser (`base.py:2459-2630`) except for the
    two refusals and the duplicates rule.
  - `StageConfig` (`enabled`, `status`, `prompt`, `pre`, `post`),
    `HookLimits` (`timeout=300`, `output_cap=65536`) and `WorkConfig`
    (`backend`, `path`, `repository`, `tags`, `documentation`, `procedures`,
    `stages`, `hooks`, `jira`), with `WorkConfig.enabled` as a property;
  - `MIGRATION_GUIDE = "docs/migration-guide-2.8-to-3.0.0.md"`;
  - `parse_work_config(mapping, origins=None) -> tuple[WorkConfig,
    list[ConfigProblem]]`, which never raises. `ConfigProblem` is a frozen
    `(key_path: tuple[str, ...], message: str)`; a problem about two keys
    names the first. `origins` maps a key path to an origin label, and each
    `Binding` built from a list under that path carries the label.
- **What the parser reuses.** `documentation` goes through
  `parse_documentation_entries` (`base.py:2880`). `procedures` is parsed here,
  with the procedure ids from `PROCEDURE_IDS` (`base.py:1143`) and the same
  "an empty list is not an opt-out" rule as `parse_procedures`
  (`base.py:3063`), but through `parse_bindings`, so `when.type` is refused
  there too.
- **What the parser refuses**, each as one `ConfigProblem` naming its key path:
  - the removed keys (`lifecycle`, `tracker`, `auto-commit-transitions`,
    `publish-transitions`, `trunk-branch`, `retain`), each naming
    `MIGRATION_GUIDE`; `lifecycle`'s message also says that `artifacts`
    templates become conditional `prompt` bindings;
  - an unknown key under `work`, under `work.hooks`, or on a stage;
  - an unknown stage;
  - `enabled: false` on a stage whose `optional` is no;
  - `pre`, `post` or `status` on a side stage;
  - `status` or `jira` when `backend` is not `jira`;
  - in Jira mode, a missing `status` on an enabled non-side stage, or two
    enabled stages with the same `status`;
  - `hooks.timeout` that is not a positive number (a boolean counts as not a
    number) and `hooks.output-cap` that is not a positive integer.
- **Create** `tests/fixtures/tcw-config-2.8.yaml`, a copy of this repository's
  current `tcw-config.yaml`.
- **Create** `tests/work/test_config.py` covering AC 16 and AC 6's "disabling
  `implement` or `request` is a config error". One test parses the fixture
  and asserts that the problems name `lifecycle`, `tracker` and `retain` as
  removed. It reads the fixture, not the live file, so TCW-76's migration of
  the live file does not break it.
- **Proof:** `pytest tests/work -q`.

## Task 5: Layout and verdicts (spec Design 4; AC 15, part of AC 7 and 14)

- **Create** `tcw/work/layout.py` with:
  - `Layout(work_root: Path, enabled: frozenset[str], external: frozenset[str])`;
  - `ROUND_NAME = re.compile(r"^round-([1-9][0-9]*)\.md$")` and
    `HANDOFF_NAME = re.compile(r"^handoff-\d{8}T\d{6}Z\.md$")`;
  - `item_dir(slug)`, `stage_dir(slug, stage)`, `document(slug, stage)`,
    `capabilities_file(slug)` (`<item>/capabilities.yaml`, which names no
    stage), `rounds(slug, stage) -> list[tuple[int, Path]]`,
    `next_round(slug, stage)`, `latest_round(slug, stage)`,
    `handoff_path(slug, stage, now)` and `latest_handoff(slug, stage)`;
  - `round_verdict(path) -> Verdict`, where `Verdict` holds `state`
    (`accepted`, `rejected` or `invalid`) and `judges: int | None`. It reads
    the front matter with `yaml.safe_load` and treats any parse error, a
    missing key, a value other than the two strings, or a `judges` that is
    not a non-negative integer (a boolean counts as not an integer) as
    `invalid`;
  - `current_verdict(slug, stage) -> str` returning `none`, `invalid`,
    `stale`, `accepted` or `rejected` by spec Design 4.8, comparing `judges`
    with the highest round of the stage's `on_reject` stage (0 when none);
  - `path(slug, stage=None, *, next=False, handoff=False, now=None)`.
- **What it refuses:**
  - a stage whose artifact is `none`, or that is external, as `Refused`;
  - a disabled stage as `UsageError`;
  - `next` on a non-rounds stage, and `handoff` together with `next`, as
    `UsageError`;
  - a handoff path that already exists, as `Refused`.
- **It creates nothing on disk.** No function makes a directory or a file.
- **Create** `tests/work/test_layout.py` (AC 15). It also covers verdict
  parsing (accepted, rejected, no front matter, a bad `verdict`, a missing
  or boolean `judges`, unreadable YAML) and `current_verdict` returning each
  of its five values, including `stale` after a newer implement round.
- **Proof:** `pytest tests/work -q`.

## Task 6: Backend interface and the memory backend (spec Design 5)

- **Create** `tcw/work/backend.py` with:
  - `Query`, a frozen dataclass (`stages`, `parent`, `assignee`, `tags`, `all`), and
    `default_includes(item_stage) -> bool`, the default rule: a non-terminal
    stage or no stage;
  - `Comment`, a frozen dataclass (`at`, `author`, `text`);
  - `WorkBackend`, a `runtime_checkable` `typing.Protocol` with the eleven
    operations and the attributes `project`, `external_stages` and
    `inbox_items`.
- **Create** `tests/work/memory_backend.py`. Its `MemoryBackend`:
  - keeps items in a dict and records every call, with its arguments, in
    `calls`;
  - `create` makes the item folder under a `tmp_path` work root, so the
    layout has somewhere real, and names it `<n>-<title words>`;
  - uses `apply_changes`, and raises `NotFound` for an unknown folder;
  - takes constructor arguments for `external_stages`, `inbox_items`, and a
    `stage=None` override that puts an item in the "no stage" state;
  - in `set_stage`, records the note as a comment, and can be told to raise
    `Refused`, to raise `MovedWithoutNote` after changing the stage, or to
    report a stage other than the target;
  - in `lookup`, matches a name only when a folder is exactly that name
    followed by `-`;
  - in `list`, applies `Query` and raises `UsageError` for `stages` with
    `all`;
  - keeps the request text given to `create` for `read_request`, keeps every
    comment (including trace notes from `set_stage`) with a timestamp for
    `read_comments`, and returns a constructor-given user name (or `None`)
    from `current_user`. The three reads are not recorded as writes in
    `calls`.
- **Create** `tests/work/test_memory_backend.py`. It checks:
  - that the memory backend satisfies the protocol (`isinstance`; this proves
    only that the names exist, which is all a protocol check can prove);
  - that the default `list` includes an item with no stage and hides
    terminal ones;
  - that `all` shows terminal items, and `parent` and `tags` filter (an item matches when it carries any of the given tags);
  - that `lookup("TCW-6")` does not match a folder `TCW-67-x`;
  - AC 21: the three reads (request text, comments newest first and limited,
    the current user).

  The later tasks rely on these behaviors, so they are pinned here.
- **Proof:** `pytest tests/work -q`.

## Task 7: Built-in gates and drift (spec Design 7; AC 13, 14, 18)

- **Create** `tcw/work/gates.py` with:
  - the reader's answer types: `Present(status)`, `ABSENT`,
    `Unchecked(reason)`, and for removals `REMOVED`, `STILL_LOCAL`,
    `INHERITED` or `Unchecked(reason)`;
  - `RecordsReader`, a protocol with `capability(path)`, `removal(path)` and
    `term(term)`;
  - `Declared` and `parse_declarations(path) -> Declared | str` (the string
    is the problem). It uses the strict schema and has no `added:` alias. A
    missing file gives an empty `Declared`;
  - `records_gate(layout, slug, reader) -> list[str]` and
    `records_problems(layout, slug, reader, *, finished) -> list[str]`, the
    gate being `records_problems(..., finished=True)`;
  - `completion_gate(layout, slug) -> list[str]`, over the layout's enabled
    verdict stages that are not external;
  - `drift_problems(layout, items, reader) -> list[str]`, with the newest
    declaration by `Item.created` winning and same-day disagreements
    reported as ambiguous;
  - `ledger_reader(own, registry, project_id, open_child, taxonomy)`, the
    production `RecordsReader`. It routes every path through
    `route_capability_path`, and turns a routing problem string, a
    `RefError`, a `ValueError` or a `yaml.YAMLError` into `Unchecked`.
    `removal` mirrors `recursion.py:126-146`: an alias in `store.extends`
    is `INHERITED`, a local capability is `STILL_LOCAL`, and anything else
    is `REMOVED`.
- **Move** `route_capability_path` and its `Route` NamedTuple from
  `tcw/work/recursion.py:195-253` into `gates.py`. **Modify**
  `tcw/work/recursion.py` to import both from `tcw.work.gates`. The behavior
  is unchanged.
- **The import direction.** `gates.py` must not import `recursion.py`.
  `tcw/store/fs.py` does not import `tcw.work`, so importing
  `FsCapabilitiesStore` from it causes no cycle. `Route`'s field annotation
  is evaluated when the class is created (`recursion.py` has no
  `from __future__ import annotations`), so `gates.py` imports
  `FsCapabilitiesStore` directly rather than writing the annotation as a
  string.
- **Create** `tests/work/test_gates.py` covering AC 13, 14 and 18 with a fake
  `RecordsReader`. Add two tests over a real temporary `FsCapabilitiesStore`
  through `ledger_reader`: one that a local path reports `Missing`, and one
  that a removed local path answers `REMOVED`.
- **Proof:**
  - `pytest tests/work -q`;
  - `pytest tests/test_capability_gate_children.py tests/test_recursion.py
    tests/test_capabilities_rm.py tests/test_unreadable_capabilities_sidecar.py -q`,
    which cover `capability_gate` through the moved function;
  - the full suite, `pytest -q`, because this is the only task that changes
    2.x code (`tcw/validate.py:273` and `tcw/work/cli.py:42` also reach the
    moved function).

## Task 8: `advance` (spec Design 6; AC 6–12)

This is the riskiest task. It comes after the table, layout, gates and memory
backend it composes, so every input is already tested.

- **Create** `tcw/work/advance.py` with:
  - `Outcome`, holding `code`, `stage`, `messages` and `overridden`;
  - `advance(backend, config, layout, reader, project_root, slug, *, to=None,
    force=False, reason=None, dry_run=False) -> Outcome`;
  - `discard(backend, config, layout, reader, project_root, slug, reason)`,
    which is `advance(to=discard_stage(), reason=reason)`.
- **The steps** follow spec Design 6.1–6.9 in order, one small private
  function each, so the spec's numbering maps onto the code:
  - `_check_usage` (6.1) raises `UsageError` before anything is read,
    including for a discard without a reason;
  - `_read` (6.2) lets `NotFound` propagate;
  - `_choose_target` (6.3) and `_check_direction` (6.4) return a refusal
    `Outcome` or nothing;
  - `_run_gates` (6.5), `_move` (6.7), `_run_post` (6.8).
- **Matching `when:`** is a local function over the 3.0 `Item`: a binding
  applies when it has no `when`, or when the item has at least one of
  `when.tags` and none of `when.not_tags`. This is today's rule
  (`base.py:1194-1210`) without `type`.
- **Running hooks.** The environment is `os.environ` plus the spec's
  variables, built by a local `_hook_env` (the 2.x `hooks.hook_env` is not
  changed or used). `TCW_SLUG` is the full `project/folder` slug, and the
  working directory is the project root. Each binding is run by calling `run_bindings([binding],
  project_root, env, config.hooks.timeout, label)`, one binding at a time.
  Without `force`, the first failure stops the loop and refuses the move.
  With `force`, every binding runs and each failure is collected into
  `Outcome.overridden`.
- **The trace note** is built by one function (`_note`) and passed to
  `set_stage` whenever the move has a reason.
- **After the move:** `Refused` from `set_stage` returns exit 3 with no
  `post`; `MovedWithoutNote` sets the outcome to exit 6 with "moved to X, but
  the trace was not recorded; add it with `tcw work comment`", and `post`
  still runs; a reported stage other than the target returns exit 1 naming
  both, with no `post`.
- **Create** `tests/work/test_advance.py`, covering AC 6–12 through
  `advance`. It uses the memory backend and real hooks run with
  `cwd=tmp_path`:
  - `true` and `false` for plain pass and fail;
  - one `python -c "…"` hook, which needs `PATH` and so proves the caller's
    environment is passed through;
  - one `sh -c 'test "$TCW_STAGE" = review && test -n "$TCW_ITEM_PATH" && …'`
    hook that checks the variables;
  - two failing hooks under `force`, to show both run and both are noted.

  The records-gate and completion-gate cases in AC 9 use a fake reader and
  real round files.
- **Proof:** `pytest tests/work -q`.

## Task 9: References and stage-ahead checks (spec Design 9; AC 17)

- **Create** `tcw/work/references.py` with:
  - `Problem`, holding `level` (`warning` or `unresolved`), `slug` and
    `message`;
  - `reference_problems(items, current_project, resolve) -> list[Problem]`.
    Its docstring says the caller passes every item, finished ones included;
  - `stage_problems(items, layout) -> list[Problem]`, which skips items with
    no stage and items at a terminal stage, and whose warning text says that
    a forced skip warns until the item finishes.
- **Create** `tests/work/test_references.py` (AC 17).
- **Proof:** `pytest tests/work -q`.

## Task 10: Structural guards (AC 5, AC 19)

- **Create** `tests/work/test_model_guards.py`. It uses `ast` to walk the new
  modules (`advance`, `gates`, `layout`, `backend`, `references`, `config`,
  `model`), `tcw/exit.py` and `tcw/errors.py`.
- **AC 5.** Every string constant that is not a docstring is checked for a
  stage name as a whole word (`\b<name>\b`). In `model.py`, stage names may
  appear only inside the `STAGES` assignment. String pieces of f-strings and
  implicitly joined literals are separate constants to `ast`, so they are
  checked too.
- **AC 19, static part.** No module imports `subprocess`; no module refers
  to `os.system` or `os.popen`; and no module refers, by import or by
  attribute, to the git helpers in `tcw/store/fs.py` that change state:
  `_git`, `_git_index`, `git_stage`, `git_rm`, `git_mv`, `git_commit`,
  `git_commit_result`, `add_worktree`, `merge_worktree`, `remove_worktree`.
  The read-only helpers (`git_root`, `git_ignored`, `git_current_branch`)
  are allowed, because TCW may read git. `advance.py` reaches `subprocess`
  only through `tcw.work.hooks`.
- **Create** `tests/work/test_no_git.py` for AC 19's behavioral part: in a
  temporary git repository with one commit, run a forced `advance` with a
  passing and a failing `pre` hook and a `post` hook, then assert that
  `git rev-parse HEAD`, `git status --porcelain` (ignoring the item folder
  the test itself wrote before the snapshot) and `git for-each-ref` are
  unchanged.
- **Proof that the guards work.** Each guard is mutation-checked by hand
  before commit, and the results are recorded in the implement round:
  - put `"review"` into `advance.py`, and `"spec/x.yaml"` into `layout.py`;
  - put `import subprocess` into `layout.py`, and `fs._git(...)` into
    `gates.py`;
  - make the memory backend's `set_stage` run `git commit --allow-empty`;
  - confirm each guard goes red and read why; then revert the mutations.
- **Proof:** `pytest tests/work -q`.

## Task 11: Documentation sync and the full suite (AC 20)

**Documentation Sync.** Each documentation entry was evaluated against this
change, which is internal and wires nothing into a command:

| Entry | Trigger | Fires? | Action |
| --- | --- | --- | --- |
| `README.md` | Public-API | No. No command, flag or output changes. | none |
| `docs/guide/jira.md` | Tracker-Change | No. No `tcw work tracker` behavior or `work.tracker` key changes in 2.x, and the new parser is not live. | none |
| `docs/guide/<topic>.md` | Guide-Topic-Change | No. No file a guide names moves, and no setting's location changes, until TCW-70. | none |
| `docs/release-notes/upcoming/<slug>.md` | Public-API | No. Nothing is visible to users. | none |
| `docs/changelogs/upcoming/<slug>.md` | Any-Code-Change | Yes | **Create** `docs/changelogs/upcoming/2026-10-01-tcw-69-core-work-model-stage-table-item-folders-that-never-move-and-advance.md`. Under `## Internal`, say that the 3.0 work model was added (stage table, layout and verdicts, backend protocol, `advance`, gates and drift, config parser, reference checks, exit codes), not yet wired into any command. Under `## Changed`, say that `route_capability_path` moved to `tcw/work/gates.py`. |
| `skills/<component>/SKILL.md` | Skill-Driven-Component | No. The work component's CLI and behavior are unchanged until TCW-70. | none |
| `skills/configure/references/<document>.md` | Configuration-Key-Change | No. The new keys (`work.stages`, `work.hooks`, `work.backend`) are not read by any command yet. TCW-70 and TCW-75 document them when they go live. | none |

Then:

- run the `documentation-sync` skill over the finished diff to confirm the
  table;
- run `pytest -q`, the whole suite (AC 20);
- run `tcw validate` from the branch's checkout, using the branch's virtual
  environment.

**Commit:** the changelog entry.

## Verification

**What the suite cannot check:**

- **That the design composes for real backends.** The memory backend proves
  the interface is consistent, not that it fits. The interface was already
  read against TCW-70's and TCW-71's ticket text during the spec review,
  which is why `set_stage` takes a note and `lookup` exists. Before handing
  over, re-read `backend.py` against both tickets once more and list, in the
  final implement round, any operation either would still have to fake.
- **That the stage rules read naturally.** Write a few sentences in the
  implement round tracing three cases through the code by hand: a bare
  `advance` in a project with review disabled and qa enabled; a qa rejection
  followed by a fix, showing the old review round becoming `stale`; and a
  Jira-mode qa rejection with `external_stages = {request, qa}`.
- **The guard tests are only as good as their mutation check** (Task 10).
  Record the mutation results in the implement round.

## Notes

- **Blockers.** TCW-70, TCW-71, TCW-72, TCW-73 and TCW-77 build on this item,
  but none is a work item yet, so no `--blocked-by` can be recorded. When each
  is adopted, give it `--blocked-by` on this slug.
- **Completing this item.** Completion is by hand, because the CLI is under
  change. Do what `tcw work complete` would have done: run `tcw validate` from
  the primary checkout after merging, write `refined-outcome.md`, move the
  folder to `docs/work/completed/`, and record that the Jira ticket (TCW-69)
  must be moved by hand, since the hand edit runs no tracker sync.
- **Self-review.** Every acceptance criterion maps to a task:
  - AC 1–4: Task 2;
  - AC 5: Tasks 3 and 10;
  - AC 6: Task 3 (helpers), Task 4 (config) and Task 8 (through `advance`);
  - AC 7: Task 5 (`current_verdict`) and Task 8;
  - AC 8–12: Task 8;
  - AC 13, 14 and 18: Task 7, with AC 9's gate cases through `advance` in
    Task 8;
  - AC 15: Task 5;
  - AC 16: Task 4;
  - AC 17: Task 9;
  - AC 19: Task 10;
  - AC 20: Tasks 7 and 11;
  - AC 21: Task 6.

  Task 1 and Task 6 are infrastructure for these.
