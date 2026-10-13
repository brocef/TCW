# Plan — Rewrite stage prompts, procedures and skills for the new lifecycle

This plan follows the spec as reviewed on 2026-10-02. Each task is one commit
on `work/2026-10-01-tcw-74-rewrite-stage-prompts-procedures-and-skills-for-the-new-lifecycle`,
made from `epic/tcw-3.0` at `58da5913`, and the tests the task names pass
after it. The order is the one the spec's Risks section asks for: the
mechanism first (the backend filter, the loader, the generated text), then the
prompts, then the procedures, then the skills and agents, then the guards that
hold all of that text, then the evals, and last the records and release
entries.

## Before the first task

**What TCW-69 to TCW-73 left, read on the branch at `58da5913`.**

- `tcw/work/resolve.py`: `compose()` resolves each binding (`blob`, `skill`,
  `builtin`, `file`, `generate`) to text, joins the parts, then substitutes
  `{{tcw:documentation}}` and `{{tcw:request}}`. `load_builtins()` loads a
  prompt only for a stage whose `prompt` column is yes **and whose file
  exists**, so a missing file is silently skipped today (that is how `review`
  and `qa` are absent without an error). `stage_header(stage, target)` is the
  only generated text; **there is no footer at all** on the branch
  (`STAGE_NEXT_STEPS` and `bookend` went with TCW-70).
- `tcw/work/cli.py`: `_stage_prompt` puts the header above the composed text
  and substitutes the slug only in the header. `_procedure` prints
  `packaged_text("procedures", id)` unchanged outside a project.
- `tcw/work/model.py` holds the stage table (`STAGES`), the only place a stage
  is named. Each backend declares `external_stages` (filesystem: none; Jira:
  request and qa, `tcw/work/jira/backend.py:59`).
- `PROCEDURE_IDS` is still in `tcw/store/base.py:651`; `tcw/config.py:204`,
  `tcw/work/config.py:418`, `tcw/work/resolve.py` and `tcw/work/cli.py:482`
  read it.
- The packaged `spec.md` and `plan.md` already use `{{tcw:request}}`
  (TCW-70); no shipped file uses `{{tcw:body}}`; `tcw/work/templates.py` is
  gone.
- `tcw work path <slug> <stage> [--next | --handoff]`, `tcw work show <slug>`
  (properties, then the request, then comments newest first),
  `tcw work comment <slug>` (text on stdin), `tcw work advance <slug> [--to
  <stage>] [--force] [--reason] [--dry-run]`, `tcw work discard <slug>
  --reason`, `tcw work list --stage/--tag/--parent/--mine/--all`,
  `tcw work tickets list [--json]`, `tcw work tickets adopt <KEY>` and
  `tcw validate --remote` all exist.
- `tcw capabilities add <path> <title>` takes a title argument and defaults
  `--status` to `Missing` (`tcw/capabilities/cli.py:260`).
- A Jira ticket key given to `tcw work comment` is looked up as an item
  (`tcw/work/cli.py:58-63`): a ticket in the inbox has no item, so the
  command exits 4 there.
- Tests skipped with a reason naming TCW-74: `tests/test_prompt_fallback.py`,
  `tests/test_skill_flow.py`, `tests/test_skill_lifecycle_parity.py` and the
  five `tests/test_eval_*.py` files.
- `tests/doc_allowance.py` lists removed commands, flags, forms and refused
  keys that documents may still name; `tests/test_documented_cli_surface.py`
  reads it for every Markdown file in the repository.

**Which source runs.** A private virtual environment at
`<scratch>/tcw74/venv` (`python -m venv --system-site-packages`, then
`pip install -e <worktree> --no-deps`). pytest and the CLI run with the
worktree as the current folder, the venv first on `PATH` and
`PYTHONDONTWRITEBYTECODE=1`. The CLI is tried by hand only in scratch folders
with `HOME` and `XDG_CONFIG_HOME` pointed at scratch folders. The board on
`main` is driven by the released 2.8.1 `tcw`, never by the worktree's code;
plan, outcome, `capabilities.yaml` and spec notes are committed on `main`.

**Tests, per the owner's rule for this epic.** The full suite is not run. Each
task runs the test files it names, the files under `tests/` that read what it
changed (found with `grep -rl`), and always the standing files:
`tests/test_cli_contract.py`, `tests/test_cli_help_standard.py`,
`tests/test_static_guards.py`, `tests/test_cli_handler.py`,
`tests/test_tree_store_raises.py`, `tests/test_no_node.py`,
`tests/test_ledger_3_0.py`, `tests/test_documented_cli_surface.py`,
`tests/test_doc_allowance.py`. A 2.x test that breaks because 2.x behavior is
removed may be deleted; each one is listed in `outcome.md`. The last task ends
with `pytest --collect-only -q` clean.

## Where the spec predates TCW-72 or TCW-73, and the later decision wins

1. **`tcw work procedure prompt <id>` is `tcw work procedure <id>`**
   (TCW-73). Every skill that injects a procedure injects the new form, and
   the tests look for it.
2. **"node" is "project"** everywhere in the shipped text (TCW-73).
3. **`connected-projects` is `projects`** (TCW-73); the spec already says so.
4. **`builtin: true` is `inherit: true`** in bindings (TCW-72). TCW-75's
   vocabulary table deliberately leaves `builtin: true` out (TCW-75 spec,
   criterion 2, its [Decision]), because `tcw config show` prints it. Criterion
   8's mutation check expects `builtin: true` in a skill to fail TCW-74's scan,
   so TCW-74's scan uses TCW-75's shared table **plus** a short list of its own
   (choice 4).
5. **`TCW_WORK_OWNER` and `--owner` are gone**: identity is `user.name`, and
   the flags are `--assign-me` and `--mine` (TCW-72).
6. **`tcw capabilities add` needs a title** (TCW-73's surface): every example
   the skills show is `tcw capabilities add <path> "<title>" --status
   Supported`.
7. **`tcw work comment <KEY>` on an inbox ticket exits 4** (TCW-71 settled the
   open question in the spec's Notes by refusing). The Jira inbox passage
   therefore puts the reason for turning a ticket away in the agent's report,
   for the person who closes it, which is the spec's own fallback; it still
   names `tcw work comment` for recording an arrival on an existing item.
   A dated implement-finding note goes into the spec.
8. **`PROCEDURE_IDS` is still in `tcw/store/base.py`**; Design 5.4 says to edit
   it wherever it lives, so it is edited there.

## Choices this plan makes

1. **The filter is `filter_backend(text, backend)` in a new module,
   `tcw/work/passages.py`**, so the stage prompts, the procedures and the
   tests import one function. It raises `BackendError` (exit 1) with the line
   number and the problem. `compose()` calls it on each binding's text before
   joining, and re-raises with the binding named (`file prompts/spec.md`,
   `generate ./x.sh`, `built-in prompt for spec`). `backend` is
   `config.backend`; outside a project it is `None`, which removes every
   passage.
2. **The loader is strict both ways.** `load_builtins()` loads exactly the
   stages whose `prompt` column is yes, and also lists `tcw/work/prompts/`:
   a `.md` file there with no such stage (`verify.md`, `completed.md`) is a
   `ResolveError` naming the file. The same for `tcw/work/procedures/` against
   `PROCEDURE_IDS`.
3. **The footer and header live in `tcw/work/resolve.py`** as
   `stage_header(stage, target)` and `stage_footer(row, external, target)`,
   taking a `Stage` row and a set of external stage names, never a stage name
   to compare against. `_stage_prompt` passes `backend.external_stages`.
   `<slug>` is substituted in the whole output (header, text, footer) by
   `_stage_prompt` when a reference is given.
4. **The shared vocabulary helper is `tests/doc_vocabulary.py`**: `PATTERNS`,
   TCW-75's table verbatim as `(pattern, reason)` pairs, and `scan(text)`
   returning `(line_number, matched_text, reason)`. TCW-74's own scan
   (`tests/test_shipped_text.py`) adds `EXTRA_PATTERNS` that only it applies:
   `builtin: true` (TCW-72 made it an error in a file), `TCW_WORK_OWNER` is
   already in the shared table, `--owner` (TCW-72), `work-stage` (a deleted
   skill), `procedure prompt` (TCW-73's removed form) and `Planning doc`
   (TCW-73 removed the field).
5. **The git scan, the vocabulary scan, the commands scan and the disposition
   checks live in one new file, `tests/test_shipped_text.py`**, because they
   share the file walk (every `.md` under `skills/` except `skills/configure/`,
   `agents/`, `tcw/work/prompts/`, `tcw/work/procedures/`) and its exclusion
   list. Each scan's allowlist is a named constant with a reason per entry.
6. **The commands scan reuses `tests/test_documented_cli_surface.py`'s
   extraction** (`_invocations`) and checks against `build_parser()` directly
   (no subprocess walk). It also checks two positional values the parser
   cannot: the word after `tcw work procedure` must be a procedure id or a
   placeholder (`<id>`), and the word after `tcw work stage prompt` must be a
   stage with a prompt or a placeholder. That is what catches
   `tcw work procedure prompt <id>`, which the parser accepts.
7. **Pause handoffs.** `commands-pause-work` writes the handoff through
   `tcw work path <slug> <stage> --handoff` when the stage has a folder; as a
   comment whose first line is `Handoff` when the stage is external; nothing
   at inbox or with no item (Design 7's row). Its conduct comes from the new
   `pause-work` procedure, injected with `` !`tcw work procedure pause-work` ``
   and named in its `## Document command summary`.
8. **`skills/README.md` keeps its two rules and verdict vocabulary** and
   replaces its table with one row per remaining document. `commands-pause-work`
   becomes "composes already" (its conduct now comes from the `pause-work`
   procedure), so its `dynamic_skill` stays `true`.
9. **The reviewer agent's file is `agents/reviewer.md`** with `name: reviewer`;
   it reads `tcw work stage prompt review <slug>` rather than carrying review
   steps, so a project's replacement reaches it.
10. **The 2.x prompt-fallback fixture is re-captured** by the rewritten
    `tests/fixtures/prompt_fallback/capture.py`, which walks a 3.0 item with
    `advance` through request, spec, plan, implement, review, qa and records
    postmortem, in its own commit (Task 4), after the prompt text (Task 2) and
    the generated text (Task 3) are final.
11. **Scenario row 4** (`tests/cli/scenarios/13-release-integrity.md`) is
    widened to every stage worked in, as the lead asked, although the spec's
    Non-goals give `tests/cli/scenarios/` to TCW-73: the row itself waits on
    this slice and says so.
12. **The eval rewrite is done by one helper agent** working in this
    worktree on `evals/` and `tests/test_eval_*.py` only, against a brief
    quoting Design 11 and criterion 12; I review its diff and run its tests
    before committing (Task 12).

## Tasks

**Every task that deletes a skill, reference or agent** (Tasks 6-9) also
removes that document's row from `skills/README.md` and, for a skill, its name
from `.codex-plugin/plugin.json`'s `longDescription` with the count corrected,
so `tests/test_dynamic_skill_marker.py` and `tests/test_plugin_manifests.py`
stay green at each commit. Task 9 then rewrites both in full.

### Task 1: Backend passages (Design 3)

- **Create `tcw/work/passages.py`**: `BACKEND_OPEN`
  (`<!-- backend: <name> -->`), `BACKEND_CLOSE` (`<!-- /backend -->`),
  `filter_backend(text, backend)`. Unknown name (not in
  `tcw.work.config.BACKENDS`), nested passage, unterminated passage and stray
  close each raise `BackendError` naming the line.
- **Modify `tcw/work/resolve.py`**: `compose()` filters each binding's text
  before `_join`; a failure is re-raised as `ResolveError` naming the binding
  (`_resolved` turns it into exit 1). Order: filter, then documentation, then
  request (Design 3.5).
- **Modify `tcw/work/cli.py` `_procedure`**: outside a project, the packaged
  text is filtered with `backend=None`.
- **Create `tests/work/test_backend_passages.py`**: criterion 4 (a `jira`
  passage removed for `filesystem` and kept without markers for `jira`; the
  four errors; `None` removes both kinds and keeps the rest; a passage inside
  a list item; a documentation span inside a passage still substitutes; every
  built-in prompt and procedure filters cleanly for both backends and for
  `None`; a project `file` binding with a `jira` passage on a filesystem
  project omits it; an unterminated passage in a `file` binding makes
  `tcw work stage prompt` exit 1 with stderr naming the file).
- Proof: the new file; `tests/work/test_compose.py`,
  `tests/test_procedure_verb.py`, `tests/config/test_personal_origins.py`,
  standing files.

### Task 2: The eight prompts and a strict loader (Design 1, 2)

- **Modify `tcw/work/resolve.py` `load_builtins`/`_load_texts`**: choice 2.
- **Delete `tcw/work/prompts/verify.md`. Create `tcw/work/prompts/review.md`,
  `tcw/work/prompts/qa.md`. Rewrite `inbox.md`, `request.md`, `spec.md`,
  `plan.md`, `implement.md`, `postmortem.md`** to Design 1-2: Purpose /
  Inputs / Produce / `## Steps` / `## Exit badly`; paths only through
  `tcw work path`; the resume rule (newest handoff first; `Handoff` comments
  in the Jira passages of request and qa); backend passages where the spec
  gives them; the request template's five sections; the QA plan comment;
  `capabilities.yaml` as the one named file; the implement round's five
  contents and "written once, at the end"; the latest-rejection rule with
  `judges` and, Jira only, the qa move comment; review and qa front matter;
  the person-decides sentence with `decided-by` and `qa --next`; postmortem
  absorbing the `post-mortem` procedure's investigation without its history
  step and defining the request-level comment as opt-in. No git words, no 2.x
  vocabulary, no skill names. Each at most 60 lines after filtering.
- **Rewrite `tests/test_shipped_prompts.py`**: criteria 1 (the set from the
  table; `verify.md` absent; a missing file and an extra `completed.md` each
  fail loading naming the file; the wheel holds exactly the set), 2 (60
  lines per backend) and 3 (every mechanical content check, per backend,
  through `filter_backend`), plus the kept checks (no `tcw work lifecycle
  --stage`, no sub-skill names, self-review in exactly spec, plan and
  implement).
- **Modify `tests/test_documentation_sync_wiring.py`**: `LIFECYCLE_REFS` points
  at `tcw/work/prompts/plan.md` and `implement.md`, which carry
  `INVOKE_PHRASE`.
- **Modify `tests/test_falsification_rule.py`, `tests/test_documentation_prompt.py`**
  for the new implement and plan text (Design 12).
- Proof: those files; `tests/work/test_compose.py`, `tests/work/test_cli_config.py`,
  `tests/test_stage_verb.py`, `tests/config/`, standing files.

### Task 3: Header, footer and `<slug>` (Design 4)

- **Modify `tcw/work/resolve.py`**: `stage_header` (no checks ran; gates run on
  a move; `advance --dry-run`), `stage_footer(row, external, target)` with
  Design 4.1's four rules in order. No stage or backend name in either.
- **Modify `tcw/work/cli.py` `_stage_prompt`**: header and footer around the
  text; with a reference, every literal `<slug>` in the output becomes the
  full slug.
- **Create `tests/work/test_stage_bookends.py`**: criterion 5 (postmortem's
  side-stage sentence; inbox has no footer; filesystem footers name
  `tcw work advance <slug>` substituted; Jira project through the fake: request
  and qa get the external sentence and no `tcw work advance`, spec, plan,
  implement and review the advance footer; the stand-in backend with
  `external_stages={"spec"}`; no `<slug>` left with a reference; a source scan
  of `stage_header` and `stage_footer` for stage and backend names;
  `{{tcw:body}}` in no shipped file, `spec.md` and `plan.md` carry
  `{{tcw:request}}`, `tcw/work/templates.py` absent).
- Proof: the new file; `tests/test_stage_verb.py`, `tests/work/test_cli_surface.py`,
  `tests/test_cli_contract.py` and the other standing files.

### Task 4: Re-capture the unconfigured-prompt fixture (Design 12)

- **Rewrite `tests/fixtures/prompt_fallback/capture.py`** for a 3.0 walk
  (`new`, then `advance` with the documents written through `path`, and an
  accepted review round so the walk reaches qa); **re-capture
  `tests/fixtures/prompt_fallback/unconfigured.json`**; **rewrite
  `tests/test_prompt_fallback.py`** to replay the same walk, its skip removed.
  This commit changes no prompt text.
- Proof: `tests/test_prompt_fallback.py` passes; changing one word of
  `tcw/work/prompts/plan.md` makes it fail (checked, restored).

### Task 5: The procedure set (Design 5)

- **Modify `tcw/store/base.py` `PROCEDURE_IDS`** to `documentation-sync`,
  `create-work`, `audit-backlog`, `search`, `triage-issues`,
  `unattended-work`, `pause-work`.
- **Delete `tcw/work/procedures/post-mortem.md`, `consolidate-plans.md`,
  `decompose.md`, `delegation.md`. Create `pause-work.md`. Rewrite
  `create-work.md`, `audit-backlog.md`, `search.md`, `triage-issues.md`,
  `unattended-work.md`**; edit `documentation-sync.md`'s 2.x work wording only.
  Backend passages where filesystem and Jira differ (inbox tickets, external
  stages).
- **Delete `skills/work/references/procedures/`** (five files).
- **Rewrite `tests/test_shipped_procedures.py`**: criterion 6's set, one file
  each, no source map, the folder gone; the two agents' checks move to Task 9.
- **Modify `tests/test_procedure_config.py`** (criterion 6:
  `work.procedures.delegation` is a problem naming the known ids),
  **`tests/test_procedure_verb.py`**, **`tests/test_unattended_work_skill.py`**
  as far as they read the procedure text.
- Proof: those files; `tests/work/test_config.py`, `tests/config/`,
  standing files.

### Task 6: The work skill (Design 7, "What the work skill carries")

- **Rewrite `skills/work/SKILL.md`** and **`skills/work/references/commands.md`**
  (the 3.0 surface from `tcw work --help` and each leaf's help; no tracker,
  claim or strict-mode sections); **edit `skills/work/references/tags.md`**
  ("node" becomes "project").
- **Delete** `skills/work/references/transitions.md`, `hooks.md`,
  `epic-deltas.md`, `cross-node-deltas.md`, `skills/work/references/lifecycle/`
  (seven files) and `skills/work-stage/`.
- **Delete `tests/test_skill_lifecycle_parity.py`.** **Modify
  `tests/test_configuration_text_home.py`**: delete only
  `test_tcw_work_keeps_only_the_runtime_tracker_text`.
- Proof: `tests/test_documented_cli_surface.py` (the work skill files),
  `tests/test_dynamic_skill_marker.py`, `tests/test_skill_path_pointers.py`,
  `tests/test_plugin_manifests.py`.

### Task 7: The command skills (Design 7 rows)

- **Rewrite `skills/commands-process-inbox/SKILL.md`,
  `skills/commands-plan-work/SKILL.md`,
  `skills/commands-drive-work-to-completion/SKILL.md`,
  `skills/commands-pause-work/SKILL.md`** (choice 7). **Delete
  `skills/commands-verify-work/`.**
- Proof: `tests/test_dynamic_skill_marker.py`, `tests/test_plugin_manifests.py`,
  `tests/test_documented_cli_surface.py`.

### Task 8: The other skills (Design 7, 8, 9)

- **Rewrite `skills/capabilities/SKILL.md`** (Design 8, the reversal).
- **Rewrite `skills/taxonomy/SKILL.md`** (terms change in implement with the
  code; "project"; `:33` without git; `:122` kept as an allowlisted fact).
- **Rewrite `skills/setup/SKILL.md`, `skills/setup/references/project.md`**;
  **create `skills/setup/references/jira.md`** (Design 9).
- **Rewrite `skills/work-create/SKILL.md`,
  `skills/work-create/references/find-overlap.md`.**
- **Rewrite `skills/extras-autonomous-work/SKILL.md`,
  `skills/extras-triage-issues/SKILL.md`; edit `skills/extras-report/SKILL.md`**
  (removed-verb examples, "tracker").
- **Edit `skills/documentation-sync/SKILL.md`** and
  **`skills/documentation-sync/references/release-notes-and-changelogs.md`**
  (2.x work words; `upcoming/` files named by the item's folder name).
- **Delete `skills/post-mortem/`.**
- Every skill this slice owns loses `Bash(git *)` / `Bash(git merge *)`.
- Proof: `tests/test_unattended_work_skill.py`, `tests/test_dynamic_skill_marker.py`,
  `tests/test_documented_cli_surface.py`, `tests/test_skill_path_pointers.py`,
  `tests/test_plugin_manifests.py`.

### Task 9: Agents, the verdict table and the plugin manifest

- **Delete `agents/verifier.md`, `agents/post-mortem.md`. Create
  `agents/reviewer.md`. Rewrite `agents/backlog-auditor.md`** (reads
  `tcw work procedure audit-backlog`; no history reads, `state.yaml` or
  removed verbs).
- **Rewrite `skills/README.md`** (choice 8).
- **Modify `.codex-plugin/plugin.json` `longDescription`** for the fourteen
  skills. Check `.claude-plugin/plugin.json` for an `agents` list naming the
  old files.
- **Modify `tests/test_shipped_procedures.py`**: the backlog-auditor check,
  for `tcw work procedure audit-backlog`.
- Proof: `tests/test_dynamic_skill_marker.py`, `tests/test_plugin_manifests.py`,
  `tests/test_shipped_procedures.py`.

### Task 10: The guards on shipped text (Design 6, 10; criteria 7-10)

- **Create `tests/doc_vocabulary.py`** (choice 4) and
  **`tests/test_shipped_text.py`** (choice 5): the git scan with its
  two-entry allowlist and the `skills/configure/` exclusion; no `git` in an
  owned skill's `allowed-tools`; the vocabulary scan; the commands scan
  (choice 6) accepting an allowance-list entry only inside
  `skills/configure/`; no allowance entry named only by files this slice
  owns; the exact file set under `skills/` and `agents/` (outside
  `skills/configure/`); every `` !` `` injection has a
  `## Document command summary` naming the same command; the pause skill names
  `--handoff`, the `Handoff` comment and inbox; criterion 10's checks on
  `skills/capabilities/SKILL.md`; the Codex count (already in
  `test_plugin_manifests.py`; this only adds "names no deleted skill").
- **Modify `tests/doc_allowance.py`**: remove each entry no remaining file
  names, recording in `outcome.md` the ones left, with the file and owner.
- **Modify `tests/test_documented_cli_surface.py`**: delete
  `_declares_a_missing_capability` and its use.
- **Fix whatever text the guards find**, in this commit.
- Proof: the new file; `tests/test_doc_allowance.py`,
  `tests/test_documented_cli_surface.py`; the mutation checks of criteria 8
  and 9, recorded in `outcome.md`.

### Task 11: The 3.0 product flow (criterion 13)

- **Rewrite `tests/test_skill_flow.py`**, skip removed: a filesystem project
  with spec, plan and review enabled; `new`; `advance` to spec; write
  `capabilities.yaml` declaring `new: [billing/refund]`; `advance` to plan,
  then implement; `tcw capabilities add billing/refund "Refund a payment"
  --status Supported` plus an implement round; a bare `advance` exits 0 into
  review. The same with a bare `capabilities add` exits 3.
- Proof: the file.

### Task 12: The eval harness (Design 11; criterion 12)

- **Rewrite `evals/seed_fixture.py`, `evals/evals.json`, `evals/grade.py`,
  `evals/run_evals.py`, `evals/coverage.py`** as Design 11 says, and
  **`tests/test_eval_coverage.py`, `test_eval_files_changed.py`,
  `test_eval_fixture.py`, `test_eval_grading.py`, `test_eval_runner.py`**, each
  skip removed. Done by one helper agent (choice 12), reviewed by me.
- Proof: the five test files; `python evals/seed_fixture.py --customized
  <dir>` and `--bare <dir>` exit 0; `python evals/coverage.py` reports no
  uncovered skill; `python -m evals.run_evals --axis a --dry-run` lists both qa
  cases. No run without `--dry-run`.

### Task 13: Records (Capability changes; criterion 11)

- **Delete** `docs/capabilities/skills/commands-verify-work/`,
  `docs/capabilities/skills/work-stage/`, `docs/capabilities/skills/post-mortem/`
  and `docs/taxonomy/commands-verify-work-skill/`,
  `docs/taxonomy/work-stage-skill/`, `docs/taxonomy/post-mortem-skill/`
  (and any relation to them in other entries).
- **Modify** the `description.md` (and `meta.yaml` name where it is wrong) of
  the fourteen `changed` records; drop any `Planning doc` or `Tracker` line in
  a record touched.
- **Write `capabilities.yaml`** in the item folder on `main`.
- Proof: `tests/test_ledger_3_0.py`, `tests/test_capability_ref_wording.py`,
  `tcw validate` in a copy of the worktree's records with a 3.0
  `tcw-config.yaml` (this repository's own is still 2.x), and
  `records_problems(..., finished=True)` over the item's `capabilities.yaml`.

### Task 14: The scenario row, release notes and changelog

- **Modify `tests/cli/scenarios/13-release-integrity.md`** row 4 (choice 11).
- **Create `docs/release-notes/upcoming/<slug>.md`** and
  **`docs/changelogs/upcoming/<slug>.md`**, each starting with a `##`
  heading.
- Proof: `tests/test_upcoming_entries.py`.

### Task 15: Mutation checks and collection

No new behavior. Each guard under "Mutation checks" below is broken on
purpose, seen red for the stated reason, and restored; results go to
`outcome.md`. Then `pytest --collect-only -q` with no errors. No commit unless
a mutation exposes a gap, in which case the fix and its test are the commit.

## Documentation Sync

| Entry | Fires | Handled |
| --- | --- | --- |
| `README.md` [Public-API] | Yes: skills removed, stage prompts change | Deferred to TCW-75, which rewrites the README for 3.0 (spec Non-goals). |
| `docs/guide/jira.md` [Tracker-Change] | Yes: what the Jira inbox, request and qa prompts tell an agent | Deferred to TCW-75. |
| `docs/guide/<topic>.md` [Guide-Topic-Change] | Yes: `docs/guide/work.md` names `verify`, `work-stage` and the deleted skills | Deferred to TCW-75. |
| `docs/release-notes/upcoming/<slug>.md` [Public-API] | Yes | Task 14. |
| `docs/changelogs/upcoming/<slug>.md` [Any-Code-Change] | Yes | Task 14. |
| `skills/<component>/SKILL.md` [Skill-Driven-Component] | Yes: this slice is the rewrite | Tasks 6-9. |
| `skills/configure/references/<document>.md` [Configuration-Key-Change] | Yes in part: `work.procedures` ids change (`pause-work` added, four removed) | Deferred to TCW-75, which owns `skills/configure/` (epic decision 3); named in the outcome's notes for TCW-75. |

## Mutation checks (Task 15)

- Criterion 8: "commit" added to `tcw/work/prompts/plan.md` → the git scan fails
  naming the file and line; `outcome.md` added to
  `skills/extras-autonomous-work/SKILL.md` and `builtin: true` to
  `skills/work/SKILL.md` → the vocabulary scan fails naming each file.
- Criterion 9: `tcw work start <slug>` added to `skills/work/SKILL.md` → the
  commands scan fails naming the file; `tcw work procedure prompt pause-work`
  → it fails on the procedure id.
- The filter ignoring the backend name (keeping every passage) → criterion 4's
  removal case goes red.
- The footer keyed on `row.name == "qa"` instead of `external` → the stand-in
  backend case goes red.
- The loader skipping a missing prompt file again → criterion 1's missing-file
  case goes red.
- `<slug>` substituted only in the header → the no-`<slug>`-left case goes red.

## Verification

What the suite cannot see, checked by reading and by hand in a scratch folder,
recorded in `outcome.md`:

- Each prompt read in full for both backends (`tcw work stage prompt <stage>
  <slug>` in a filesystem scratch project, and the filtered text through
  `filter_backend` for Jira), for plain language and for agreement with the
  stage table: what it reads, what it writes, who moves the item.
- The jira-filtered qa prompt names `--reason` only in text addressed to the
  person deciding (criterion 3's last part, checked by reading).
- Every rewritten skill read once start to end under the assumption that the
  reader runs Codex: no step depends on an injection with no fallback.
- `tcw work procedure pause-work` and `tcw work procedure create-work` outside
  any project print text with no backend markers.

## Notes

- **Self-hosting.** This slice edits `tcw/`; the board is driven by the
  released 2.8.1 `tcw` from the primary checkout.
- **Not done here, by the spec:** `skills/configure/` and its references,
  README, guides and `docs/lifecycle/*.md` (TCW-75); this repository's
  bindings, `docs/procedures/` and `AGENTS.md` (TCW-76); `tcw/serve/` and the
  viewer (TCW-77). The inbox entry about `docs/lifecycle/implementation.md`
  naming `descendant_nodes` and `--include-descendants` falls to TCW-75
  (that file is in its inventory, Design 7.2) and is left alone here.
