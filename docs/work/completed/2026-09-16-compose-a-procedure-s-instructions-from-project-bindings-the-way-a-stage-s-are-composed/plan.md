# Plan — Compose a procedure's instructions from project bindings the way a stage's are composed

Implements `spec.md` in this folder. Every task writes its failing test first
and commits alone; the suite is green at every commit.

Tests run from the worktree root against the worktree's own virtual environment,
never the shared editable install:
`PATH="$PWD/.venv/bin:$PATH" .venv/bin/pytest`. The CLI tests call `tcw` from
`PATH`, which is why `.venv/bin` goes first.

## Tasks

### 1. Procedure ids and their shipped default text

Covers spec criteria 2, 9, 10.

- **Modify** `tcw/store/base.py` — add `PROCEDURE_IDS` beside `STAGE_IDS`
  (`:932`), in the spec's order, with a comment that the ids are public API and
  do not follow skill names.
- **Create** `tcw/work/procedures/<id>.md` for all ten ids, each a verbatim copy
  of its source per the spec's table: a skill's body after its closing
  frontmatter `---` line, or the whole reference document.
- **Modify** `tcw/work/resolve.py` — `Builtins` gains
  `procedures: Mapping[str, str]`; `load_builtins()` loads it from
  `procedures/<id>.md` over `sorted(PROCEDURE_IDS)` through one helper shared
  with the stage-prompt loop, so the missing-file and empty-file refusals are one
  piece of code with the role named in the message ("built-in text for procedure
  '<id>' …").
- **Modify** `pyproject.toml` — `"tcw.work" = ["prompts/*.md", "procedures/*.md"]`.
- **Create** `tests/test_shipped_procedures.py`:
  - `set(load_builtins().procedures) == set(PROCEDURE_IDS)`;
  - parity: for each id, the default equals its source once both are stripped
    (the id→source map written out in the test, not derived, with a docstring
    telling a conversion child to change the row deliberately);
  - a missing file and an empty file each raise `ResolveError` naming a
    procedure id and `tcw/work/procedures` (monkeypatch `files` so only the
    procedure path fails, so the stage prompts loading first does not mask it);
  - the ten files are in a built wheel, reusing `_pristine_checkout` from
    `tests/test_shipped_prompts.py` by import.
- **Proof:** the new tests fail before the files and loader exist (`AttributeError`
  on `procedures`, then a parity failure if a file is edited), and pass after.
  Mutation check: delete one byte from one default and confirm the parity test
  names that id.

### 2. `work.procedures` parsing and validation

Covers spec criteria 8, 11.

- **Modify** `tcw/store/base.py`:
  - `LifecyclePolicy` gains `procedures: dict[str, list[Binding]]` and
    `procedure(id) -> list[Binding]` returning `[]` when unset;
  - new pure `parse_procedures(raw) -> tuple[dict[str, list[Binding]], list[str]]`:
    `None` → no problems; not a mapping → one problem; unknown id → problem
    naming `PROCEDURE_IDS`; value not a list → problem; empty list → the
    `_empty_prompt`-style refusal worded for a procedure; otherwise
    `_parse_binding_list(value, "work.procedures.<id>", problems, PROMPT_KINDS,
    "procedure")`;
  - `_parse_binding`'s `generate` hint (`:1848`) also fires for role
    `procedure`.
- **Modify** `tcw/store/fs.py`:
  - `lifecycle_policy()` (`:5372`) sets `policy.procedures` from
    `parse_procedures(self._work_config().get("procedures"))`, problems
    discarded;
  - `lifecycle_problems()` (`:5494`) appends `parse_procedures`'s problems, and
    `_file_binding_problems` (`:5499`) also checks each procedure's `file:`
    bindings under `work.procedures.<id>[i]`.
- **Create** `tests/test_procedure_config.py`: one test per spec criterion 8
  case against `parse_procedures`, each asserting the message names the location
  and the mistake; a `file:` that is missing and one that escapes through a
  symlink, through `FsWorkStore.check()`; a valid block yields no problem; and a
  malformed block leaves `tcw work list` exiting 0 (criterion 11).
- **Proof:** tests red with `ImportError`/missing problems before, green after.

### 3. Resolution

Covers spec criteria 3 and 4 at library level.

- **Modify** `tcw/work/resolve.py` — extract the body of `resolve_prompts`
  (`:443-467`) into a private `_compose(bindings, *, role, hook_id, builtins, …)`;
  `resolve_prompts` calls it with `policy.stage(stage_id) or [builtin]`,
  `role="prompt"`, and new `resolve_procedure(policy, procedure_id, item,
  node_root, builtins, artifacts=(), env=None, *, execute=True,
  documentation=())` calls it with `policy.procedure(procedure_id) or [builtin]`,
  `role="procedure"`, `builtins.procedures`. Phase stays `"prompt"`.
- **Create** `tests/test_resolve_procedure.py`: no bindings → the default text;
  `[blob A, builtin, blob B]` → exact composed string; `[blob A]` → `A` only; a
  conditional binding with and without a matching item; a `generate:` binding
  whose script echoes `$TCW_HOOK_ROLE/$TCW_HOOK_ID` and the stdin `hook.role`;
  `execute=False` runs no script and records `matched`/skipped plan entries.
- **Proof:** the existing `tests/test_resolve.py` and
  `tests/test_documentation_prompt.py` stay green unchanged — that is the
  evidence the extraction did not alter stage resolution.

### 4. `tcw work procedure prompt`

Covers spec criteria 1, 3–7 end to end.

- **Modify** `tcw/work/cli.py`:
  - `SUBCOMMANDS` (`:42`) gains `procedure`;
  - a `procedure` subparser group with one verb, `prompt <id> [slug] [--no-exec]`;
  - `_procedure_prompt(args)`: unknown id → refusal listing `PROCEDURE_IDS`,
    exit 1; no slug → `_store()` and `item=None`; slug → `_resolve(args.slug,
    "procedure prompt")`, `st.get`, `MultipleMatch` and not-found refusals worded
    as `stage prompt`'s; then resolve with `resolve_procedure`, print a
    `ResolveError` to stderr and exit 1; `--no-exec` prints the plan to stderr
    only; otherwise print the text if non-empty, and print the spec's stderr note
    when the text is empty and any plan entry was skipped by its condition (its
    second sentence only when no slug was given). No bookend, no harness check.
- **Create** `tests/test_procedure_verb.py` against real `tmp_path` git nodes
  built with `init(["work"], …)`, with the config written explicitly per test
  (no fixture default for `work.procedures`): every id prints its default file
  and exits 0 in an unconfigured node; configured composition order; tag
  condition with a tagged and an untagged item; `generate:` receives the item
  JSON; the conditional-only note with no slug, and its absence for
  `[{blob: ""}]`; unknown id, unknown slug, deleted `file:` each exit 1 with empty
  stdout; `--no-exec` creates nothing a script would have created; a
  `<project-id>/<slug>` reference reads the owning node's `work.procedures`.
  Where a message is asserted, also assert the argparse `invalid choice` text is
  absent, so the test cannot pass on argparse's own error.
- **Proof:** red with argparse's `invalid choice: 'procedure'` before, green
  after; run `.venv/bin/tcw work procedure prompt delegation` by hand and diff it
  against `skills/tcw-work/references/procedures/delegation.md`.

### 5. Capabilities ledger

Covers spec criterion 13.

- Run with `.venv/bin/tcw`, whose capabilities code this item does not modify:
  - `tcw capabilities add work/run-a-procedure "Run a procedure" --status Missing`
    and `tcw capabilities add work/configure-procedures "Configure procedures"
    --status Missing`;
  - `tcw capabilities set <path> --field "Planning doc=<slug>"`,
    `--field Feature=configurable-work-lifecycle`, and `--field
    Subject=work-item/lifecycle-hook` on each;
  - write each `description.md` in the ledger's plain user voice.
- **Modify** `docs/capabilities/work/configure-the-work-lifecycle/description.md`
  — one sentence: `timeout` and `output-cap` also bound a procedure's
  `generate:` script.
- **Create** `capabilities.yaml` in this item's folder with `new:` and `changed:`
  as the spec lists.
- **Proof:** `.venv/bin/tcw capabilities check` exits 0. The two new entries stay
  `Missing` until the coordinating session's `complete` flips them — this child
  runs no transition.

### 6. Documentation Sync

One pass over the finished diff, committed separately from code.

- `README.md` **[Public-API]** — fires: new verb and new key. Add a
  `tcw work procedure` row to the command table (`:621`) and a short paragraph
  where `work.lifecycle` configuration is introduced.
- `docs/release-notes/upcoming.md` **[Public-API]** — fires: a plain-language
  entry that a project can now replace TCW's own text for ten named procedures.
- `docs/changelogs/upcoming.md` **[Any-Code-Change]** — fires: Added entries for
  `PROCEDURE_IDS`, `tcw/work/procedures/`, `work.procedures`,
  `resolve_procedure`, the verb; Internal entry for the `_compose` extraction.
- `skills/<component>/SKILL.md` **[Skill-Driven-Component]** — fires for
  `tcw-work`. `SKILL.md` body is 59/60 lines, so it gains no line; add the verb to
  `references/commands.md` and a `procedure` row to the roles table in
  `references/hooks.md`.
- `skills/tcw-configure/references/<document>.md` **[Configuration-Key-Change]**
  — fires: a `work.procedures` section in `work.md` with the id list, the plain
  list shape, the empty-list refusal, the shared limits, and the conditional-only
  case.
- `docs/guide/jira.md` **[Tracker-Change]** — does not fire.
- Not an entry, evaluated anyway: `docs/guide/configuration.md` documents
  `tcw work stage prompt` for users; add a short "procedures" paragraph there.
- **Proof:** `tests/test_documented_cli_surface.py` and
  `tests/test_skill_lifecycle_parity.py` green.

### 7. `outcome.md`

Write it after a fresh full suite run and commit it alone.

## Verification

What the suite cannot check:

- **That a skill reading the command still works as a skill.** No skill reads
  it yet; that is each conversion child's end-to-end check.
- **That the ids are the right names.** A judgment for the requester, listed in
  the spec's Notes.
- **Codex parity.** The command is plain CLI output with no harness branch, so it
  reads identically; there is no injected-context path in this child to check
  under Codex.

## Notes

- **Stage gate not run.** `tcw work stage gate plan <slug>` refused — "'plan' is
  not legal for an item in 'active'; it runs in backlog" — because the
  coordinating session started the item before planning, and the requester chose
  to proceed without moving it back.
- **What skipping it skipped.** `tcw work lifecycle` shows one `pre:` check on
  `plan`: `python scripts/require_artifact.py spec`. It was run by hand with
  `TCW_SLUG` set to this item and exited 0, so the check the gate would have run
  did run. The legality check is the only part not satisfied.
- No blockers to record: the routing item this epic waited on is merged, and
  `tcw work stage validate` and harness detection exist in the tree
  (`tcw/work/cli.py:1528`, `tcw/harness.py`).
- Plan step 7 of the stage prompt says to run `tcw work start` after committing
  the plan; the item is already active, and the brief forbids transitions.
