# Plan — Separate setting up and configuring TCW from using it

Implements `spec.md`. "AC n" refers to the spec's acceptance criteria and "Dn"
to its design sections.

## Before starting

- **Blocked.** This item is blocked by
  `2026-09-14-delete-a-capability-with-tcw-capabilities-rm` (recorded with
  `tcw work edit --blocked-by`), and `tcw work start` refuses until that item
  completes. Tasks 1–11 don't need the delete command, but the item is not split:
  its ledger tasks (12–13) do need it, and starting half an item isn't allowed.
- **Re-read the dependency's spec.** Before task 13, find out how that item
  records a deleted capability in a work item's `capabilities.yaml`. Task 13
  writes the deletions in that form.
- **Check the tracker item first.** At `tcw work start`, see whether
  `2026-09-12-configure-an-external-tracker-and-read-its-tickets` has completed.
  If it hasn't, task 6 moves `skills/tcw-work/references/commands.md:93-100` as
  it stands on `main` that day, and the note in task 14 tells that item where the
  text went.
- **No `tcw/` code changes.** This item edits no code under `tcw/`, so driving the
  lifecycle with the `tcw` CLI throughout is safe (`CLAUDE.md`, the exception for
  editing TCW's own code does not apply).
- **Record `<base>`.** It is the commit that last touched this `plan.md`. Record
  it in `outcome.md` when the item starts, because ACs 11 and 16 are checked
  against it.
- **Every commit leaves bare `pytest` green.** Each task names the test files it
  must keep passing, and ends by running `pytest -q` (bare, as CI does).
- **Line numbers are as of `<base>`.** Where an earlier task has already edited a
  file, find the passage by its text, not by the number.

## Tasks

### Phase A — Eval infrastructure (no skill changes)

#### Task 1 — Make `files_changed_exactly` compare against the seeded state

The spec (D6.2) requires this check to measure what the agent changed, not
whether it committed. Tests come first.

- **Modify `tests/test_eval_grading.py`** (or create
  `tests/test_eval_files_changed.py` if it reads more cleanly). Add tests that
  build a real git repository with `tmp_path` and `git init`, commit a seed, and
  record its commit as `seeded_head`. Four cases:
  - an uncommitted edit to one expected file passes;
  - a committed edit to the same file passes;
  - an extra untracked, non-ignored file fails;
  - an expected file left unchanged fails.

  Confirm the tests fail against today's grader.
- **Modify `evals/seed_fixture.py`:** at the end of `seed()`, record
  `git rev-parse HEAD` in the returned manifest as `seeded_head`.
- **Modify `evals/run_evals.py`:** carry `manifest["seeded_head"]` into the run
  entry written to `timing.json`, next to `fixture`.
- **Modify `evals/grade.py`** (`p_files_changed_exactly`, `:338-343`): compute
  the changed set as the union of `git diff --name-only <seeded_head>` (working
  tree against that commit) and `git ls-files --others --exclude-standard`. If the
  run entry has no `seeded_head`, return a failing verdict that says so.
- **Modify `evals/evals.json`:** make the `files_changed_exactly` predicate
  description (`:158-163`) match the new behavior. Re-read case B10's `paths` list
  (`:764` onward) against it; change it only if the fixed check shows it was
  wrong.
- **Proof:**
  - the new tests pass;
  - `tests/test_eval_grading.py`, `tests/test_eval_runner.py`,
    `tests/test_eval_fixture.py` pass;
  - bare `pytest` is green.

#### Task 2 — Add `tool_input_contains` and `tool_input_absent`

The spec (D6.1) needs routing checks that only look at what the agent actually
did, not at text it read.

- **Modify `tests/test_eval_grading.py`.** Using a hand-built transcript in the
  shape `evals/grade.py:84-106` parses, add tests showing:
  - `tool_input_contains` passes when a tool call's input holds the substring, and
    fails when the substring appears only in a tool *result* or in assistant text
    (a loaded skill body);
  - `tool_input_absent` is the mirror of that.

  Write these tests first.
- **Modify `evals/grade.py`:** add a helper that yields only tool-call inputs
  (serialized, as `_texts` does for `input`), and two graders registered the way
  the existing predicates are.
- **Modify `evals/evals.json`:** declare both predicates in `predicates`
  (`family: transcript`, `args: ["text"]`), each with a `reads` line.
- **Proof:**
  - the new tests pass;
  - `test_every_declared_predicate_has_a_grader` and
    `test_no_grader_exists_for_an_undeclared_predicate` pass;
  - bare `pytest` is green.

#### Task 3 — Fixture variants by name, and a `bare` variant

The spec (D6.3, case 3) needs a fixture for a repository that doesn't use TCW
yet.

- **Modify `tests/test_eval_runner.py:48-59`.**
  - `variant_for` returns `"customized"` or `"control"` for axis A, and
    `"customized"` for both axis B arms.
  - A case with `"fixture": "bare"` returns `"bare"` in either axis B arm.
- **Modify `tests/test_eval_fixture.py`.** Add a test that `seed(dest, "bare")`
  builds a git repository with the fixture's code, has no `tcw-config.yaml`, and
  returns a manifest whose `nonces` and `stage_items` are empty and whose
  `seeded_head` is set. It must also be one where `tcw validate` does not exit 0.
- **Modify `evals/seed_fixture.py`:**
  - `seed(dest, variant="control")` accepts `"customized"`, `"control"` or
    `"bare"`, replacing the true/false `customized` flag.
  - `"bare"` writes the code files and commits, and skips `tcw init` and every
    step after it.
  - `main()`'s `--customized` flag maps to `"customized"`, and a new `--bare` flag
    maps to `"bare"`.
- **Modify `evals/run_evals.py`:**
  - `variant_for` (`:113-119`) returns the name; `case.get("fixture")` wins when
    present.
  - Every caller of `variant_for` and `seed` passes the name.
  - `run_one` (`:195-196`) keeps reading `nonces` and `stage_items`, which the
    bare manifest supplies empty.
- **Modify `evals/evals.json`** schema block: document the optional `fixture` key
  and its one allowed value, `bare`. Update the case-id range text to name the new
  cases added in tasks 7 and 10.
- **Proof:**
  - `tests/test_eval_runner.py` and `tests/test_eval_fixture.py` pass;
  - `python evals/seed_fixture.py --bare /private/tmp/<dir>` builds a repository
    with no `tcw-config.yaml`;
  - `python -m evals.run_evals --axis b --dry-run` still lists the existing arms
    unchanged;
  - bare `pytest` is green.

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
      `tcw-configure/references/docs-sync.md`;
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

- **Modify `.codex-plugin/plugin.json`** `longDescription`: "fifteen skills" →
  "sixteen skills", and add a clause "tcw-configure for changing a project's TCW
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
- `tcw validate` exits 0, and `tcw work docs` lists the new entry (AC 19).
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
- **Modify `.codex-plugin/plugin.json`:** "sixteen skills" → "seventeen skills",
  and add a clause "tcw-setup for setting TCW up and repairing the CLI". This
  count is temporary until task 11.
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
- **Modify `scripts/session_bootstrap.sh:9`, `:45`:** comments name the
  `tcw-setup` skill and its `install.md`.

**Proof**

- `tests/test_skill_lifecycle_parity.py`, `tests/test_skill_path_pointers.py`,
  `tests/test_plugin_manifests.py`, `tests/test_eval_coverage.py`, and
  `tests/test_eval_grading.py` pass.
- `bash -n scripts/session_bootstrap.sh` passes.
- Bare `pytest` is green.

#### Task 11 — Remove `tcw-plugin` and the three commands

Tests first.

**Tests**

- **Modify `tests/test_skill_lifecycle_parity.py`:** add a deleted-names test
  modeled on `DELETED` (`:47`, `:254`). It rejects `tcw-plugin`,
  `tcw-taxonomy-init`, `tcw-capabilities-init` and `tcw-docs-sync-setup` in any
  file under `skills/`, `commands/`, `.claude-plugin/`, `.codex-plugin/`,
  `README.md` and `docs/guide/`. Confirm it fails before the deletions below.

**Deletions**

- `git rm -r skills/tcw-plugin`
- `git rm commands/tcw-taxonomy-init.md commands/tcw-capabilities-init.md commands/tcw-docs-sync-setup.md`

**Wiring**

- **Modify `.codex-plugin/plugin.json`:** "seventeen skills" → "sixteen skills",
  and remove the "tcw-plugin for installing and repairing the CLI" clause.
- **Modify `tests/test_documentation_sync_wiring.py:23-26`:** remove the
  `tcw-docs-sync-setup` entry from `COMMAND_ROUTES`. The `tcw-cut-version` entry
  stays.
- **Modify `tests/test_plugin_manifests.py:4`:** the docstring names `tcw-setup`.
- **Modify `evals/evals.json` B5:** `skill: cross-axis`,
  `invokes: ["tcw-taxonomy", "tcw-capabilities"]`. The prompt and assertions are
  unchanged.
- **Modify `evals/coverage.py`:** remove `PARTIAL["tcw-plugin"]` and its comment
  (`:46-57`).
- **Modify `README.md`:** `:217` and `:227` name `tcw-setup`; `:352` asks for the
  `tcw-setup` skill instead of the two commands; `:470-471` drop the three
  commands. Task 15 handles the rest of the README.
- **Modify `docs/guide/taxonomy-and-capabilities.md:59`:** the same change as
  `README.md:352`.

**Proof**

- The deleted-names test passes.
- ACs 1–5 hold.
- `tests/test_plugin_manifests.py`, `tests/test_eval_coverage.py`, and
  `tests/test_documentation_sync_wiring.py` pass.
- Bare `pytest` is green.

### Phase D — Taxonomy and ledger (needs `tcw capabilities rm`)

#### Task 12 — Register the `skill` term and sixteen Features

**Commands**

- `tcw taxonomy add "Skill" -s skill "<definition from the spec>"`
- For each row of the spec's Taxonomy table, top-level rows first:
  `tcw taxonomy add "<Feature name>" --kind feature -s <slug> [--parent tcw-work-stage-skill] --vocab <term> …`
  with a one-sentence description of the interaction area only, with no behavior
  (spec D, Taxonomy).

**`relatesTo` links**

- Edit `relatesTo` in each listed Feature's `meta.yaml`, the skill's documented
  hand edit, as the spec's table gives.

**Checks**

- `tcw taxonomy check`
- `tcw validate`

**Proof**

- AC 15, checked with the loop in Verification.
- Bare `pytest` is green.
- The commit contains only `docs/taxonomy/`.

#### Task 13 — Write the sixteen capabilities and delete the nine they replace

**Every new capability**

- `tcw capabilities add skills/<s> "<name in the spec's form>" --status <Supported|Missing>`
- `tcw capabilities set skills/<s> --field "Feature=<Feature path>" --field "Subject=skill"`
- Write the body in the capability's `description.md` in "As a user or agent, I
  …" form. Find the file with `tcw capabilities path`.
- For `skills/tcw-setup` and `skills/tcw-configure` only: `--status Missing` and
  `--field "Planning doc=2026-09-14-consolidate-the-setup-skills-into-a-single-tcw-setup-skill"`.

**Commits**

Each commit writes a successor and deletes what it replaces together, so the
ledger is never missing either:

1. `skills/tcw-work`, whose body folds in the bodies of `plugin/work-lifecycle`,
   `work/consolidate-plans`, `work/search-the-work-items` and
   `work/audit-work-backlog` as they stood at `<base>`. Then `tcw capabilities rm`
   each of those four.
2. `skills/tcw-report`, `skills/tcw-post-mortem` and `skills/tcw-triage-issues`,
   each folding its predecessor. Then `rm` `plugin/report-an-issue-upstream`,
   `plugin/run-a-post-mortem` and `plugin/triage-github-issues`.
   - In the same commit, change `docs/capabilities/work/complete-a-work-item/description.md:20`'s
     link to `tcw://C/skills/tcw-triage-issues`.
3. `skills/tcw-setup` (`Missing`), folding `taxonomy/bootstrap-the-taxonomy` and
   `capabilities/bootstrap-the-capabilities`. Then `rm` both.
   - In the same commit, reword `plugin/bootstrap-the-cli`'s two `tcw-plugin`
     mentions to `tcw-setup`.
4. The remaining nine, which delete nothing: `skills/tcw-configure` (`Missing`),
   `skills/tcw-taxonomy`, `skills/tcw-capabilities`, `skills/documentation-sync`,
   `skills/tcw-work-stage`, the five `skills/tcw-work-stage-*`,
   `skills/autonomous-work`.

   Only fourteen skills ship before this item, and they are covered across
   commits 1–4.

**This item's capability delta**

- Write `capabilities.yaml` in this item's folder: `new:` lists the sixteen
  `skills/*` paths, and `changed:` lists `plugin/bootstrap-the-cli` and
  `work/complete-a-work-item`.
- Record the nine deletions in the form the dependency item defined (see Before
  starting).
- Commit it with commit 1.

**After each commit**

- `tcw capabilities check` prints `capabilities OK`.
- `tcw validate` exits 0.
- Bare `pytest` is green.

**Proof:** AC 16.

#### Task 14 — Notes on related open items

Add one line under `## Notes` in each item's body document: `initial-request.md`
where present, otherwise `intake.md`. Name this item's slug and say where that
item's text or capability now lives:

- `2026-09-12-configure-an-external-tracker-and-read-its-tickets`,
  `2026-09-12-claim-an-external-tracker-ticket-and-bind-it-to-a-work-item`,
  `2026-09-12-synchronize-the-work-lifecycle-outward-to-the-tracker`,
  `2026-09-12-refuse-local-work-that-no-claimed-tracker-ticket-authorizes`,
  `2026-09-12-surface-an-item-s-tracker-binding-in-the-board-the-projection-and-the-web-app`:
  tracker configuration text goes in the `tcw-configure` skill's `tracker.md`.
- `2026-08-18-serve-version-cut-instructions-from-tcw-config-yaml-instead-of-the-agent-guide`,
  `2026-09-10-let-a-node-declare-its-own-work-item-state-fields`,
  `2026-09-10-record-a-work-item-s-branch-and-let-a-node-declare-its-own-state-fields`:
  new configuration keys are documented in `tcw-configure`, per the
  `Configuration-Key-Change` entry.
- `2026-09-01-fan-the-backlog-audit-out-across-every-connected-work-root`: its
  capability delta names `skills/tcw-work`.
- `2026-09-11-run-the-eval-harness-and-act-on-what-it-finds`: B5 is retargeted;
  B11 and B12 and the `tool_input_*` predicates exist; `files_changed_exactly`
  was fixed.
- `2026-09-11-refine-the-plugin-skills-and-lifecycle-prompts-against-the-eval-findings`:
  it refines the restructured skill set.
- `2026-08-18-report-the-missing-skill-caveat-from-tcw-work-lifecycle-rather-than-the-skill`:
  the caveat it quotes is at `hooks.md:88` at `<base>`, and its line has moved.
- `2026-08-12-separate-the-agent-plugin-from-the-python-cli-source`: `tcw-plugin`
  no longer exists; its install text is in `tcw-setup/references/install.md`.

**Proof:** each note is committed. Neither `tcw work show <slug>` nor
`tcw validate` errors.

## Documentation Sync

Evaluated with `tcw work docs` at plan time. Implementation answers these in one
pass over the finished diff, after task 14.

### Task 15 — `README.md` [Public-API] — fires

Slash commands are removed, and skills are added and renamed.

- `:430-432`: "Fifteen skills … Nine carry a distinct procedure" → "Sixteen
  skills … Ten carry a distinct procedure".
- The skills table (`:438-446`): replace the `tcw-plugin` row with a `tcw-setup`
  row ("Gets TCW working: installs or repairs the CLI, sets up a repository,
  starts a taxonomy or capabilities ledger") and a `tcw-configure` row ("Changes a
  project's configuration: lifecycle bindings, Definition of Done, documentation
  entries, tracker, stores, connected and inherited projects").
- Re-read the Install section (`:205-230`) and "Bootstrapping" (`:348-353`) for
  anything task 11's line edits left reading oddly.

### Task 16 — `docs/release-notes/upcoming.md` [Public-API] — fires

In plain language:

- setup and configuration each have one skill;
- `/tcw-taxonomy-init`, `/tcw-capabilities-init` and `/tcw-docs-sync-setup` are
  gone; ask for the `tcw-setup` or `tcw-configure` skill instead;
- `tcw-plugin` is now `tcw-setup`;
- nine capability entries were merged into one per skill.

### Task 17 — `docs/changelogs/upcoming.md` [Any-Code-Change] — fires

Technical, grouped:

- **Added:** the two skills and their references, the `skill` term and sixteen
  Features, sixteen `skills/*` capabilities, `tool_input_contains` and
  `tool_input_absent`, the `bare` fixture and per-case `fixture` key, the
  `Configuration-Key-Change` documentation entry, and the new tests.
- **Changed:** `files_changed_exactly` compares against `seeded_head`, and
  `seed()` and `variant_for` take variant names. B5 is retargeted; B4 and B8
  gained routing checks. The text moved out of `hooks.md`, `commands.md`, the axis
  skills and `documentation-sync`.
- **Removed:** `tcw-plugin`, the three commands, the nine capability paths with
  their successors, and the skill map.

### `skills/<component>/SKILL.md` [Skill-Driven-Component] — expected not to fire

No component's CLI surface, model, lifecycle or guardrails change. The skills are
themselves the subject of this item, and tasks 4–11 edit them. Re-evaluate at the
documentation pass, and record the verdict and reason in `outcome.md`.

### `skills/tcw-configure/references/<document>.md` [Configuration-Key-Change] — expected not to fire

This entry is added by task 7. No configuration key is added, removed, or changes
meaning. The documents are written by tasks 5–6. Re-evaluate at the documentation
pass.

## Verification

The suite covers ACs 1–3, 6, 9, 10 (partly), 13, 14 and 18–20 through tests added
above, plus bare `pytest` and `tcw validate`. The checks below cover the rest, or
things no test can check. Record every result in `outcome.md`.

1. **AC 4, AC 5.** Run the two `git grep` commands exactly as written in the spec;
   each prints nothing.
2. **AC 7, AC 8.** Read `skills/tcw-setup/SKILL.md`'s routing table and both
   descriptions, and tick each required row and word.
3. **AC 11, renames.** For each of the three moves:

   ```sh
   git log --format=%H <base>..HEAD | while read c; do git show --name-status --find-renames --format= $c; done | grep '^R100'
   ```

   It must list all three moves.
4. **AC 11, partial moves.** Run this Python check once per source range in the
   spec:

   ```sh
   python3 - <<'PY'
   import subprocess, sys
   def lines(rev, path, a, b):
       text = subprocess.run(["git", "show", f"{rev}:{path}"], capture_output=True, text=True, check=True).stdout
       return [l.strip().lstrip("#").strip() for l in text.splitlines()[a-1:b] if l.strip()]
   src = lines("<base>", "<source path>", <start>, <end>)
   dest = open("<destination path>").read()
   missing = [l for l in src if l not in dest]
   print("\n".join(missing) or "all present")
   PY
   ```

   Every missing line must appear in `outcome.md` under "Moved lines changed", with
   its reason.
5. **AC 12.** `grep -c` each required string in each document; each count is 1 or
   more.
6. **AC 15.**

   ```sh
   for p in skill tcw-setup-skill tcw-configure-skill …; do tcw taxonomy show $p; done
   ```

   Compare each `vocabulary:` line with the spec table, then run
   `tcw taxonomy check`.
7. **AC 16.**
   - For each of the fourteen already-shipping skills, `tcw capabilities show skills/<s>`
     must show `**Status:** Supported` and a Feature line.
   - `tcw capabilities show skills/tcw-setup` and `skills/tcw-configure` must show
     `**Status:** Missing` and `**Planning doc:**`.
   - Each of the nine deleted paths must make `show` exit non-zero.
   - `tcw capabilities show plugin/bootstrap-the-cli | grep -c tcw-plugin` prints
     0.
8. **AC 17.** After `tcw work complete`, both `Missing` entries show
   `**Status:** Supported`.
9. **Not checkable by the suite; judged by reading:**
   - **Folded bodies.** Read `skills/tcw-work`'s capability body against the four
     deleted bodies at `<base>` (`git show <base>:docs/capabilities/<path>/description.md`),
     and confirm every behavior they described is still described. Do the same for
     the other folded capabilities.
   - **Text left behind.** Read `hooks.md`, `commands.md`, `transitions.md`, and
     the `## Inheritance` / `## Federation` sections after the cuts, and confirm no
     dangling "both", "below" or "the same way".
   - **Routing.** Read both routers and all usage-skill descriptions, and confirm
     no usage skill still advertises setup or configuration.
10. **Not verified by this item.** Whether agents actually route correctly needs a
    paid eval run, which is
    `2026-09-11-run-the-eval-harness-and-act-on-what-it-finds`. Say so in
    `outcome.md`; do not claim it.

## Notes

- **Traceability.**
  - ACs 1–5 → tasks 4, 8, 11.
  - AC 6 → tasks 7, 10.
  - AC 7 → task 10.
  - AC 8 → tasks 7, 10.
  - AC 9 → tasks 5, 10.
  - AC 10 → tasks 4, 6, 7, 8.
  - AC 11 → tasks 4, 6, 8, 10.
  - AC 12 → task 6.
  - AC 13 → task 6.
  - AC 14 → task 7.
  - AC 15 → task 12.
  - ACs 16–17 → task 13.
  - AC 18 → tasks 1–3, 7, 10, 11.
  - AC 19 → task 7.
  - AC 20 → every task.
- **The riskiest change, in isolation.** Tasks 6 and 13 are the riskiest: text cut
  across skills, and the ledger rewrite. Task 6 runs after the destination skill's
  rename commit and before its router exists, so a mistake there is visible in the
  documents alone. Task 13 runs last, after every skill it describes exists, one
  successor and deletion per commit.
- **Temporary skill count.** Between tasks 10 and 11 the plugin ships seventeen
  skills, and the Codex manifest says so. That keeps
  `test_the_codex_description_counts_the_skills_it_ships` green at every commit.
- **Delegation.** Tasks 1–3 are independent of each other and of Phase B, and
  could go to subagents working in parallel. Tasks 4–13 edit overlapping files and
  should run in one session, in order.
