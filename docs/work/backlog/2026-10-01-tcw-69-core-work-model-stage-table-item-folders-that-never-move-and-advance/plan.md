# Plan — Core work model: stage table, item folders that never move, and advance

Each task below is one commit, and the suite is green after each. The new code
is additive: no 2.x module changes behavior. The one exception is Task 7, which
moves `route_capability_path` from `recursion.py` into `gates.py`, and
`recursion.py` keeps working by importing it from there. Every task's tests live
in `tests/work/` and run with `pytest tests/work -q`, which takes seconds. The
full suite runs once, in Task 11, because it takes about half an hour.

**How the board is driven.** This plan's tasks edit `tcw/`, so from
`implement` on, the board is maintained by editing files, not through the
`tcw` CLI (`CLAUDE.md`, "Exception"). The CLI is only safe to use where it does
not depend on the code being changed. That includes moving this item to
`active` before the first code edit.

## Task 1: Exit codes and errors

- **Create** `tcw/exit.py` with the code constants:
  - `OK=0`
  - `ERROR=1`
  - `USAGE=2`
  - `REFUSED=3`
  - `NOT_FOUND=4`
  - `UNREACHABLE=5`
  - `POST_FAILED=6`
- **Create** `tcw/work/backend.py` with the errors only, for now:
  - a base `WorkError(Exception)` with a `code` attribute;
  - its subclasses `UsageError`, `Refused`, `NotFound`, `Unreachable` and
    `BackendError`.
- **Create** `tests/work/__init__.py` (empty) and `tests/work/test_errors.py`.
  The test checks that each error carries its code, and that the codes match
  TCW-73's table.
- **Proof:** `pytest tests/work -q`.

## Task 2: Identity and properties (spec Design 1–2; AC 1–4)

- **Create** `tcw/work/model.py`. It holds:
  - `Slug`, a frozen dataclass with `parse(text, current_project)` and
    `__str__`, using the folder regex and the 128-character limit.
  - `title_words(title, limit)`. It reuses nothing from `base.slugify`
    (`tcw/store/base.py:2402`), which has a 120-character cut and different
    rules. It does lowercase, collapses runs of characters outside
    `[a-z0-9]` to `-`, trims the ends, and cuts at a `-` boundary.
  - `PRIORITIES` and `SIZES`.
  - `Item`, a frozen dataclass with the spec's fields.
  - `Changes`, a dataclass with these fields:
    - `title`, `priority`, `effort`, `complexity`, `assignee` and `parent`
      (sentinel `UNSET`; `None` clears);
    - `add_tags` and `remove_tags`;
    - `add_blocked_by` and `remove_blocked_by`.
  - `validate_changes(changes, *, item_slug, registered_tags, current_project) -> None`,
    which raises `UsageError` or `Refused` as the spec says.
  - `apply_changes(item, changes) -> Item`, a pure function that backends may
    use.
  - `blocks_of(slug, items)`.
- **Create** `tests/work/test_identity.py` (AC 1, 2) and
  `tests/work/test_properties.py` (AC 3, 4). AC 4 runs through
  `apply_changes` and `blocks_of`.
- **Proof:** `pytest tests/work -q`.

## Task 3: The stage table (spec Design 3; AC 5 table part, AC 6 navigation part)

- **Modify** `tcw/work/model.py` to add:
  - `Stage`, a frozen dataclass with the columns `name`, `kind`, `artifact`,
    `optional`, `verdict`, `on_reject` and `gates`;
  - `STAGES`, the table exactly as in the spec;
  - `DISCARD = "discarded"`;
  - `stage(name)`, which raises `UsageError` for an unknown name.
- **Add** the pure navigation helpers. Each takes an `enabled: frozenset[str]`:
  - `flow_order(enabled)`, the enabled flow stages in order;
  - `next_stage(current, enabled)`, the next enabled flow stage, or else the
    first terminal stage;
  - `completion_stage()`, the first terminal stage;
  - `is_skip(current, target, enabled)`;
  - `records_gate_stage(enabled)`, the stage following the last unverdicted
    rounds stage, worked out with `next_stage`;
  - `gates_for(target, enabled)`, the built-in gate names for a target:
    the table's `gates`, plus `records` when the target is
    `records_gate_stage`.
- **Create** `tests/work/test_stage_table.py`. It covers:
  - the table rows;
  - `next_stage` with plan disabled (spec→implement) and with review and qa
    disabled (implement→completed);
  - `is_skip` for spec→implement, spec→completed (review and qa disabled),
    review→spec (not a skip) and anything→discarded (not a skip);
  - `records_gate_stage` as review, then as `completed` when review and qa
    are disabled;
  - `stage("bogus")` raising `UsageError`.
- **Proof:** `pytest tests/work -q`.

## Task 4: Configuration (spec Design 8; AC 6 config part, AC 16)

- **Create** `tcw/work/config.py` with:
  - `StageConfig`, holding `enabled`, `status`, and `prompt`, `pre` and
    `post`, each a list of `Binding`;
  - `WorkConfig`, holding `backend`, `path`, `repository`, `tags`,
    `documentation`, `procedures`, `stages: dict[str, StageConfig]` and
    `jira: dict | None`;
  - `WorkConfig.enabled` as a property;
  - `parse_work_config(mapping) -> tuple[WorkConfig, list[str]]`.
- **What the parser reuses.** Binding lists go through the existing
  `_parse_binding_list` (`tcw/store/base.py`) with the existing kind sets.
  These are imported, not copied, and TCW-72 replaces the marker.
  `documentation` and `procedures` reuse the existing parsers at
  `base.py:2880` and `base.py:3063`.
- **What the parser refuses:**
  - the removed keys, each with a message naming
    `docs/migration-guide-2.8-to-3.0.0.md`;
  - an unknown key;
  - an unknown stage;
  - an unknown key on a stage;
  - `enabled: false` on a required stage;
  - in Jira mode, a missing or duplicate `status`.
- **Create** `tests/work/test_config.py` (AC 16, plus "disabling `implement`
  or `request` is a config error" from AC 6). One test parses this
  repository's own `tcw-config.yaml`. It asserts that the problems name
  `lifecycle`, `tracker` and `retain` as removed, which pins the expected
  migration surface.
- **Proof:** `pytest tests/work -q`.

## Task 5: Layout (spec Design 4; AC 15)

- **Create** `tcw/work/layout.py` with:
  - `Layout(work_root: Path, external_stages: frozenset[str])`;
  - `item_dir(slug)`, `stage_dir(slug, stage)`, `document(slug, stage)`,
    `rounds(slug, stage) -> list[(n, Path)]`, `next_round(slug, stage)`,
    `latest_round(slug, stage)`, `handoff_path(slug, stage, now)`,
    `latest_handoff(slug, stage)` and `capabilities_file(slug)`;
  - `path(slug, stage=None, next=False)`;
  - `round_verdict(path) -> "accepted" | "rejected" | "invalid"`, which
    parses YAML front matter with `yaml.safe_load`.
- **What it refuses:**
  - a stage whose artifact is `none` or that is external, as `Refused`;
  - a `next` on a non-rounds stage, as `UsageError`.
- **It creates nothing on disk.** No function makes a directory.
- **Create** `tests/work/test_layout.py` (AC 15). It also covers verdict
  parsing: accepted, rejected, missing front matter, a bad value, and
  unreadable YAML (invalid).
- **Proof:** `pytest tests/work -q`.

## Task 6: Backend interface and the memory backend (spec Design 5)

- **Modify** `tcw/work/backend.py` to add:
  - `Query`, a dataclass;
  - `WorkBackend`, a `typing.Protocol` with the seven operations and the
    attributes `project`, `external_stages` and `inbox_items`.
- **Create** `tests/work/memory_backend.py`. Its `MemoryBackend` keeps items
  in a dict and records every call in `calls` for AC 8 and AC 11. Its
  `create` makes the item folder under a `tmp_path` work root, so the layout
  has somewhere real. Its folder name is `<n>-<title words>`, it uses
  `apply_changes`, and it raises `NotFound`. A constructor flag sets
  `external_stages` and `inbox_items`, and a `stage=None` override puts an
  item in the "no stage" state.
- **Create** `tests/work/test_memory_backend.py`. It checks that the memory
  backend satisfies the protocol (`isinstance` against a
  `runtime_checkable` protocol). It also checks that `list` hides terminal
  stages unless `include_finished` is set, and filters by `parent`. These
  behaviors are what the later tasks lean on, so they must be pinned.
- **Proof:** `pytest tests/work -q`.

## Task 7: Built-in gates and drift (spec Design 7; AC 13, 14, 18)

- **Create** `tcw/work/gates.py` with:
  - `RecordsReader`, a protocol with `capability_status(path) -> str | None`
    (`None` means it does not resolve) and `term_exists(term) -> bool`;
  - `parse_capabilities_file(path) -> Declared | problem`, which uses the
    strict schema and has no `added:` alias;
  - `records_gate(layout, slug, reader) -> list[str]`;
  - `completion_gate(layout, slug, enabled, external) -> list[str]`;
  - `drift_problems(layout, completed_slugs, reader) -> list[str]`;
  - `ledger_reader(own, registry, project_id, open_child, taxonomy)`, the
    production `RecordsReader`. It routes every path through
    `route_capability_path`.
- **Move** `route_capability_path` and its `Route` NamedTuple from
  `tcw/work/recursion.py:195-253` into `gates.py`. **Modify**
  `tcw/work/recursion.py` to import both from `tcw.work.gates`. The behavior
  is unchanged.
- **Check for a cycle first.** `gates.py` must not import `recursion.py`.
  Check that `route_capability_path`'s own imports (the FS capability store
  type, used only in annotations) do not create a cycle. If one appears,
  keep the annotation as a string under `TYPE_CHECKING`.
- **Create** `tests/work/test_gates.py`, covering AC 13, 14 and 18 with a
  fake `RecordsReader`. Add one test that builds a `ledger_reader` over a
  real temporary `FsCapabilitiesStore`, to prove the production adapter
  resolves a local path and reports `Missing`.
- **Proof:**
  - `pytest tests/work -q`;
  - `pytest tests/test_capability_gate_children.py tests/test_recursion.py -q`,
    which still pass after the move.

## Task 8: `advance` (spec Design 6; AC 7–12)

This is the riskiest task. It comes after the table, layout, gates and
memory backend it composes, so every input is already tested.

- **Create** `tcw/work/advance.py` with:
  - `Outcome`, holding `code`, `stage`, `messages` and `overridden`;
  - `advance(backend, config, layout, project_root, slug, *, to=None, force=False, reason=None, dry_run=False) -> Outcome`;
  - `discard(...)`, which is `advance(to=DISCARD, ...)` and requires a reason.
- **The steps** follow spec Design 6.1–6.10 in order. Each numbered step is
  one small private function, so the spec's numbering maps onto the code.
- **Gates and hooks.**
  - Built-in gates come from `gates_for`.
  - Configured `pre` and `post` bindings run through
    `tcw.work.hooks.run_bindings` (`tcw/work/hooks.py:73`), after
    `tcw.work.resolve.select` (which applies `when:`).
  - The environment comes from a new local `_hook_env`. It sets `TCW_SLUG`,
    `TCW_STAGE`, `TCW_FROM_STAGE`, `TCW_ITEM_PATH` and `TCW_PROJECT_ROOT`,
    plus `TCW_FORCED` and `TCW_REASON` when forced.
  - `hooks.hook_env` is not changed, because 2.x still uses it.
  - Gate failures that `force` overrides go into `Outcome.overridden` and
    into the trace comment.
- **Errors.** Usage, not-found and refusal conditions raise or return the
  `WorkError` codes from Task 1. A comment failure after the move returns
  that error's code with the message "moved to X, but the trace comment was
  not posted".
- **Create** `tests/work/test_advance.py`, covering AC 7–12. It uses the
  memory backend. Hooks are real shell commands (`true` and `false`, and
  `sh -c 'exit 1'`) run through `run_bindings`, with `cwd=tmp_path`.
- **Cover the discard reason and the side stage too:**
  - `discard` without a reason is a `UsageError`;
  - `--to postmortem` is a `UsageError`.
- **Proof:** `pytest tests/work -q`.

## Task 9: References and stage-ahead checks (spec Design 9; AC 17)

- **Create** `tcw/work/references.py` with:
  - `reference_problems(items, current_project, resolve) -> list[Problem]`;
  - `stage_problems(items, layout, enabled) -> list[Problem]`;
  - `Problem`, holding `level` (`warning` or `unresolved`), `slug` and
    `message`.
- **Create** `tests/work/test_references.py` (AC 17).
- **Proof:** `pytest tests/work -q`.

## Task 10: Structural guards (AC 5, AC 19)

- **Create** `tests/work/test_model_guards.py`. It uses `ast` to walk the new
  modules (`advance`, `gates`, `layout`, `backend`, `references`, `config`,
  `model`) and `tcw/exit.py`.
- **AC 5.** No string constant equals a stage name in any module except
  `model.py`. In `model.py` they may appear only inside the `STAGES`
  assignment and `DISCARD`.
- **AC 19.** No module imports `subprocess`, `tcw.store.fs`'s git helpers
  (`git_stage`, `git_rm`, `git_mv`, `git_commit`, `git_commit_result`,
  `add_worktree`, `merge_worktree`, `remove_worktree`) or `publish`.
  `advance.py` reaches `subprocess` only through `tcw.work.hooks`.
- **Proof that the guards work.** Each guard is mutation-checked by hand
  before commit:
  - put a literal `"review"` into `advance.py` and an `import subprocess`
    into `layout.py`;
  - confirm each guard goes red, and why;
  - revert the mutations.
- **Proof:** `pytest tests/work -q`.

## Task 11: Documentation sync and the full suite (AC 20)

**Documentation Sync.** Each documentation entry was evaluated against this
change, which is internal and wires nothing into a command:

| Entry | Trigger | Fires? | Action |
| --- | --- | --- | --- |
| `README.md` | Public-API | No. No command, flag or output changes. | none |
| `docs/guide/jira.md` | Tracker-Change | No. `work.tracker` is untouched in 2.x, and the new parser is not live. | none |
| `docs/guide/<topic>.md` | Guide-Topic-Change | No. Nothing a guide names moves yet. | none |
| `docs/release-notes/upcoming/<slug>.md` | Public-API | No. Nothing is visible to users. | none |
| `docs/changelogs/upcoming/<slug>.md` | Any-Code-Change | Yes | **Create** `docs/changelogs/upcoming/2026-10-01-tcw-69-core-work-model-stage-table-item-folders-that-never-move-and-advance.md`. Under `## Internal`, say that the 3.0 work model was added (stage table, layout, backend protocol, `advance`, gates, config parser), not yet wired in. Under `## Changed`, say that `route_capability_path` moved to `tcw/work/gates.py`. |
| `skills/<component>/SKILL.md` | Skill-Driven-Component | No. The work component's CLI and behavior are unchanged until TCW-70. | none |
| `skills/configure/references/<document>.md` | Configuration-Key-Change | No. The new keys are not read by any command yet. TCW-70 and TCW-75 document them when they go live. | none |

Then:

- run the `documentation-sync` skill over the finished diff to confirm the
  table;
- run `pytest -q`, the whole suite, once (AC 20);
- run `tcw validate` from the primary checkout.

**Commit:** the changelog entry.

## Verification

**What the suite cannot check:**

- **That the design composes for real backends.** The memory backend proves
  the interface is implementable. It cannot prove that Jira's transition
  semantics or a filesystem `item.yaml` fit without strain. The check is
  reading, not testing: before handing over, re-read `backend.py` against
  TCW-70's and TCW-71's ticket text, and list any operation either would
  have to fake.
- **That the stage rules read naturally.** Write a few sentences tracing a
  bare `advance` through a project with review disabled and qa enabled, and
  check it against the spec by hand.
- **The guard tests are only as good as their mutation check** (Task 10).
  Record the mutation results in `outcome.md`.

## Notes

- **Blockers.** TCW-70, TCW-71, TCW-72, TCW-73 and TCW-77 build on this item,
  but none is a work item yet, so no `--blocked-by` can be recorded. When each
  is adopted, give it `--blocked-by` on this slug.
- **Self-review.** Every acceptance criterion maps to a task:
  - AC 1–4: Task 2;
  - AC 5: Tasks 3 and 10;
  - AC 6: Tasks 3 and 4;
  - AC 7–12: Task 8;
  - AC 13, 14 and 18: Task 7;
  - AC 15: Task 5;
  - AC 16: Task 4;
  - AC 17: Task 9;
  - AC 19: Task 10;
  - AC 20: Task 11.

  Task 1 and Task 6 are infrastructure for these.
