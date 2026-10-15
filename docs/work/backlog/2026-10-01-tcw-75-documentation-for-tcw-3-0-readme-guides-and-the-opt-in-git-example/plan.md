# Plan — Documentation for TCW 3.0: README, guides and the opt-in git example

This plan follows the spec as reviewed on 2026-10-02 and amended before
planning on 2026-10-15 (spec, "Pre-plan amendments"). Where this plan names a
file, line or function, it was read on `epic/tcw-3.0` at `5b0dcf95`.

## Rules for this item (the owner's, for the TCW 3.0 epic)

- **Where the work happens.** A worktree `.worktrees/2026-10-01-tcw-75-documentation-for-tcw-3-0-readme-guides-and-the-opt-in-git-example`
  on branch `work/2026-10-01-tcw-75-documentation-for-tcw-3-0-readme-guides-and-the-opt-in-git-example`,
  made from `epic/tcw-3.0` (made by hand with `git worktree add`, since the
  3.0 CLI has no `--worktree`). The board, `docs/work/` on `main`, is edited by
  hand or with the released 2.8.1 `tcw`, never with the worktree's code; this
  item's `plan.md`, `outcome.md`, `capabilities.yaml` and spec notes are
  committed on `main`.
- **Which source runs.** A private virtual environment, never a re-pointed
  shared install: `python -m venv --system-site-packages <scratch>/tcw75/venv`,
  then `<scratch>/tcw75/venv/bin/pip install -e <worktree> --no-deps`, and
  `<scratch>/tcw75/venv/bin/pip install --ignore-installed pytest` so that bare
  `pytest` also resolves inside the environment. pytest and `tcw` run with the
  worktree as the current folder and the environment's `bin` first on `PATH`.
- **Do not run the full pytest suite.** Each task runs the test files it
  names, every file under `tests/` that reads a file the task changed (found
  with `grep -rl '<file name>' tests`), and these standing guard files, all
  present on the branch: `tests/test_cli_contract.py`,
  `tests/test_cli_help_standard.py`, `tests/test_static_guards.py`,
  `tests/test_cli_handler.py`, `tests/test_tree_store_raises.py`,
  `tests/test_no_node.py`, `tests/test_ledger_3_0.py`,
  `tests/test_documented_cli_surface.py`, plus `tests/test_doc_allowance.py`
  and `tests/test_shipped_text.py`, which read the same allowance lists every
  documentation task shrinks. `pytest --collect-only -q` stays clean after
  every task. The full suite (criterion 12) runs at the end of the epic.
- **New tests only.** Write the 3.0 tests the spec calls for. A 2.x test that
  breaks because 2.x behavior is gone is deleted or skipped, not ported, and
  each one is listed in `outcome.md`.
- **Every new guard is mutation-checked**: break what it claims to observe,
  confirm it goes red for the stated reason, restore (Task 17).
- **One commit per task**, on the work branch, with no co-author or session
  lines in the message.
- **No `tcw` against this repository.** With the epic's code, every `tcw`
  command here stops on the 2.x `tcw-config.yaml` until TCW-76 migrates it.
  A task that needs a working `tcw` builds a fixture project in a scratch
  folder, with `HOME` and `XDG_CONFIG_HOME` pointed at scratch folders and
  `TCW_NO_PERSONAL_CONFIG=1` unless the task is about personal configuration.

## Blockers

- `blocked_by`: TCW-74 and TCW-77 (both complete on `epic/tcw-3.0`, graveyard
  `64a2eb94` and `0a23906f`). No other blocker.
- This item blocks TCW-76 (its `state.yaml` lists it), which links to the git
  example's script path, the README index row for the migration guide, and
  removes the link exception of Task 1.
- **A version must not be cut between TCW-74 and the end of this item**
  (TCW-74's note 4): the skills already point to a configure Jira reference
  that only Task 3 creates.

## Before the first task: what the branch already has

- `tests/doc_vocabulary.py` (TCW-74) holds criterion 2's table verbatim
  (`PATTERNS`) and `scan(text)`; the new scan imports it.
- `tests/doc_allowance.py` holds five lists; `tests/test_doc_allowance.py`
  proves each entry is really gone. Today these documents name an entry
  (computed with `tests/test_shipped_text.py`'s `_names` and `_flag_named`):
  README, every guide but `web-viewer.md`, `docs/lifecycle/implementation.md`,
  `skills/configure/SKILL.md` and four of its references; and, outside this
  item, `AGENTS.md` (`tcw work stage gate`, TCW-76's part of the file) and
  three capability records:
  `docs/capabilities/work/configure-the-work-store-location/description.md`
  (`tcw work init`), `docs/capabilities/cli/validate-a-project/description.md`
  (`tcw taxonomy check`, `tcw capabilities check`) and
  `docs/capabilities/work/configure-the-work-lifecycle/description.md`
  (`work.lifecycle`, `work.tracker`, `work.retain`,
  `work.auto-commit-transitions`, `work.publish-transitions`,
  `work.trunk-branch`).
- `tests/test_shipped_text.py:33` excludes `skills/configure/` from TCW-74's
  scans; `SHIPPED` (:67) lists every other skill file.
- `tests/test_upcoming_entries.py` refuses leading text in every upcoming
  entry.
- `tests/test_configuration_text_home.py` holds two 2.x tests (tracker
  inheritance sentences, the router's tracker row).
- `tests/test_repo_lifecycle.py` is gone; nothing checks the four
  lifecycle-document phrases.
- The 3.0 command surface (walked from `tcw.cli.build_parser()`): top level
  `init`, `provision`, `validate [--remote]`, `serve`, `projects list`,
  `config show [--origin]`; `taxonomy` and `capabilities` with `list`, `add`,
  `show`, `path`, `rm`, `search`, `extends add|rm`, plus `capabilities set`,
  `reset`, `drift`; `work` with `new`, `list`, `show`, `path`, `edit`,
  `advance`, `discard`, `comment`, `rename`, `stage prompt`, `procedure`,
  `lifecycle`, `docs`, `tags list|add|rm`, `tickets list|adopt`.
- Exit codes (`tcw/exit.py`): 0 OK, 1 ERROR, 2 USAGE, 3 REFUSED, 4 NOT_FOUND,
  5 UNREACHABLE, 6 MOVED_WITH_PROBLEM.
- The backend interface (`tcw/work/backend.py:70-114`) has twelve operations,
  the twelfth being `is_item_folder` (TCW-77).
- The procedures are `audit-backlog`, `create-work`, `documentation-sync`,
  `pause-work`, `search`, `triage-issues`, `unattended-work`
  (`tcw.store.base.PROCEDURE_IDS`).

## Choices this plan makes

1. **The owned-document scans grow one document at a time.**
   `tests/test_docs_describe_3_0.py` holds a tuple `REWRITTEN` of the owned
   documents finished so far, and the vocabulary scan (criterion 2), the link
   check (criterion 3) and the allowance-name check (criterion 4) are
   parametrized over it. Each document task adds its files to the tuple in the
   same commit, so a document is guarded from the moment it is rewritten and
   the suite is green at every commit. Task 15 replaces the tuple with the
   full owned set, derived by glob, and asserts it.
2. **The `AGENTS.md` part** that is owned is the text from the line
   `### Working in a git worktree` to the next line starting `## `; the test
   reads only that span (a helper, `agents_worktree_section()`), and fails if
   the heading is missing.
3. **Links** are Markdown inline links `[text](target)` outside fenced code.
   A target starting `http:`, `https:`, `mailto:` or `tcw:` is skipped. A
   relative target must exist, resolved from the document's folder. An
   `#anchor` on a link into an owned document must equal a heading's anchor,
   made the way GitHub makes one: lower-case, backticks and punctuation other
   than `-` and spaces removed, spaces turned into `-`, and `-1`, `-2` added
   to repeated headings. The one exception is a constant
   `PENDING_TARGETS = ("docs/migration-guide-2.8-to-3.0.0.md",)` whose comment
   says TCW-76 removes it when the guide exists.
4. **Criterion 4's name check reuses TCW-74's helpers** (`_names`,
   `_flag_named` in `tests/test_shipped_text.py`) over all five allowance
   lists, so the two checks cannot read a document differently.
5. **The "still named somewhere" check (TCW-74's note 2) goes in
   `tests/test_doc_allowance.py`**, beside the guards that each entry is
   really gone: for every entry of the five lists, at least one live document
   (`tests/test_documented_cli_surface.DOC_FILES`) names it. It is added in
   Task 14, when the dead entries are removed in the same commit.
6. **Criterion 7's sample values** are written per key path, each loaded on
   its own through `tcw.config.load_config` in a `tmp_path` project that is a
   git repository, with `TCW_NO_PERSONAL_CONFIG=1`. The base file is `id: x`.
   For every `work.jira.*` path and `work.stages.*.status`, the base adds
   `work.backend: jira` and this complete block, checked to load with no
   problems on the branch:
   `site: https://example.atlassian.net`, `project: TCW`,
   `credentials: {email-env: TCW_JIRA_EMAIL, token-env: TCW_JIRA_TOKEN}`,
   `fields: {project: customfield_1, item: customfield_2, effort: customfield_3, complexity: customfield_4}`,
   and a `status` for every enabled stage (`Inbox`, `Request`, `Specifying`,
   `Planning`, `In Progress`, `In Review`, `In QA`, `Done`, `Discarded`).
   Values: `work.path: tcw-work`; `work.repository: {url: https://example.com/store.git, ref: main}`;
   `work.backend: filesystem`; `work.tags: [auth]`; `work.documentation: []`;
   `work.procedures.search: [{blob: hello}, {inherit: true}]`;
   `work.stages.spec.enabled: true`; `work.stages.spec.status: Specifying`;
   `work.stages.spec.prompt: [{inherit: true}]`;
   `work.stages.spec.pre: [{command: "true"}]`;
   `work.stages.spec.post: [{command: "true"}]`; `work.hooks.timeout: 60`;
   `work.hooks.output-cap: 1000`; `work.jira.issue-type: Task`;
   `work.jira.inbox-query: 'status = "To Do"'`; `work.jira.timeout: 30`;
   `work.jira.priorities: {highest: Highest, high: High, medium: Medium, low: Low, lowest: Lowest}`;
   the other `work.jira.*` paths are the base block's own values. The
   combined file was loaded on the branch with no problems.
7. **The exit-code table in `docs/guide/cli.md`** is a Markdown table whose
   first column is the code as a bare number. The test reads every
   module-level integer in `tcw/exit.py` and compares the set of numbers and
   the count of rows.
8. **The commit script is run with `sh <path>`** in its test, as the example
   binds it, and is committed with mode 0755 so a project can also run it
   directly.
9. **One fold-in outside the ownership table:** `evals/coverage.py:68` names
   `tracker.md`, which Task 3 removes; the line changes to `jira.md` and adds
   `personal.md`. It is TCW-74's file and TCW-74 is complete; the change is a
   fact the rename makes false, so it travels with the rename (flagged for
   the orchestrator).

## Tasks

Every task ends by running its named tests plus the standing files, and
`pytest --collect-only -q`.

### Task 1: The scanning machinery, guarding nothing yet (criteria 2, 3, 4)

- **Creates** `tests/test_docs_describe_3_0.py`: `REWRITTEN = ()`;
  `agents_worktree_section()`; the vocabulary scan over `REWRITTEN` using
  `tests.doc_vocabulary.PATTERNS`/`scan`; the link check (choice 3) with
  `PENDING_TARGETS`; the allowance-name check (choice 4). Each scanner gets a
  test of its own on inline text: a line with `tcw work start` is a hit; a
  link to a missing file and to a missing heading are reported; a link to
  `PENDING_TARGETS[0]` is not; `` `tcw work stage gate <slug>` `` is found as
  an allowance entry.
- **Proves:** the new file passes (the per-document tests collect zero
  cases); standing files.

### Task 2: The configure references and router (Design 6; criteria 6, 7)

- **Modifies** `skills/configure/SKILL.md` (router: one row per reference;
  `description` and `when_to_use` naming 3.0 areas only; `allowed-tools`
  without `Bash(git *)`; keeps `dynamic_skill: false`, the version-check
  line, and the sentences on `id` and `tcw work tags add`);
  `skills/configure/references/work.md` (rewritten: every `work.*` key in the
  Design 6 table, each in its own heading with its label line; the binding
  kinds table from `tcw/work/config.py:31-38`; how hooks run and every
  variable; `generate:` variables and stdin; the
  `{{tcw:request}}…{{/tcw:request}}` pair; `work.procedures` with the seven
  procedure ids and no deleted id; no `tcw work procedure prompt`);
  `skills/configure/references/projects.md` (rewritten: `projects` with
  `parent`, `children`, `upstream`, the delegation `jira` block and its five
  keys, `TCW_PROJECT_<ID>`, the five delegation cases, `extends`; no
  `start`, `drop`, `delegate` verbs); `stores.md` and `docs-sync.md`
  (edited: every vocabulary hit removed, `<slug>` placeholders become
  `<folder>`, the folder-name rule of Design 10.5, `docs-sync.md` still says
  `work.documentation` and "prefer config").
- **Creates** `skills/configure/references/jira.md` (every `work.jira` key,
  each under its own heading; stages to statuses; required custom fields;
  `tcw validate --remote`; each project states its own block) and
  `skills/configure/references/personal.md` (Design 6 row; the table of
  every key path in criterion 7 with its label; a sample of
  `tcw config show --origin` output copied from a run in a scratch fixture,
  including one `- builtin: true  # tcw/work/prompts/<stage>.md` line).
- **Deletes** `skills/configure/references/tracker.md` (`git rm`); the
  replacement carries none of its `{slug}` viewer text, status folders,
  "served under its path" or `work.retain` (TCW-74/77 note 8).
- **Replaces** `tests/test_configuration_text_home.py` with criterion 6 (every
  reference linked from the router, every router link resolves, no
  `tracker.md`, frontmatter free of criterion 2's patterns, one heading per
  key path in exactly one reference with a label matching the table) and
  criterion 7 (the key-path constant; `personal.md`'s table has exactly one
  row per path; the `Overridable` and `Personal only` rows equal
  `tcw.config.PERSONAL_KEYS`, `user.name` alone `Personal only`; each `work.*`
  path loads with choice 6's value and no problem naming it).
- **Modifies** `evals/coverage.py:68` (choice 9).
- **Modifies** the records: `docs/capabilities/skills/configure/description.md`
  (lists the Design 6 areas; its `Planning doc` line in `meta.yaml` is left
  for TCW-76); `docs/taxonomy/configure-skill/description.md` (3.0 areas) and
  `docs/taxonomy/configure-skill/meta.yaml` (`relatesTo` gains
  `personal-configuration`).
- **Adds** the six configure files to `REWRITTEN`.
- **Proves:** `tests/test_configuration_text_home.py`,
  `tests/test_docs_describe_3_0.py`, `tests/test_documentation_sync_wiring.py`,
  `tests/test_skill_path_pointers.py`, `tests/test_dynamic_skill_marker.py`,
  `tests/test_check_versions.py`, `tests/test_eval_coverage.py`, standing
  files (`tests/test_ledger_3_0.py` covers the two records).

### Task 3: TCW-74's scans read the configure skill (Design 1.5)

The riskiest test change, alone in its commit.

- **Modifies** `tests/test_shipped_text.py`: the `EXCLUDED` constant, its
  comment and every use of it are deleted (`_shipped_text`'s filter, the
  `include_excluded` argument, the disposition test's filter, and the
  allowance branch of `test_every_command_named_in_shipped_text_exists`);
  `SHIPPED` gains the seven configure files; the walk test's last assertion
  becomes a positive one (`skills/configure/SKILL.md` is scanned);
  `VOCABULARY_ALLOWED` gains `skills/configure/references/personal.md` with
  the exact `builtin: true` output line and the reason "`tcw config show`
  prints it for a built-in entry (review decision R8)"; `GIT_ALLOWED` gains
  each exact phrase the git scan reports in the configure files that is a
  fact rather than an instruction (expected: the linked-worktree sentence in
  `personal.md`, the `ref` of a `repository` entry in `stores.md`), each with
  its reason. Any other hit is reworded in the reference, not allowed.
- **Proves:** `tests/test_shipped_text.py` in full, including
  `test_no_owned_skill_grants_git`, `test_every_git_allowance_is_still_needed`,
  `test_every_vocabulary_allowance_is_still_needed`,
  `test_every_command_named_in_shipped_text_exists` for the configure files
  without the allowance; standing files.

### Task 4: The lifecycle documents (Design 7.1-7.3; criterion 9)

- **Modifies** `docs/lifecycle/abstraction.md` (rewritten per Design 7.1:
  the premise, `## The backend interface` with twelve bold-named bullets,
  the litmus question word for word, the ownership question word for word,
  "Abstract spine, filesystem leverage", the use-freely and keep-out lists,
  binding comment at `:1-2` unchanged);
  `docs/lifecycle/implementation.md` (Design 7.2: the backend-interface rule
  at `:9`; the other-repository section in project vocabulary with
  `work_path`, `open_backend`, `git_root`, `find_project_root`,
  `descendant_projects`, and no `--include-descendants`; "Beginning
  implementation" deleted; ":71" says "project"; the phrases "assert that
  the message it replaces" and "another program owns" kept);
  `docs/lifecycle/harness.md` (`:12`, Design 7.3).
- **Modifies** `tests/test_docs_describe_3_0.py`: criterion 9's checks (the
  four moved phrases; the ownership question; the twelve names exactly; no
  `\bmv\b`); the three files join `REWRITTEN`.
- **Proves:** `tests/test_docs_describe_3_0.py`,
  `tests/test_falsification_rule.py`, standing files.

### Task 5: The worktree section of `AGENTS.md` (Design 7.4)

- **Modifies** `AGENTS.md:80-101` only (the heading becomes
  `### Working in a git worktree`; TCW creates no worktree; the import-hook
  reason kept; the fix is `python -m venv .venv` and
  `.venv/bin/pip install -e '.[dev]'` inside the worktree, with pytest and
  `tcw` run from it; the `start --worktree` and `complete` sentences go).
  `CLAUDE.md` is a link to it and is not edited. The rest of the file, and
  its `tcw work stage gate`, are TCW-76's.
- **Modifies** `tests/test_docs_describe_3_0.py`: the section joins the
  scans.
- **Proves:** `tests/test_docs_describe_3_0.py`,
  `tests/test_documentation_sync_wiring.py` (reads `AGENTS.md`), standing
  files.

### Task 6: The commit script and its behavior (Design 8.1; criterion 5, first part)

- **Creates** `docs/guide/examples/commit-item-after-move.sh` (Design 8.1's
  text exactly, mode 0755) and `tests/test_git_example.py` with the four
  repository cases of criterion 5 (one commit with only item paths; other
  staged and unstaged changes left as they were; no change, no commit, exit
  0; a nested second repository committed, the outer untouched). Each case
  builds its own repositories under `tmp_path` with a local `user.name` and
  `user.email`.
- **Proves:** `tests/test_git_example.py`; standing files.

### Task 7: The configuration guide and the git example (Design 5.3, 8; criterion 5, second part)

- **Modifies** `docs/guide/configuration.md` (rewritten per Design 5.3, with
  the section "Example: keeping git in step with each stage change (something
  your project adds)" per Design 8: the script shown in a `sh` block, the
  first `yaml` block exactly Design 8.2's, the push fragment, what the
  example does not do, the personal variant with `- inherit: true`; no
  `procedure prompt`, no deleted procedure id, no 2.x viewer text at `:252`;
  the example placeholders `<folder>`).
- **Modifies** `tests/test_git_example.py`: the `sh` block under the heading
  equals the script byte for byte; the first `yaml` block under the heading,
  with `id: x`, loads through `load_config` with no problems; every stage with
  a `prompt` resolves to the pull blob then the `builtin` binding; no `pre`
  key; the blob contains `git -C`. The guide joins `REWRITTEN`.
- **Proves:** `tests/test_git_example.py`, `tests/test_docs_describe_3_0.py`,
  standing files. **By hand, in a scratch fixture** with that configuration:
  `tcw work stage prompt spec <slug>` prints the pull text before the
  built-in prompt, and `tcw work advance` on a fixture item commits its
  folder (recorded in `outcome.md`).

### Task 8: The CLI guide (Design 9; criterion 8)

- **Creates** `docs/guide/cli.md` (Design 9's outline; one exit-code row per
  `tcw/exit.py` constant with Design 9's meanings; two script examples).
- **Creates** `tests/test_cli_guide.py` (choice 7). The guide joins
  `REWRITTEN`.
- **Proves:** `tests/test_cli_guide.py`, `tests/test_docs_describe_3_0.py`,
  `tests/test_documented_cli_surface.py` (every command in the guide exists),
  standing files.

### Task 9: The work guide (Design 5.1; criterion 4's verbs)

- **Modifies** `docs/guide/work.md` (rewritten per Design 5.1, in that order;
  links to `cli.md`, `configuration.md`, `jira.md`; no 2.x viewer text).
- **Modifies** `tests/test_documented_cli_surface.py`: a second tuple,
  `WORK_GUIDE_VERBS = ("tcw work advance", "tcw work discard",
  "tcw work tickets adopt")`, checked in `docs/guide/work.md` only by its own
  parametrized test (the existing test reads TCW-74's `commands.md` too). The
  guide joins `REWRITTEN`.
- **Proves:** `tests/test_documented_cli_surface.py`,
  `tests/test_docs_describe_3_0.py`, standing files.

### Task 10: The Jira guide (Design 5.2)

- **Modifies** `docs/guide/jira.md` (rewritten from scratch per Design 5.2;
  status names `Specifying`, `Planning`, `In QA`; credentials by variable
  name; request sections as `tcw/work/prompts/request.md:24-29` names them;
  no 2.x viewer text). The guide joins `REWRITTEN`.
- **Proves:** `tests/test_docs_describe_3_0.py`,
  `tests/test_documented_cli_surface.py`, standing files.

### Task 11: The multi-project guide (Design 5.4)

- **Modifies** `docs/guide/multi-repo.md` (rewritten per Design 5.4; the
  sections on epic roll-ups, `delegate`, `escalate`, the store lock and a
  "node that keeps no work store" go; no `--include-descendants`, no
  `provision --refresh`; no 2.x viewer text at `:86`). The guide joins
  `REWRITTEN`.
- **Proves:** `tests/test_docs_describe_3_0.py`,
  `tests/test_documented_cli_surface.py`, standing files.

### Task 12: The taxonomy, capabilities and validation guides (Design 5.5, 5.6)

- **Modifies** `docs/guide/taxonomy-and-capabilities.md` (Design 5.5,
  including every hit the scan reports today: `taxonomy check` at `:35`,
  `:48`; `capabilities check` at `:89`; "node" at `:111`, `:112`, `:170`;
  `-s`, `-p`, `--local-only` and `capabilities extends <id>` rewritten to
  the 3.0 forms) and `docs/guide/linking-and-validation.md` (Design 5.6,
  including "no longer" at `:94` reworded inside the kept pre-2.5.0 section,
  `--no-recurse` and the viewer text at `:26`). Both join `REWRITTEN`.
- **Proves:** `tests/test_docs_describe_3_0.py`,
  `tests/test_documented_cli_surface.py`, standing files.

### Task 13: The README, and the inbox template deleted (Design 4, 5.7; criterion 1)

- **Modifies** `README.md` per Design 4, section by section, including the
  Node.js requirement at `:110` and the web app section (`:768-805`), the
  `node --version` line, the documentation index (every guide, `cli.md`, the
  configure references row, every migration guide including 2.4 → 2.5 and
  2.8 → 3.0.0, no inbox template), the worktree sentence at `:845-848`
  linking `AGENTS.md`'s section, and the Releasing paragraph's folder-name
  rule.
- **Deletes** `docs/work-inbox-template.md`, and edits the comment in
  `tests/test_documented_cli_surface.py` (`ARCHIVAL`) that names it as a live
  file.
- **Modifies** `tests/test_docs_describe_3_0.py`: criterion 1's checks; the
  README joins `REWRITTEN`.
- **Proves:** `tests/test_docs_describe_3_0.py`,
  `tests/test_documented_cli_surface.py`,
  `tests/test_documentation_sync_wiring.py`, standing files.

### Task 14: The allowance shrinks to what other items' files name (Design 1.5; criterion 4; notes 1, 2, 7)

- **Modifies** `tests/test_doc_allowance.py`: choice 5's check.
- **Modifies** `tests/doc_allowance.py`: every entry no live document names
  is removed, which is expected to empty `REFUSED_VALUES` (note 1),
  `REMOVED_FLAGS` (note 7's `--include-descendants` among them) and
  `REMOVED_FORMS`, and to leave only entries named by `AGENTS.md` or the
  three capability records listed under "Before the first task". The module
  docstring and `tests/test_shipped_text.py` keep working with an empty
  list; a list emptied entirely stays as an empty tuple, since TCW-76 deletes
  the module.
- **Writes** in this item's implement round (`outcome.md` on `main`) each
  remaining entry with the file that names it and its owner.
- **Proves:** `tests/test_doc_allowance.py`, `tests/test_shipped_text.py`,
  `tests/test_documented_cli_surface.py`, `tests/test_docs_describe_3_0.py`,
  standing files.

### Task 15: The owned set is complete (Design 3; criteria 2, 3, 10)

- **Modifies** `tests/test_docs_describe_3_0.py`: `REWRITTEN` gives way to
  `OWNED`, built by glob (`README.md`; `docs/guide/*.md` but `web-viewer.md`;
  the three lifecycle files; `skills/configure/SKILL.md` and
  `references/*.md`) plus the `AGENTS.md` section; a test asserts the scanned
  set equals it; criterion 10's existence checks (two files gone, three
  present).
- **Proves:** `tests/test_docs_describe_3_0.py`, standing files.

### Task 16: Release notes and changelog (Design 10; criterion 11)

- **Modifies** `docs/changelogs/upcoming/README.md` and
  `docs/release-notes/upcoming/README.md` (`:6`, the folder-name rule).
- **Creates** `docs/release-notes/upcoming/2026-10-01-tcw-75-documentation-for-tcw-3-0-readme-guides-and-the-opt-in-git-example.md`
  (the 3.0.0 introduction before any `##`, linking
  `docs/migration-guide-2.8-to-3.0.0.md`; then `## Documentation`) and the
  same name under `docs/changelogs/upcoming/` (`## Added`, `## Changed`,
  `## Removed`, per Design 10.4).
- **Modifies** `tests/test_upcoming_entries.py` (Design 10.2: one named
  exemption, its docstring corrected) and adds criterion 11's test there: the
  entry has text before its first `##` that links the migration guide, and
  `scripts.cut_version.combine()` over the current release-note entries puts
  that text first.
- **Proves:** `tests/test_upcoming_entries.py`, `tests/test_cut_version.py`,
  standing files.

### Task 17: Mutation checks, collection, and the record

- For each guard below, make the break in a scratch copy or in the working
  tree, run the one test, confirm it fails for the stated reason, restore,
  and record the result in `outcome.md`:
  1. `tcw work start` inserted into a copy of `docs/guide/work.md` → the
     vocabulary scan fails on that line (criterion 2's own mutation).
  2. A link to `docs/guide/nowhere.md` and one to `cli.md#no-such-heading`
     in an owned document → the link check fails on each.
  3. `tcw work list --status x` in an owned document → criterion 4's name
     check fails naming `REMOVED_FLAGS`.
  4. An allowance entry nobody names added to `tests/doc_allowance.py` →
     choice 5's check fails.
  5. The `Overridable:` label of `work.stages.*.post` changed to `Shared:` →
     criterion 6 fails; a row removed from `personal.md`'s table → criterion
     7 fails; a path added to `PERSONAL_KEYS` in a scratch copy → criterion 7
     fails.
  6. `-- .` removed from the script's `git commit` line → the
     staged-elsewhere case fails; `- inherit: true` removed from the guide's
     block → the built-in-prompt check fails; one byte changed in the guide's
     `sh` block → the identity check fails.
  7. A row added to `cli.md`'s exit table → criterion 8 fails.
  8. One bullet removed from `## The backend interface` → criterion 9 fails.
  9. The heading after `## Overview` renamed → criterion 1 fails.
  10. The introduction moved under a `##` heading → criterion 11 fails; a
      second entry with leading text → the narrowed upcoming-entry test fails.
  11. A filter skipping `skills/configure/` put back into `_shipped_text` →
      the walk test fails.
- `pytest --collect-only -q` clean; every test file this plan touched, run
  once more together.
- **Writes** `outcome.md` on `main`: per criterion, the evidence; criterion
  12 deferred to the end of the epic by the owner's rule; the mutation
  results; the remaining allowance entries and their owners; the deleted or
  skipped 2.x tests (expected: the two in `test_configuration_text_home.py`,
  replaced, not ported).

## Documentation Sync

This item is documentation, so most entries are the work itself:

| Entry | Trigger | Answered by |
| --- | --- | --- |
| `README.md` | Public-API | Task 13 |
| `docs/guide/jira.md` | Tracker-Change | Task 10 |
| `docs/guide/<topic>.md` | Guide-Topic-Change | Tasks 7, 8, 9, 11, 12 (`web-viewer.md` is TCW-77's and not touched) |
| `docs/release-notes/upcoming/<folder>.md` | Public-API | Task 16, this item's own file only |
| `docs/changelogs/upcoming/<folder>.md` | Any-Code-Change | Task 16, this item's own file only |
| `skills/<component>/SKILL.md` | Skill-Driven-Component | Task 2 (`skills/configure/SKILL.md`); no other skill changes |
| `skills/configure/references/<document>.md` | Configuration-Key-Change | Task 2 (no key changes, but every reference is rewritten) |

`<folder>` is the item's folder name, never the full slug (Design 10.1).
The `documentation-sync` skill is invoked before the item is reported
complete, after Task 17.

## Verification

What the suite cannot check, and how it is checked:

1. **Criterion 1, by reading:** the new README section makes Design 4.6's
   four points in order, and point 3 says "could".
2. **Criterion 10, by reading:** each rewritten or edited document follows its
   outline in Designs 4 to 7, checked section by section by the reviewer.
3. **Writing rules (Design 2), by reading:** plain language with each term
   defined where it first appears; both backends described side by side with
   the filesystem first; git always the project's choice; configuration keys
   explained only in the configure references, with guides linking there.
4. **Accuracy against the code:** a reviewer runs, in a scratch fixture
   project for each backend that does not need Jira, a sample of the
   commands each guide shows (at least one per guide), and compares the
   printed output and exit code with what the guide says. Jira-only
   behavior is checked against TCW-71's code and tests, not a live site.
5. **The git example under both harnesses:** it uses only `prompt` and
   `post`, which `tcw work stage prompt` and `tcw work advance` run the same
   way under Claude Code and Codex; Task 7's hand run is the evidence.
6. **Criterion 12** is deferred to the end of the epic by the owner's rule.
7. **Review:** a bounded adversarial review (the epic's approval rule), split
   into the configure skill and its tests (Tasks 2, 3, 14), the guides and
   README (Tasks 4 to 13), and the tests and release entries (Tasks 1, 15, 16,
   17), then one combined pass over the whole difference.
8. **Board and ticket:** this item is moved by hand on `main`, and TCW-75 is
   moved by hand in Jira, as earlier children were.

## Criterion-to-task table

| Criterion | Tasks |
| --- | --- |
| 1 README structure | 13 (test), Verification 1 |
| 2 No 2.x vocabulary | 1 (scan), 2-13 (each document joins), 15 (full set), 17 (mutation) |
| 3 Links resolve | 1 (check), 2-13, 15, 17 |
| 4 No phantom commands, allowance not named | 1, 9 (work-guide verbs), 14 |
| 5 Git example works | 6, 7 |
| 6 Configure skill consistent | 2, 3 |
| 7 Override table matches code | 2 |
| 8 Exit-code table matches code | 8 |
| 9 Lifecycle documents | 4 |
| 10 Inventory carried out | 2 (tracker.md, personal.md), 6 (script), 8 (cli.md), 13 (template), 15 (test), Verification 2 |
| 11 Release notes | 16 |
| 12 Full suite | deferred (Verification 6) |

Every task traces to a criterion: Task 1 to 2-4; 2 to 6, 7, 10; 3 to 6
(Design 1.5); 4 to 9; 5 to 2 (Design 7.4); 6 to 5; 7 to 5; 8 to 8; 9 to 4;
10 to 2, 3; 11 to 2, 3; 12 to 2, 3; 13 to 1, 10; 14 to 4; 15 to 2, 3, 10;
16 to 11; 17 to every guard.

## Notes from TCW-74 and TCW-77, one by one

| Note | Task |
| --- | --- |
| 1 `procedure prompt` still named | 2 (`work.md`), 7 (`configuration.md`), 13 (README); entry removed in 14 |
| 2 nothing notices a dead allowance entry | 14 (choice 5's check) |
| 3 deleted procedure ids still listed | 2 (`work.md`), 7 (`configuration.md`) |
| 4 the configure Jira reference does not exist | 2 (`jira.md`); no version cut until this item ends |
| 5 2.x `tcw serve` text | 13 (README), 7, 9, 10, 11, 12 (guides) |
| 6 `Planning doc` on records | Not this item's: TCW-76 removes the field from every record (TCW-76 spec Design 3.7, epic decision 9). On the branch 13 `meta.yaml` files carry it today, `skills/configure` among them; Task 2 edits that record's description and leaves the line. Recorded in `outcome.md` (Task 17). |
| 7 `--include-descendants` entry | 4 (`implementation.md`), 11 (`multi-repo.md`); entry removed in 14 |
| 8 2.x viewer and verbs in configure references | 2 (`tracker.md` deleted, `projects.md` rewritten) |

## Notes

- The abstraction litmus test: this item adds and changes no operation. The
  rewritten `abstraction.md` names the twelve operations and passes each
  through both questions; the git example uses only `prompt` and `post`,
  which both backends run the same way, and tolerates a move that changes no
  file (spec, "Abstraction litmus test").
- Two facts outside this item's files go to the orchestrator rather than
  being changed here: `skills/README.md:85` still says "TCW-75 rewrites this
  skill" (TCW-74's file), and `tcw/store/base.py:5-6`'s docstring still says
  remote adapters are "possible but unbuilt" (Python text is TCW-73's).

## Amendments after the plan review (2026-10-15)

An adversarial review of this plan (one round, `adversarial-spec-reviewer`)
returned NOT DONE with two must-fix findings and eight to handle during
implementation. Each was checked against the branch; all are accepted, and
they override the task text above where the two differ.

1. **Links to text a later task writes (must-fix).** Task 2's `stores.md`
   does not link to the git example; Task 7 adds that link when the heading
   exists. In general, a task that adds or renames headings in a guide also
   fixes every anchor into that guide from a document already in
   `REWRITTEN`, in the same commit, so the link check stays green.
2. **The `AGENTS.md` section is scanned as text, not as a file (must-fix).**
   Task 3 changes `_names(doc, entry)` and `_flag_named(doc, command, flag)`
   in `tests/test_shipped_text.py` to take the document's text (callers pass
   `path.read_text(...)`), so criterion 4's check can pass the owned span of
   `AGENTS.md` alone. Until Task 3, the allowance-name check in Task 1 reads
   text through a local adapter; Task 5 relies on the text form.
3. **Mutation 17.3** inserts `tcw work init` (still in `REMOVED_COMMANDS`
   after Task 14), not `tcw work list --status x`.
4. **Criteria 6 and 7's key paths are spelled in full**, with `*` for a
   name chosen by the project (`work.stages.*.post`, `projects.parent.*.jira.site`),
   never `<stage>`: 57 paths, each its own heading and its own row. Headings
   live in exactly one reference: `work.md` holds every `work.*` path but
   `work.jira.*` and `work.documentation`; `jira.md` holds `work.jira.*`;
   `docs-sync.md` holds `work.documentation`; `stores.md` holds
   `taxonomy.path`, `taxonomy.repository`, `capabilities.path`,
   `capabilities.repository` (and describes `work.path` and
   `work.repository` by linking to `work.md`'s headings);
   `projects.md` holds `id`, `taxonomy.extends`, `capabilities.extends` and
   every `projects.*` path; `personal.md` holds `user.name`.
5. **Criterion 2's built-in mutation is a pytest case** (Task 1, extended
   in Task 9): it copies a real owned document to `tmp_path`, inserts
   `tcw work start`, and asserts the scan reports that line. 17.1 stays as
   the hand check.
6. **Task 3's `GIT_ALLOWED`:** about thirteen git-scan hits exist in
   `stores.md` and `projects.md` today. Each is reworded where the word is
   an instruction; where it is a fact (a linked git worktree, a `.git` URL
   in an example, a `ref`, an anchor such as `#example-keeping-git-in-step-…`)
   it is allowed with its reason, as spec Design 1.5 permits.
7. **Anchors keep underscores** (`TCW_PROJECT_<ID>` → `tcw_project_id`), as
   GitHub does; choice 3's punctuation rule removes everything except
   letters, digits, `-`, `_` and spaces.
8. **Task 2's record edits** (`docs/capabilities/skills/configure`,
   `docs/taxonomy/configure-skill`) are checked by running the branch's
   `tcw validate` in a scratch fixture holding copies of the edited records
   and the records they link to; the result goes in `outcome.md`.
9. **Note 3 in the guide:** Task 7 ends with
   `grep -nE 'consolidate-plans|decompose|delegation|post-mortem' docs/guide/configuration.md`
   printing no procedure-id use, recorded in `outcome.md`.
10. `SHIPPED` starts at `tests/test_shipped_text.py:68`.
