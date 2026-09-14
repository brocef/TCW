# Plan — Restructure TCW's skills: setup and configure skills, command and extras skills, and no slash commands

Implements `spec.md`. "AC n" refers to its acceptance criteria and "Dn" to its
design sections. Carved from the original item's plan as of `9fbaa25a`, with that
item's round-three review findings applied.

## Before starting

- **Blocked** by
  `2026-09-14-make-eval-checks-measure-what-the-agent-did-working-tree-file-changes-tool-call-routing-and-named-fixture-variants`.
  Tasks 7 and 10 use its `tool_input_*` predicates and `bare` fixture.
  `tcw work start` refuses until that item completes.
- **Check the tracker item first.** At `tcw work start`, see whether
  `2026-09-12-configure-an-external-tracker-and-read-its-tickets` has completed.
  If it hasn't, task 6 moves `skills/tcw-work/references/commands.md:93-100` as it
  stands on `main` that day, and the note in task 12 tells that item where the text
  went.
- **No `tcw/` code changes.** This item edits no code under `tcw/`, so driving the
  lifecycle with the `tcw` CLI is safe.
- **Record `<base>`**, the commit that last touched this `plan.md`, in `outcome.md`
  when the item starts. AC 11 is checked against it.
- **Every commit leaves bare `pytest` green.** Each task names the tests it must
  keep passing, and ends with bare `pytest -q`.
- **Line numbers are as of `<base>`.** Where an earlier task already edited a file,
  find the passage by its text.

## Tasks

### Phase A — Fewer skills, clearer names

#### Task 1 — Delete the five per-stage skills

Spec D8, revision note 13.

Everything in this task is **one commit**. Dropping the exclusion while the skill
still exists, or deleting the skill while the manifest still names it, would fail
the tests.

**Tests and evals**

- **Modify `tests/test_skill_lifecycle_parity.py` (`:305-375`):**
  - delete `NO_PER_STAGE_SKILL`, `PER_STAGE_IDS`, `PER_STAGE_SKILLS`,
    `test_the_per_stage_skills_are_exactly_the_stages_that_get_one`, and
    `test_a_per_stage_skill_takes_the_item_alone`;
  - set `COMPOSING_SKILLS = {None: STAGE_SKILL}`, so the `@composing` tests run
    against `tcw-work-stage` alone;
  - rewrite the section comment to say one document composes a stage.
- **Modify `evals/evals.json`:** the `invokes` of A1 (`:171`), A2 (`:207`), A3
  (`:243`), A4 (`:279`) and A8 (`:402`) becomes `tcw-work-stage`. Prompts and
  assertions are unchanged.
- **Modify `evals/coverage.py`:** remove `EXCLUSIONS["tcw-work-stage-request"]`
  (`:35-38`), and add `PARTIAL["tcw-work-stage"]` carrying its reason for the
  `request` route (spec D6.3 item 5).
- **Modify the comments** at `evals/assets/gen_requirement.py:35` and
  `tests/test_eval_fixture.py:149`: "which every per-stage skill documents" →
  "which `tcw-work-stage` documents".

**Deletions**

- `git rm -r skills/tcw-work-stage-request skills/tcw-work-stage-spec skills/tcw-work-stage-plan skills/tcw-work-stage-implement skills/tcw-work-stage-verify`

**Wiring**

- **Modify `.codex-plugin/plugin.json`** `longDescription`: "fifteen skills" →
  "ten skills", and remove the sentence part naming the five per-stage skills.
- **Modify `README.md:451-461`** ("Reading a lifecycle stage"): one skill,
  `tcw-work-stage`, takes the stage id and reaches all seven stages. Task 13 fixes
  the counts at `:430-432`.
- **Modify `docs/capabilities/work/run-a-lifecycle-stage/description.md:104-116`:**
  reword the paragraph so it describes `tcw-work-stage` alone, reaching every stage
  under Claude and Codex, with the stage named in the request. It is the
  capability's body, edited directly because `set` cannot write a body.
  - Replace "`tcw-work-stage` still reaches both, which is why it stays".
  - Keep "None of the five gates either" only if it still reads true.
- **Modify `skills/tcw-work-stage/SKILL.md`** (fallback block, `:41-47`): add,
  before the commands, "Use the stage and work item named in the request in place
  of `$stage` and `$item`." (spec D8, AC 16).
- **Modify `skills/tcw-work/references/commands.md:31-32`:** delete the
  `tcw-work-stage-<id>` row, and remove "**Claude only.**" from the
  `tcw-work-stage` row (AC 16).

**Proof**

- `tests/test_skill_lifecycle_parity.py`, `tests/test_plugin_manifests.py` and
  `tests/test_eval_coverage.py` pass.
- `git grep -nE 'tcw-work-stage-(request|spec|plan|implement|verify)' -- skills commands README.md .codex-plugin evals docs/capabilities`
  prints nothing.
- `tcw capabilities check` prints `capabilities OK`.
- Bare `pytest` is green.

#### Task 2 — Rename the three extras skills

Spec D8, revision notes 14–15.

**Renames**

- `git mv skills/autonomous-work skills/tcw-extras-autonomous-work`, and set its
  `name:` to `tcw-extras-autonomous-work`.
- `git mv skills/tcw-triage-issues skills/tcw-extras-triage-issues`, and set its
  `name:` to `tcw-extras-triage-issues`. Replace every mention of its own old name
  inside the skill.
- `git mv skills/tcw-report skills/tcw-extras-report`, and set its `name:` to
  `tcw-extras-report`. In `skills/tcw-extras-triage-issues/SKILL.md:3-4`,
  `tcw-report` → `tcw-extras-report`.
- In `commands/tcw-triage-issues.md`, update `:5`, `:8` and `:10` to the new skill
  names, so the command still routes correctly until task 11 deletes it.

**References**

- **Modify `skills/tcw-work/references/lifecycle/stage-inbox.md:11`** and
  **`skills/tcw-work/references/transitions.md:117`, `:157`:**
  `tcw-triage-issues` → `tcw-extras-triage-issues`.
- **Modify `docs/guide/work.md:212`:** `/tcw-triage-issues` → "the
  `tcw-extras-triage-issues` skill".
- **Modify `README.md`:**
  - rename the `tcw-report` (`:441`), `tcw-triage-issues` (`:442`) and
    `autonomous-work` (`:445`) rows, and move them under a short "Extras" note:
    "`tcw-extras-*` skills are optional, built for one way of working, and not
    needed to use TCW".
  - The slash-command paragraph (`:465-472`) is left for task 11.
- **Modify `.codex-plugin/plugin.json`:** rename all three skills in
  `longDescription`. The count stays "ten skills".
- **Modify `evals/evals.json`:**
  - B7 (`:653-654`): `skill` and `invokes` become `tcw-extras-triage-issues`;
  - B6 (`:625-626`): `skill` and `invokes` become `tcw-extras-report`.
- **Modify `evals/coverage.py:39`:** re-key `EXCLUSIONS["autonomous-work"]` to
  `tcw-extras-autonomous-work`.
- **Leave these alone.** Task 11 deletes `tcw-plugin`, and the
  taxonomy-and-capabilities item deletes the two capabilities:
  `skills/tcw-plugin/SKILL.md:29-54`,
  `docs/capabilities/plugin/triage-github-issues/description.md`, and
  `docs/capabilities/plugin/report-an-issue-upstream/description.md`.

**Proof**

- `tests/test_plugin_manifests.py` passes: every shipped skill is named as a whole
  token.
- `tests/test_eval_coverage.py` passes.
- `git grep -nP '(?<![-\w])autonomous-work|(?<![-\w])tcw-triage-issues|(?<![-\w])tcw-report' -- skills README.md .codex-plugin evals docs/guide`
  prints only `skills/tcw-plugin/SKILL.md` lines, `commands/tcw-triage-issues.md`,
  and the `README.md` slash-command paragraph (`:465-472`), which task 11 rewrites.
- Bare `pytest` is green.

#### Task 3 — Turn the four workflow commands into `tcw-commands-*` skills

Spec D9.

**For each pair**

- `commands/tcw-plan-work.md` → `skills/tcw-commands-plan-work/SKILL.md`
- `commands/tcw-drive-work-to-completion.md` →
  `skills/tcw-commands-drive-work-to-completion/SKILL.md`
- `commands/tcw-verify-work.md` → `skills/tcw-commands-verify-work/SKILL.md`
- `commands/tcw-process-inbox.md` → `skills/tcw-commands-process-inbox/SKILL.md`

**Steps**

1. **Rename commit.** `git mv` each file to its new path and edit nothing in
   those files. `tests/test_plugin_manifests.py` would fail on a `SKILL.md`
   without `name`, so this commit also adds the frontmatter keys:
   - `name: tcw-commands-<rest>`;
   - a `when_to_use` built from the command's `description`;
   - `allowed-tools`: the list at `skills/tcw-work/SKILL.md:5`;
   - `metadata.author` and `license`, as on other skills.

   The rename therefore won't be `R100`. No acceptance criterion needs it to be;
   git history still follows the file at a lower similarity.

   **The same commit also** changes `.codex-plugin/plugin.json` from "ten skills"
   to "fourteen skills", naming the four. It also adds the four `EXCLUSIONS`
   entries to `evals/coverage.py`. Without both, the manifest-count test and the
   coverage gate fail at this commit.
2. **Body edits:**
   - Paths written relative to `tcw-work` (`references/lifecycle/stage-*.md`,
     `references/epic-deltas.md`, `references/procedures/delegation.md`,
     `skills/tcw-work/SKILL.md`) become "the `tcw-work` skill's `<document>`", in
     words.
   - "This command covers" → "This skill covers".
   - `/tcw-drive-work-to-completion` and `/tcw-plan-work` in the bodies become
     "the `tcw-commands-drive-work-to-completion` skill" and "the
     `tcw-commands-plan-work` skill".
   - Remove the trailing `$ARGUMENTS`; the work item is named in the request.
3. **Wiring:**
   - **`skills/tcw-extras-autonomous-work/SKILL.md:3`** (its `description`, "via
     tcw-drive-work-to-completion") **and `:8`** (`/tcw-drive-work-to-completion`)
     → the `tcw-commands-drive-work-to-completion` skill.
   - **`skills/tcw-work/references/commands.md:135-140`:** the section "Slash
     commands (Claude only)" becomes "Command skills", naming the four
     `tcw-commands-*` skills and saying that every one works by invoking the
     skill, under any harness.
   - **Any other file under `skills/` or `docs/guide/`:** replace each mention of
     `/tcw-plan-work`, `/tcw-drive-work-to-completion`, `/tcw-verify-work` or
     `/tcw-process-inbox` with the matching skill. Find them with
     `git grep -nE 'tcw-(plan-work|drive-work-to-completion|verify-work|process-inbox)' skills docs/guide`,
     which has no leading `/`, so it also catches mentions without the slash.

**Proof**

- `tests/test_plugin_manifests.py` passes: frontmatter parses, and the count and
  names match.
- `tests/test_eval_coverage.py` passes.
- `commands/` no longer holds those four files.
- Bare `pytest` is green.

### Phase B — `tcw-configure`

#### Task 4 — Rename the documentation-entries setup document (a commit that only renames)

- **Run:** `git mv skills/documentation-sync/references/setup.md skills/tcw-configure/references/docs-sync.md`.
  Make **no** edits to the moved file in this commit.
- **In the same commit, update every pointer to the old path:**
  - `commands/tcw-docs-sync-setup.md:7`, which still exists until task 11: read the
    `tcw-configure` skill's `references/docs-sync.md`.
  - `skills/documentation-sync/SKILL.md:15`, `:29`, and the table row at `:98`:
    "the `tcw-configure` skill's `docs-sync.md`", in words, with no path.
  - `skills/documentation-sync/references/release-notes-and-changelogs.md:5`: the
    same wording.
  - `tests/test_documentation_sync_wiring.py`:
    - `SKILL_FILES` (`:13-19`) drops `setup.md`, and a new line checks the
      document exists at its new path;
    - the `COMMAND_ROUTES` value for `tcw-docs-sync-setup` (`:24`) becomes
      `references/docs-sync.md`, which is a substring of the command's reworded
      pointer, so `test_commands_route_into_the_skill` keeps passing;
    - the docstring at `:109-115` and the read at `:127-134` use the new path.
  - `tests/test_documentation_config.py:137`: the docstring names the new
    document.
- **Proof:**
  - `git show --name-status --find-renames HEAD` lists the move as `R100` (AC 11);
  - `tests/test_documentation_sync_wiring.py` and
    `tests/test_documentation_config.py` pass;
  - bare `pytest` is green.

#### Task 5 — Edit `docs-sync.md` into its new home

- **Modify `skills/tcw-configure/references/docs-sync.md`:**
  - Retitle it "Declare which documents track which changes".
  - Its pointers into "`SKILL.md`" (`:34`, `:37`) name "the `documentation-sync`
    skill's `SKILL.md`".
  - Keep the `CLAUDE.md` fallback form (`:27`) and the "Create Tracked Files" and
    "Deferred follow-up work" sections unchanged.
- **Modify `skills/documentation-sync/SKILL.md:3`** (`description`): replace "Use
  when a project declares documentation entries — in `tcw-config.yaml` under
  `work.documentation`, or as a `## Documentation Sync` section in its CLAUDE.md."
  with "Use when a project has documentation entries — from `tcw work docs`, or a
  `## Documentation Sync` section in its CLAUDE.md — and a change may have fired
  one." (AC 9)
- **Proof:**
  - `test_the_skill_and_setup_reference_do_not_contradict_each_other` still passes
    (it needs "prefer config" and `work.documentation` in the document);
  - bare `pytest` is green.

#### Task 6 — Write `work.md`, `tracker.md`, `stores.md`, `projects.md` by moving text

Cut every passage at a paragraph boundary. After each cut, re-read the text left
behind for references to what moved ("both", "the same way", "below", "above"),
and reword them so they stand alone (D4).

**`skills/tcw-configure/references/work.md` (new file)**

- **Move from `skills/tcw-work/references/hooks.md`:**
  - `:1-19`: the title, the binding example, "a binding declares one kind
    explicitly", and what `tcw validate` rejects;
  - `:38-41`: the legacy bare-list shape;
  - `:97-98`: the trust note.
- **Add new text:**
  - `work.lifecycle.timeout` (seconds, a positive integer) and
    `work.lifecycle.output-cap` (bytes, a positive integer). Source:
    `tcw/store/base.py:1830-1848`.
  - `docs/work/dod.yaml`: a list of strings, or a mapping with `checklist:`. It
    *replaces* the built-in five, and is printed and never enforced. Source:
    capability `work/customize-the-definition-of-done`.
  - `work.retain.<status>`: true by default, and refused while the destination is
    gitignored. Source: `transitions.md:23-30`.
  - `work.auto-commit-transitions`: true by default. Source: `transitions.md:11-14`.
  - `work.trunk-branch`. Source: `docs/guide/work.md:188`.
  - `work.publish-transitions`: false turns publication off for a provisioned
    store. Source: `commands.md:227`.
  - Each new paragraph states the key, its type, its default, and what
    `tcw validate` says about a bad value. Check each fact against the source
    named above.
- **Refer to the roles, kinds and `when:` table in words** ("the table in the
  `tcw-work` skill's `hooks.md`"); don't copy it.

**`skills/tcw-work/references/hooks.md` (modify)**

- It now opens with one line: "How bindings run. To declare them, see the
  `tcw-configure` skill's `work.md`."
- It keeps `:21-36` and `:43-95` (AC 13).

**Other pointers**

- **Modify `skills/tcw-work/references/transitions.md`:** after the key name at
  `:11` and at `:23`, add "(set with the `tcw-configure` skill)". Nothing else
  changes.
- **Modify `skills/tcw-work/references/lifecycle/default/README.md:51`:** it names
  "the `tcw-configure` skill's `work.md`" for binding shapes, and `hooks.md` for
  the conditions table.

**`skills/tcw-configure/references/tracker.md` (new file)**

- **Move from `skills/tcw-work/references/commands.md`:** `:93-100` (the
  `work.tracker` keys, and credentials by name).
- **Leave behind:** one line, "Configured with the `tcw-configure` skill's
  `tracker.md`." The `tcw work tracker` rows and `:102-109` stay.
  `tests/test_documented_cli_surface.py` requires `tcw work tracker` in
  `commands.md`.

**`skills/tcw-configure/references/stores.md` (new file)**

- **Move from `commands.md`:** `:156-162` (declaring `work.repository`).
- **Add new text:**
  - `taxonomy.path`, `capabilities.path`, `work.path`;
  - `tcw init --work-path/--taxonomy-path/--capabilities-path` and
    `tcw work init --path`;
  - "changing a store's path **does not move** existing items; a store that isn't
    empty is never moved automatically". Check this against
    `tcw/store/fs.py:924-934` and `docs/guide/multi-repo.md:205`;
  - a closing step: run `tcw validate`, and `tcw provision` when a `repository`
    block was added.
- **Leave behind:** one line in `commands.md`.

**`skills/tcw-configure/references/projects.md` (new file)**

- **Move from `commands.md`:** `:173-191` (a connected project as
  `{path, repository}`, and `TCW_PROJECT_<ID>`).
- **Move from `skills/tcw-taxonomy/SKILL.md`:** `:93-98` (declaring
  `tcw taxonomy extends add|rm`).
- **Move from `skills/tcw-capabilities/SKILL.md`:** `:86-91` (declaring
  `tcw capabilities extends [--rm]`).
- **Add new text:**
  - the `connected-projects` mapping: `parent` holds at most one entry, and
    `children` a list; each entry is a locator or `{path, repository}`. Check
    against `tcw/store/project.py:440-452`;
  - `extends` is stored in `docs/taxonomy/config.yaml` and
    `docs/capabilities/.config.yaml`, and changes only through the commands.
- **Leave behind:** in `tcw-taxonomy` `## Inheritance` and `tcw-capabilities`
  `## Federation`, how inherited entries resolve, are overridden and reset stays,
  plus one line pointing to "the `tcw-configure` skill". Their quick-reference
  `extends` rows (`tcw-taxonomy:119`, `tcw-capabilities:133`) point there too.

**Tests**

- **Modify `tests/test_documented_cli_surface.py`:** no change is required.
  Confirm `tcw work tracker` is still found in `commands.md`.

**Proof**

- `git grep -n 'work.lifecycle' skills/tcw-work/references/hooks.md` shows no
  "how to declare" example remains.
- AC 12's strings are present.
- Bare `pytest` is green. That includes `tests/test_skill_lifecycle_parity.py`,
  which requires every `tcw-work` reference file to be reachable, and
  `tests/test_documented_cli_surface.py`.

Commit this task as four commits, one per new document, each green.

#### Task 7 — Create the `tcw-configure` skill

Tests first.

**Tests**

- **Modify `tests/test_skill_lifecycle_parity.py`:** parametrize the router tests
  over `tcw-configure` (and, from task 10, `tcw-setup`):
  - the body is at most 60 lines;
  - every file under `references/` is named in `SKILL.md`;
  - there is no `$ARGUMENTS` and no `` !` ``;
  - the other skill is named as "the `tcw-setup` skill" or "the `tcw-configure`
    skill".

  Until task 10 the parameter list holds only `tcw-configure`. Its body already
  names "the `tcw-setup` skill", so the check passes before that skill exists.
- **Create `tests/test_skill_path_pointers.py`:** no file under `skills/` outside
  `skills/tcw-configure/` contains `tcw-configure/references/`, and none outside
  `skills/tcw-setup/` contains `tcw-setup/references/` (AC 14, D6.5).
- **Modify `tests/test_repo_lifecycle.py:94-104`:** the expected entry paths and
  triggers include the new `skills/tcw-configure/references/<document>.md` entry
  and the `Configuration-Key-Change` trigger.

**The skill**

- **Create `skills/tcw-configure/SKILL.md`:**
  - **Frontmatter:**
    - `name: tcw-configure`;
    - `description` per D2, containing the AC 8 words: `lifecycle`,
      `definition of done`, `documentation`, `tracker`, `store`, `connected`,
      `set up`;
    - a `when_to_use`;
    - `allowed-tools`: the list at `skills/tcw-work/SKILL.md:5` plus `Grep, Glob`;
    - `metadata.author` and `license` as on other skills.
  - **Body, at most 60 lines:**
    - one sentence of purpose;
    - "Getting TCW working where it does not yet is the `tcw-setup` skill";
    - a routing table with columns *situation* → *document*, one or more rows per
      reference document, covering every area in spec Goal 2.

**Wiring**

- **Modify `.codex-plugin/plugin.json`** `longDescription`: "fourteen skills" →
  "fifteen skills", and add a clause "tcw-configure for changing a project's TCW
  configuration".
- **Modify `evals/evals.json`:** add case **B11**:
  - `axis: B`, `skill: tcw-configure`, `invokes: tcw-configure`, arms `with-skill`
    and `no-skill`.
  - Prompt: "Set up documentation tracking so README.md is also updated whenever
    any code in demo-app changes." The fixture declares `README.md` only under
    `Public-API` (`evals/seed_fixture.py:245-248`), so this adds a new
    `(path, trigger)` pair to an existing file and has no reason to create one.
  - Assertions:
    - `tool_input_contains` `tcw-configure/references/docs-sync.md`;
    - `tool_input_absent` `tcw-setup/references/`;
    - `files_changed_exactly` `["tcw-config.yaml"]`;
    - `validate_exit_zero`.
- **Modify `tests/test_eval_grading.py`:** add a failing-transcript test for B11's
  routing assertion, such as a transcript whose only read is
  `tcw-setup/references/project.md`, with a passing counterpart.
- **Modify `evals/coverage.py`:** add `PARTIAL["tcw-configure"]`: "B11 measures
  the documentation-entries route only. `work.md`, `tracker.md`, `stores.md` and
  `projects.md` are unmeasured."
- **Modify `tcw-config.yaml` `work.documentation`:**
  - Add the entry: `path: skills/tcw-configure/references/<document>.md`,
    `trigger: Configuration-Key-Change`, with the description from spec D4.
  - Append to the `Skill-Driven-Component` description: "How to configure a
    component goes to `tcw-configure`, not to the component's skill."

**Pointers**

- **Modify `skills/tcw-work/SKILL.md`:**
  - Delete "`tcw-plugin` maps the skills." (`:19-20`).
  - At `:55`, add "declaring them: the `tcw-configure` skill".
  - The body stays at most 60 lines (`test_the_router_stays_within_its_line_budget`).

**Proof**

- `tests/test_skill_lifecycle_parity.py`, `tests/test_skill_path_pointers.py`,
  `tests/test_repo_lifecycle.py`, `tests/test_plugin_manifests.py`,
  `tests/test_eval_coverage.py`, and `tests/test_eval_grading.py` pass.
- `tcw validate` exits 0, and `tcw work docs` lists the new entry (AC 18).
- Bare `pytest` is green.

### Phase C — `tcw-setup`

#### Task 8 — Rename both `init.md` documents (a commit that only renames)

- **Run:**
  - `git mv skills/tcw-taxonomy/references/init.md skills/tcw-setup/references/taxonomy.md`
  - `git mv skills/tcw-capabilities/references/init.md skills/tcw-setup/references/capabilities.md`

  Make no edits to either moved file.
- **In the same commit, update the pointers:**
  - `commands/tcw-taxonomy-init.md:5` and `commands/tcw-capabilities-init.md:5`,
    which remain until task 11: the new paths.
  - `skills/tcw-taxonomy/SKILL.md` `## Bootstrap` (`:104-107`) and
    `skills/tcw-capabilities/SKILL.md` `## Bootstrap` (`:117-120`): replace each
    section with one line, "To seed a new taxonomy (capabilities ledger) from an
    existing codebase, use the `tcw-setup` skill." Use words only; task 7's
    path-pointer test would fail on a path.
- **Proof:**
  - `git show --name-status --find-renames HEAD` lists both moves as `R100`
    (AC 11);
  - bare `pytest` is green.

#### Task 9 — Edit the two moved setup documents

- **Modify `skills/tcw-setup/references/taxonomy.md`:** replace step 2
  "Inheritance" (the old `init.md:15-23`) with:

  > Ask whether this project inherits taxonomy from another registered project.
  > If it does, declare it with the `tcw-configure` skill's `projects.md`, then
  > continue.

- **Modify `skills/tcw-setup/references/capabilities.md`:** line 9, "point the
  user at `/tcw-taxonomy-init`", becomes "seed it first with `taxonomy.md`".
- **Proof:** bare `pytest` is green.

#### Task 10 — Create the `tcw-setup` skill

Tests first.

**Tests**

- **Modify `tests/test_skill_lifecycle_parity.py`:** add `tcw-setup` to the router
  test parameters from task 7.
- **Modify `tests/test_eval_grading.py`:** add failing and passing transcript
  tests for:
  - B12's `tool_input_contains` `tcw-setup/references/project.md`;
  - `tool_input_absent` `tcw-setup/references/` as used by B4 and B8.

**The skill**

- **Create `skills/tcw-setup/references/install.md`.** Move
  `skills/tcw-plugin/SKILL.md:62-115` into it.
  - Reword only mentions of the old skill.
  - The cloud-environment paragraph (`:107-110`) keeps its rule and drops "The
    README's _Install → In a cloud environment_ carries the script". List that
    line in `outcome.md` under "Moved lines changed" (AC 11).
  - In `skills/tcw-plugin/SKILL.md`, replace the moved section with one line
    pointing to the `tcw-setup` skill. `tcw-plugin` is deleted in task 11.
- **Create `skills/tcw-setup/references/project.md` (new text):**
  - `tcw init --id <project-id> [components]` marks the current directory as a
    TCW node, writes `tcw-config.yaml`, and scaffolds each component. It refuses
    outside a git repository.
  - Per-component `tcw taxonomy|capabilities|work init`.
  - "Store locations other than the defaults: see the `tcw-configure` skill's
    `stores.md`."
  - `tcw provision [--component …]` for a project whose stores or connected
    projects are declared in another repository. Never run `tcw init` to work
    around a declared store.
  - Close with `tcw validate`, then "to change configuration from here, use the
    `tcw-configure` skill".
  - Check every command against `tcw init --help`, `tcw provision --help` and
    `README.md:336-351`.
- **Create `skills/tcw-setup/SKILL.md`:**
  - **Frontmatter:**
    - `name: tcw-setup`;
    - `description` per D2, containing the AC 8 words: `missing`, `broken`,
      `stale`, `taxonomy`, `capabilities`;
    - a `when_to_use`;
    - `allowed-tools`: `skills/tcw-plugin/SKILL.md:5` plus `Read, Grep, Glob`;
    - `compatibility`, `metadata`, `license` from `skills/tcw-plugin/SKILL.md:6-9`.
  - **Body, at most 60 lines:**
    - one sentence of purpose;
    - "Changing a working project's configuration is the `tcw-configure` skill";
    - the order: install → project → taxonomy → capabilities;
    - a routing table with rows to its four documents, plus redirect rows naming
      "the `tcw-configure` skill" for documentation entries, lifecycle bindings,
      Definition of Done, tracker, store locations, and connected or inherited
      projects (AC 7).

**Wiring and pointers**

- **Modify `skills/tcw-taxonomy/SKILL.md:3-4`:**
  - `description`: remove "federating shared vocabulary across repos, or
    bootstrapping a taxonomy from an existing codebase".
  - `when_to_use`: remove "seeding", "federating shared vocabulary across repos"
    and "bootstrapping a taxonomy from an existing codebase".
  - Keep the sentences grammatical (AC 9).
- **Modify `skills/tcw-taxonomy/SKILL.md:24-25`:** delete "See `tcw-plugin` for
  the cross-skill map."
- **Modify `.codex-plugin/plugin.json`:** "fifteen skills" → "sixteen skills", and
  add a clause "tcw-setup for setting TCW up and repairing the CLI". This count is
  temporary until task 11.
- **Modify `evals/evals.json`:**
  - Add case **B12**:
    - `axis: B`, `skill: tcw-setup`, `invokes: tcw-setup`, `fixture: bare`, arms
      `with-skill` and `no-skill`.
    - Prompt: "This is demo-app. Start tracking it with TCW."
    - Assertions: `tool_input_contains` `tcw-setup/references/project.md`;
      `tool_input_absent` `tcw-configure/references/`; `validate_exit_zero`.
  - Add `tool_input_absent` `tcw-setup/references/` to B4 and B8.
- **Modify `evals/coverage.py`:** add `PARTIAL["tcw-setup"]` covering the
  unmeasured routes listed in spec D6.4.
- **Modify `docs/capabilities/plugin/bootstrap-the-cli/description.md`:** its two
  mentions of `tcw-plugin` become `tcw-setup` (spec Capability changes, AC 15). It
  is body text, edited directly. Then run `tcw capabilities check`.
- **Modify `scripts/session_bootstrap.sh:9`, `:45`:** comments name the
  `tcw-setup` skill and its `install.md`.

**Proof**

- `tests/test_skill_lifecycle_parity.py`, `tests/test_skill_path_pointers.py`,
  `tests/test_plugin_manifests.py`, `tests/test_eval_coverage.py`, and
  `tests/test_eval_grading.py` pass.
- `bash -n scripts/session_bootstrap.sh` passes.
- Bare `pytest` is green.

#### Task 11 — Remove `tcw-plugin` and every remaining command

Tests first.

**Tests**

- **Modify `tests/test_skill_lifecycle_parity.py`:** add a deleted-names test
  modeled on `DELETED` (`:47`, `:254`). As whole names (a regex that rejects a
  preceding `-` or word character, so `tcw-extras-autonomous-work` does not match
  `autonomous-work`), it rejects:
  - `tcw-plugin`, `tcw-taxonomy-init`, `tcw-capabilities-init`,
    `tcw-docs-sync-setup`;
  - the five `tcw-work-stage-<stage>` names;
  - `autonomous-work`, `tcw-triage-issues`, `tcw-report`;
  - `tcw-plan-work`, `tcw-drive-work-to-completion`, `tcw-verify-work`,
    `tcw-process-inbox`, `tcw-work-search`, `tcw-audit-work-backlog`,
    `tcw-consolidate-plans`, `tcw-cut-version`.

  It scans every file under `skills/`, `.claude-plugin/`, `.codex-plugin/`,
  `README.md`, `docs/guide/` and `docs/lifecycle/`, and asserts `commands/` does
  not exist. Confirm it fails before the deletions below and passes after them.

**Deletions**

- `git rm -r skills/tcw-plugin`
- `git rm -r commands`. By now it holds only `tcw-taxonomy-init`,
  `tcw-capabilities-init`, `tcw-docs-sync-setup`, `tcw-cut-version`,
  `tcw-post-mortem`, `tcw-triage-issues`, `tcw-work-search`,
  `tcw-audit-work-backlog` and `tcw-consolidate-plans`. Spec D9 records, for each,
  the skill text that already covers it. Re-read that table against each file
  before deleting it.

**Wiring**

- **Modify `.claude-plugin/plugin.json:21`:** remove the `commands` key.
- **Modify `.codex-plugin/plugin.json`:** "sixteen skills" → "fifteen skills", and
  remove the "tcw-plugin for installing and repairing the CLI" clause.
- **Modify `tests/test_documentation_sync_wiring.py`:** delete `COMMAND_ROUTES`
  (`:21-26`) and `test_commands_route_into_the_skill` (`:97-104`).
- **Modify `skills/tcw-work/SKILL.md` `when_to_use`:** add "searching the board,
  auditing the backlog, or consolidating external planning documents".
- **Modify `skills/tcw-work/references/procedures/search.md:7-8`,
  `audit-backlog.md:5`, `consolidate-plans.md:6`:** "Claude users reach it as
  `/tcw-…`" → "ask the `tcw-work` skill for it".
- **Modify `skills/tcw-work/references/lifecycle/stage-verify.md:36`:** drop
  "`/tcw-cut-version` is the Claude shortcut to the same thing".
- **Modify `docs/lifecycle/harness.md:18`:** use the sentence from spec D9.
- **Modify `skills/tcw-work/references/commands.md:42-43`:** "`/tcw-audit-work-backlog`
  in Claude" and "`/tcw-consolidate-plans` in Claude" → "ask the `tcw-work`
  skill". The rows keep pointing at the procedures.
- **Modify `skills/documentation-sync/references/cut-version.md`:** before its
  "Rotate `upcoming.md` files" step, add "Write the release-note and changelog
  entries into the `upcoming.md` files first. The cut rotates them." Also change
  `:3`, and the `SKILL.md` table row at `:99`, so the document opens when the user
  asks directly to cut a version, not only after picking a bump (spec D4, AC 16).
  Do this before deleting `commands/tcw-cut-version.md`.
- **Modify `.claude-plugin/marketplace.json:12`:** "skills + slash commands" →
  "skills".
- **Modify `docs/guide/work.md:465`, `:475`:** `/tcw-audit-work-backlog` and
  `/tcw-consolidate-plans` → "ask the `tcw-work` skill to audit the backlog" or
  "to consolidate external plans".
- **Modify `tests/test_plugin_manifests.py:4`:** the docstring names `tcw-setup`.
- **Modify `evals/evals.json` B5:** `skill: cross-axis`,
  `invokes: ["tcw-taxonomy", "tcw-capabilities"]`. The prompt and assertions are
  unchanged.
- **Modify `evals/coverage.py`:** remove `PARTIAL["tcw-plugin"]` and its comment
  (`:46-57`).
- **Modify `README.md`:**
  - `:217` and `:227` name `tcw-setup`;
  - `:352` asks for the `tcw-setup` skill instead of the two commands;
  - the slash-command paragraph (`:465-472`) becomes two sentences naming the four
    `tcw-commands-*` skills and the three `tcw-extras-*` skills;
  - `:440`, the `tcw-plugin` row, becomes rows for `tcw-setup` and `tcw-configure`
    (the descriptions from task 13). It lands in this commit so the deleted-names
    test passes here;
  - `:34`, `:230` and `:463`: "slash commands" → "command skills", keeping the
    table-of-contents anchor in step with the heading.

  Task 13 handles the rest of the README.
- **Modify `docs/guide/taxonomy-and-capabilities.md:59`:** the same change as
  `README.md:352`.

**Proof**

- The deleted-names test passes.
- ACs 1–5 hold.
- `tests/test_plugin_manifests.py`, `tests/test_eval_coverage.py`, and
  `tests/test_documentation_sync_wiring.py` pass.
- Bare `pytest` is green.

### Phase D — Notes

#### Task 12 — Notes on related open items

Add one line under `## Notes` in each item's body document (`initial-request.md`,
or `intake.md` where there is no request). Name this item's slug and say what
changed for that item:

- **Tracker items:** tracker configuration text goes in the `tcw-configure` skill's
  `tracker.md`.
  - `2026-09-12-configure-an-external-tracker-and-read-its-tickets`
  - `2026-09-12-claim-an-external-tracker-ticket-and-bind-it-to-a-work-item`
  - `2026-09-12-synchronize-the-work-lifecycle-outward-to-the-tracker`
  - `2026-09-12-refuse-local-work-that-no-claimed-tracker-ticket-authorizes`
  - `2026-09-12-surface-an-item-s-tracker-binding-in-the-board-the-projection-and-the-web-app`
- **Items that add configuration keys:** new keys are documented in
  `tcw-configure`, per the `Configuration-Key-Change` entry.
  - `2026-08-18-serve-version-cut-instructions-from-tcw-config-yaml-instead-of-the-agent-guide`
  - `2026-09-10-let-a-node-declare-its-own-work-item-state-fields`
  - `2026-09-10-record-a-work-item-s-branch-and-let-a-node-declare-its-own-state-fields`
- **`2026-09-11-run-the-eval-harness-and-act-on-what-it-finds`:**
  - B11 (`tcw-configure`) and B12 (`tcw-setup`, bare fixture) are new;
  - B5 is retargeted;
  - B4 and B8 gained routing checks;
  - A1–A4 and A8 now invoke `tcw-work-stage`, and the axis A baseline may move,
    because the agent must now pass the stage as an argument;
  - the four `tcw-commands-*` skills are excluded, with no case yet;
  - `PARTIAL` gained `tcw-setup`, `tcw-configure` and `tcw-work-stage`.
- **`2026-09-11-refine-the-plugin-skills-and-lifecycle-prompts-against-the-eval-findings`:**
  it refines the restructured skill set.
- **`2026-08-18-report-the-missing-skill-caveat-from-tcw-work-lifecycle-rather-than-the-skill`:**
  the caveat it quotes was at `hooks.md:88` at `<base>`, and its line has moved.
- **`2026-08-12-separate-the-agent-plugin-from-the-python-cli-source`:**
  - `tcw-plugin` is gone; its install text is the `tcw-setup` skill's `install.md`;
  - `commands/`, which its plan moves, no longer exists.

**Proof:** each note is committed, and `tcw validate` exits 0.

## Documentation Sync

Evaluated with `tcw work docs` at plan time. Implementation answers these in one
pass over the finished diff, after task 12.

### Task 13 — `README.md` [Public-API] — fires

- **`:430-432`:** "Fifteen skills … Nine carry a distinct procedure; the other six
  all compose one lifecycle stage" → fifteen skills in three groups: eight core
  skills (one composes a lifecycle stage), four command skills for the everyday
  workflow, and three extras.
- **Row descriptions used in task 11:**
  - `tcw-setup`: "Gets TCW working: installs or repairs the CLI, sets up a
    repository, starts a taxonomy or capabilities ledger".
  - `tcw-configure`: "Changes a project's configuration: lifecycle bindings,
    Definition of Done, documentation entries, tracker, stores, connected and
    inherited projects".
- **Re-read** the Install section (`:205-230`), "Bootstrapping" (`:348-353`),
  "Reading a lifecycle stage" (`:451-461`) and the command-skills paragraph for
  anything the earlier line edits left reading oddly.

### Task 14 — `docs/release-notes/upcoming.md` [Public-API] — fires

In plain language, for someone who used the old names:

- **Setting TCW up** is the `tcw-setup` skill, which replaces `tcw-plugin`.
  **Changing its configuration** is the `tcw-configure` skill.
- **There are no slash commands any more.**
  - The everyday workflows are skills: `tcw-commands-plan-work`,
    `tcw-commands-drive-work-to-completion`, `tcw-commands-verify-work`,
    `tcw-commands-process-inbox`.
  - For searching the board, auditing the backlog, or consolidating plans, ask the
    `tcw-work` skill.
  - For a post-mortem, use the `tcw-post-mortem` skill.
  - For a version cut, use `documentation-sync`.
- **The five per-stage skills are gone.** `tcw-work-stage` takes the stage and
  works the same under Codex.
- **Renamed:**
  - `autonomous-work` → `tcw-extras-autonomous-work`
  - `tcw-triage-issues` → `tcw-extras-triage-issues`
  - `tcw-report` → `tcw-extras-report`

### Task 15 — `docs/changelogs/upcoming.md` [Any-Code-Change] — fires

Technical, grouped:

- **Added:**
  - the `tcw-setup` and `tcw-configure` skills and their references;
  - the four `tcw-commands-*` skills;
  - eval cases B11 and B12, and routing checks on B4 and B8;
  - `PARTIAL` entries;
  - the `Configuration-Key-Change` documentation entry;
  - the deleted-names, router and path-pointer tests.
- **Changed:**
  - text moved out of `hooks.md`, `commands.md`, `transitions.md`, the axis skills
    and `documentation-sync`;
  - B5 retargeted, and A1–A4 and A8 invoke `tcw-work-stage`;
  - `tcw-work-stage`'s fallback works under Codex;
  - `cut-version.md` gained the pre-cut entry rule and a direct route.
- **Removed:**
  - `tcw-plugin` and its skill map;
  - the five `tcw-work-stage-<stage>` skills and their tests;
  - every slash command, `commands/`, and the `commands` manifest key.
- **Renamed:** the three extras.

### `skills/<component>/SKILL.md` [Skill-Driven-Component] — expected not to fire

No component's CLI surface, model, lifecycle or guardrails change. The skills are
themselves this item's subject. Re-evaluate at the documentation pass, and record
the verdict and reason in `outcome.md`.

### `skills/tcw-configure/references/<document>.md` [Configuration-Key-Change] — expected not to fire

This entry is added by task 7. No configuration key changes; tasks 5–6 write these
documents. Re-evaluate at the documentation pass.

## Verification

The suite covers ACs 1–3, 6, 9, 10 (partly), 13, 14, 17 and 19. Check the rest by
hand, and record every result in `outcome.md`:

1. **AC 4 and AC 5.** Run both `git grep` commands exactly as the spec writes
   them. Each prints nothing.
2. **AC 7 and AC 8.** Read the routing table and both descriptions, and tick each
   required row and word.
3. **AC 11, renames:**

   ```sh
   git log --format=%H <base>..HEAD | while read c; do git show --name-status --find-renames --format= $c; done | grep '^R100'
   ```

   It must list all three moves.
4. **AC 11, partial moves.** For each source range in the spec, run:

   ```sh
   python3 - <<'PY'
   import subprocess
   def lines(rev, path, a, b):
       text = subprocess.run(["git", "show", f"{rev}:{path}"], capture_output=True, text=True, check=True).stdout
       return [l.strip().lstrip("#").strip() for l in text.splitlines()[a-1:b] if l.strip()]
   src = lines("<base>", "<source path>", <start>, <end>)
   dest = open("<destination path>").read()
   print("\n".join(l for l in src if l not in dest) or "all present")
   PY
   ```

   Every missing line must appear in `outcome.md` under "Moved lines changed",
   with its reason.
5. **AC 12.** Run `grep -c` for each required string; each count is 1 or more.
6. **AC 15.** Run the three `tcw capabilities` commands exactly as the spec writes
   them.
7. **AC 16.** Run `grep` for each required string or absence.
8. **AC 18.** Run `tcw work docs` and confirm it lists the new entry.
9. **Judged by reading:**
   - **Text left behind.** Read `hooks.md`, `commands.md` and `transitions.md`,
     and the `## Inheritance` and `## Federation` sections, and confirm nothing
     dangles ("both", "below", "the same way").
   - **Routers and descriptions.** Read both routers and every usage skill's
     description, and confirm no usage skill still advertises setup or
     configuration.
   - **Command skills.** Read the four `tcw-commands-*` bodies against the
     commands at `<base>`, and confirm only the wording changes listed in task 3
     were made.
10. **Not verified by this item.** Whether agents route correctly needs a paid eval
    run, which is `2026-09-11-run-the-eval-harness-and-act-on-what-it-finds`. Say
    so in `outcome.md`.

## Notes

- **Traceability.**
  - ACs 1–5 → tasks 1, 2, 3, 4, 8, 11.
  - AC 6 → tasks 7, 10.
  - AC 7 → task 10.
  - AC 8 → tasks 7, 10.
  - AC 9 → tasks 5, 10.
  - AC 10 → tasks 4, 6, 7, 8.
  - AC 11 → tasks 4, 6, 8, 10.
  - AC 12 → task 6.
  - AC 13 → task 6.
  - AC 14 → task 7.
  - AC 15 → tasks 1, 10.
  - AC 16 → tasks 1, 11.
  - AC 17 → tasks 1, 2, 3, 7, 10, 11.
  - AC 18 → task 7.
  - AC 19 → every task.
  - Task 9 serves AC 11. Task 12 carries the spec's Risks notes.
- **Skill counts at each commit:** 15 at `<base>`; 10 after task 1 (the five
  per-stage skills deleted); 10 after task 2 (renames only); 14 after task 3; 15
  after task 7; 16 after task 10; 15 after task 11. The Codex manifest states the
  count in the same commit that changes it.
- **The riskiest change, in isolation.** Task 6 cuts text across skills. It runs
  after the destination skill's rename commit and before its router exists, so a
  mistake shows in the documents alone.
- **Delegation.** Tasks 1–11 edit overlapping files (the Codex manifest,
  `evals/evals.json`, `evals/coverage.py`, `README.md`). Run them in one session,
  in order.
