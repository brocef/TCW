# Plan — Migration guide from 2.x to 3.0.0, and migrate the TCW repository first

This plan follows the spec as reviewed on 2026-10-02 and amended before
planning on 2026-10-15 (spec, "Pre-plan amendments", 1 to 20). Where it names a
file, line or function of 3.0, it was read on `epic/tcw-3.0` at `5b0dcf95`;
where it names 2.x code, at the tag `v2.8.1`; where it names TCW-75's work, on
TCW-75's spec, plan and work branch as they stood on 2026-10-15.

The work splits in two:

- **Part A** can run now, while TCW-75 is still being implemented. It touches no
  file TCW-75's plan changes (checked task by task below).
- **Part B** needs TCW-75 complete and merged into the epic branch, and then
  the code freeze. It holds every task that touches a file TCW-75 also
  changes, the migration itself, and the end of the epic.

## Rules for this item (the owner's, for the TCW 3.0 epic)

- **Where the work happens.**
  - Part A, and Part B up to the freeze: a worktree
    `.worktrees/2026-10-01-tcw-76-migration-guide-from-2-x-to-3-0-0-and-migrate-the-tcw-repository-first`
    on branch `work/2026-10-01-tcw-76-migration-guide-from-2-x-to-3-0-0-and-migrate-the-tcw-repository-first`,
    made by hand with `git worktree add` from `epic/tcw-3.0` (the 3.0 CLI has no
    `--worktree`). Called "the work branch" below.
  - The migration (Tasks B4 to B19): a worktree `.worktrees/tcw-3-0-migration-run-<N>`
    on branch `migrate/tcw-3.0-run-<N>`, made from the freeze commit (Task B3).
    It is deliberately not a `work/` branch (spec amendment 20). An abandoned
    run's branch is kept (spec Design 8.5.3).
  - The board: `docs/work/` on `main`, driven with the released 2.8.1 `tcw`
    installed outside the checkout, until Task B3 merges `main` into the epic
    branch and freezes `main`'s board (spec amendment 1). This item's
    `plan.md`, `outcome.md` (the migration log, spec Design 1.8) and
    `capabilities.yaml` are committed on `main` until then, and on the
    migration branch after.
  - **Before Task A1** the item is started on `main` with 2.8.1
    (`source ~/.bashrc >/dev/null 2>&1; tcw work start <slug>`), which moves
    the folder to `active/` and the ticket to `In Progress`. This plan is
    committed first.
- **Which source runs.** Private virtual environments in this session's
  scratch folder, never a re-pointed shared install:
  - 3.0: `python -m venv --system-site-packages <scratch>/tcw76/venv`,
    `<scratch>/tcw76/venv/bin/pip install -e <worktree> --no-deps`,
    `<scratch>/tcw76/venv/bin/pip install --ignore-installed pytest`; pytest
    and `tcw` run with the worktree as the current folder and the venv's `bin`
    first on `PATH`. Re-pointed with `pip install -e <migration worktree>
    --no-deps` at Task B3.
  - 2.8.1, for building the rehearsal project (Task A6) and reading `main`'s
    board: `python -m venv <scratch>/tcw76/venv-28`,
    `<scratch>/tcw76/venv-28/bin/pip install tcw-cli==2.8.1`.
- **Do not run the full pytest suite per task.** Each task runs the test files
  it names, every file under `tests/` that reads a file the task changed
  (`grep -rl '<file name>' tests`), and the standing guard files, all present
  on the epic branch: `tests/test_cli_contract.py`,
  `tests/test_cli_help_standard.py`, `tests/test_static_guards.py`,
  `tests/test_cli_handler.py`, `tests/test_tree_store_raises.py`,
  `tests/test_no_node.py`, `tests/test_ledger_3_0.py`,
  `tests/test_documented_cli_surface.py`, `tests/test_doc_allowance.py` and
  `tests/test_shipped_text.py` (the last two until Task B17 deletes or edits
  them). `pytest --collect-only -q` stays clean after every task. For this
  last child, the full suite (criterion 21) runs **once**, with bare `pytest`,
  in Task B19.
- **New 3.0 tests only.** Write the tests the spec calls for. A 2.x test that
  breaks because 2.x behavior is gone is deleted or skipped, not ported, and
  listed in the log.
- **Every new guard is mutation-checked**: break what it claims to observe,
  confirm it goes red for the stated reason, restore. Each task names its
  mutation; Task B19 records them all.
- **One commit per task** (per migration step in B4 to B15), with no co-author
  or session lines in the message.
- **No `tcw` from the epic's code against this repository** until migration
  step 3's scratch check and step 11. Every `tcw` command here stops on the 2.x
  `tcw-config.yaml` until then. A task that needs a working 3.0 `tcw` builds a
  fixture project in a scratch folder, with `HOME` and `XDG_CONFIG_HOME`
  pointed at scratch folders and `TCW_NO_PERSONAL_CONFIG=1`.
- **Jira.** Reads (REST `GET`, and JQL search) are allowed, with
  `source ~/.bashrc >/dev/null 2>&1;` first for `TCW_JIRA_EMAIL` and
  `TCW_JIRA_API_KEY`. No Jira write, and no GitHub post, is made without its
  exact text approved first: every comment the migration posts is in the
  consolidated plan the owner approves at step 1, and the owner makes every
  workflow, status and field change by hand (spec Design 2 step 2, 6.2).
- **The guide is followed as written.** Where it is wrong or unclear, the guide
  is fixed first on the migration branch, the amendment is logged, and the step
  is redone from the fixed text (spec Design 5.1). A defect in 3.0 code
  abandons the run (spec Design 8.5.3).
- **Approval is a bounded adversarial review**, standing in for the owner at
  this item's review stage: one review round, one fix round, one confirming
  round; findings sorted into "belongs to this change" and "needs a separate
  change"; the reviewer ends with DONE or NOT DONE. A confirming round still
  NOT DONE stops and goes to the owner. The owner's own end-of-epic review is
  this item's qa stage (Task B22).

## Blockers

- `blocked_by`: TCW-75 (`state.yaml`). It blocks Part B only. Part A needs
  nothing TCW-75 has not already settled in its plan: the git example's script
  path (`docs/guide/examples/commit-item-after-move.sh`), the README index row
  for the guide, and `PENDING_TARGETS`.
- **No version may be cut** between now and Task B23.
- **The owner's questions** (spec, Notes, items 7 to 9). The plan proceeds on
  the recommended answers to 7 (the deleted children stay deleted) and 9 (this
  item rewords the three capability descriptions). Item 8 (`v2.8.2` and the Pi
  change) must be answered before Task B3.

## Before the first task: what the branch already has

- The 3.0 command surface (walked from `tcw.cli.build_parser()`): top level
  `init`, `provision`, `validate [--remote]`, `serve`, `projects list`,
  `config show [--origin]`; `taxonomy` and `capabilities` with `list`, `add`,
  `show`, `path`, `rm`, `search`, `extends add|rm`, plus `capabilities set`,
  `reset`, `drift`; `work` with `new`, `list` (`--stage --tag --parent
  --assignee --mine --all --json`), `show`, `path` (`--next --handoff`),
  `edit`, `advance` (`--to --force --reason --dry-run`), `discard`,
  `comment`, `rename`, `stage prompt`, `procedure`, `lifecycle`, `docs`,
  `tags list|add|rm`, `tickets list|adopt`.
- The 3.0 layout: stages `inbox request spec plan implement review qa
  completed discarded postmortem` (`tcw/work/model.py:304-316`); document
  stages hold `<stage>/<stage>.md`, rounds stages `<stage>/round-N.md` with
  `verdict:` and `judges:` front matter (`tcw/work/layout.py`); filesystem
  `item.yaml` keys `title stage priority effort complexity tags assignee parent
  blocked-by` (`tcw/work/fs_backend.py:53-54`), folders `<date>-<words>`; Jira
  `item.yaml` is `ticket: <site>/browse/<KEY>` alone, folders `<KEY>-<words>`,
  `request` and `qa` kept in Jira (`tcw/work/jira/backend.py:59`).
- Configuration: `work` keys `path repository backend tags documentation
  procedures stages hooks jira`, the six removed keys each an error naming the
  guide (`tcw/work/config.py:40-58`, `:480-483`); `work.jira` keys `site
  project credentials fields priorities issue-type inbox-query timeout`
  (`tcw/work/jira/config.py:31`); `inherit: true` only in chain lists, one per
  list, and `builtin` in a file an error naming the guide (`tcw/config.py:295-311`).
- Hook variables `TCW_SLUG` (full slug), `TCW_STAGE`, `TCW_FROM_STAGE`,
  `TCW_ITEM_PATH`, `TCW_PROJECT_ROOT`, `TCW_FORCED=1`, `TCW_REASON`
  (`tcw/work/advance.py:164-179`), and `TCW_CONFIG_DIR`
  (`tcw/work/hooks.py:74`); `generate` adds the four `TCW_HOOK_*` and reads
  `{"schema", "item", "request", "hook"}` on stdin (`tcw/work/resolve.py:295-316`).
- `tests/doc_allowance.py` (five lists), its guard `tests/test_doc_allowance.py`,
  and the three code tests that read `REMOVED_COMMANDS`
  (`tests/work/test_removed_commands.py`, `tests/work/test_no_2x_names.py`,
  `tests/work/test_cli_config.py`).
- `tests/test_repo_lifecycle.py` and `tests/test_lifecycle_baseline.py` are
  gone (TCW-70). `tests/work/projects.py` has `make_project`, `write_item`,
  `commit_all` and `git` for fixture projects.
- `scripts/require_artifact.py` is still the 2.x script (`tcw work show
  --json`, `TCW_NODE_ROOT` in its docstring at `:12`).
- The sibling specs are no longer on `main`'s board: 2.x retention deleted
  them. Each is read with `git show <location>:docs/work/completed/<slug>/spec.md`,
  the `location` being its `graveyard.yaml` entry: TCW-69 `0e4d4061`, TCW-70
  `3207f310`, TCW-71 `6599dd20`, TCW-73 `e400dcfd`, TCW-72 `a066ae20`, TCW-74
  `64a2eb94`, TCW-77 `0a23906f`.

## Choices this plan makes

1. **The guide's own test**, `tests/test_migration_guide.py`, checks what can be
   checked mechanically, by section:
   - steps are the headings `### Step 0: …` to `### Step 11: …`, in order;
     every step section holds one paragraph starting `**Check:**`; every check
     but step 2's holds a backticked or fenced shell command and the words
     "prints" or "exits" with the expected output; step 2's names step 3
     (criterion 2);
   - `**Stop and ask**` appears in step 1 and step 2 only, and the rules
     section states the general "a check that fails after one retry" stop
     (criterion 3);
   - a constant `TWO_X_NAMES`, written out by hand, holds every name criterion
     4 lists, each group with a comment citing its `v2.8.1` file and line
     (`TRACKER_KEYS` and the rest no longer exist on the epic branch, so they
     cannot be imported); each name matches `^\| [^|]*<name>` in the guide
     (criterion 4);
   - the hook-variable rows of criterion 5, the `artifacts` row's `not_tags`
     rule and this repository's `spec` templates of criterion 6, and the
     `judges` values of criterion 8, by row text;
   - the "2.x behavior with no key" section names automatic commits,
     publishing, retention and ignored discarded folders (criterion 7);
   - no `` !` ``, and no backticked span that is a bare slash command
     (`^/[a-z][a-z0-9-]*(:[a-z0-9-]+)?$`) (criterion 9);
   - **every `tcw` invocation outside a table's first column parses on the 3.0
     CLI**, using `_invocations` and `_check` from
     `tests/test_documented_cli_surface.py` (the guide is otherwise exempt
     there, `ARCHIVAL`). A 2.x command named in prose outside a first column
     goes in a constant `TWO_X_SPANS` with its reason, the way TCW-74's
     allowance lists are written. This is criterion 10's automatic part; the
     `--help` run stays by hand (Task A6).
   From Task B1, it also runs TCW-75's link check on the guide.
2. **The code tests' own list.** `tests/work/removed_2x.py` holds
   `REMOVED_2X_COMMANDS`, the 21 entries `REMOVED_COMMANDS` holds at
   `5b0dcf95`, verbatim, with a comment saying it is permanent: it lists the
   2.x commands that must stay gone, which is not what the allowance is for.
   TCW-75's Task 14 may shrink `REMOVED_COMMANDS` meanwhile; that no longer
   weakens these tests.
3. **`require_artifact.py`** runs `tcw work path "$TCW_SLUG" <stage>`, reads
   the one path it prints, and fails unless the file exists and holds
   something other than white space. It keeps failing closed (exit 1) when
   `TCW_SLUG` is unset, `tcw` cannot be run, or `tcw` exits non-zero; usage
   errors stay exit 2. The docstring keeps the litmus-test reason, names
   `tcw work path`, and names neither `TCW_NODE_ROOT` nor `--json`.
4. **Its test** binds the script in a fixture project's `plan.pre` as
   `command: <sys.executable> <absolute script path> spec`, puts
   `Path(sys.executable).parent` first on `PATH` so the hook's `tcw` is the one
   under test (the venv locally, the installed package in CI), and moves an
   item from `spec` to `plan` through `tcw.cli.main` in-process. Unset
   `TCW_SLUG` and an unknown slug are run directly with `subprocess`.
5. **The migration log** is this item's 2.x `outcome.md` (on `main` until
   Task B3, then on the migration branch) until migration step 7 moves it to
   `implement/round-1.md`. Part A writes into it the rehearsal record (A6),
   criterion 10's `--help` run (A6) and the Jira checklist (A7). Each run
   starts under a heading `## Run <N>`.
6. **TCW's 3.0 configuration** is written at migration step 3 from the spec's
   Design 6, in the shape of TCW-75's example: each stage's `prompt` list is
   the pull `blob`, then `inherit: true`, then this repository's files; `post`
   is `command: sh docs/guide/examples/commit-item-after-move.sh` on request,
   spec, plan, implement, review, qa, completed and discarded; `postmortem`
   gets the pull prompt only. Anchors are used only where lists are equal.
   The step-3 scratch folder gets the configuration, every bound file at its
   relative path, empty `docs/work`, `docs/taxonomy` and `docs/capabilities`
   folders, and `git init`, so a missing repository is not one of its
   findings.
7. **Freeze.** "Code frozen" (spec Design 8.5.1) starts at Task B3's merge of
   `main` into the epic branch. The freeze commit is the epic-branch commit
   after that merge, written into the log at step 0. Criterion 23 compares it
   with the commit that merges the migration branch back.

## Part A — can run before TCW-75 completes

Every Part A task runs on the work branch, except where it names `main`.
TCW-75's plan and its branch change `AGENTS.md`, `README.md`, `docs/guide/**`
(including `examples/`), `docs/lifecycle/{abstraction,implementation,harness}.md`,
`docs/work-inbox-template.md`, `skills/configure/**`, `evals/coverage.py`,
`docs/capabilities/skills/configure/description.md`,
`docs/taxonomy/configure-skill/**`, `docs/{changelogs,release-notes}/upcoming/`
(its READMEs and its own entries), and the tests
`test_configuration_text_home.py`, `test_shipped_text.py`,
`test_docs_describe_3_0.py`, `test_git_example.py`, `test_cli_guide.py`,
`test_documented_cli_surface.py`, `test_doc_allowance.py`,
`test_upcoming_entries.py`, `test_check_versions.py`, and
`tests/doc_allowance.py`. Each task below says why it shares none of them.

### Task A1: The code tests keep their own list of removed 2.x commands (Design 7; criterion 28, first part)

- **Creates** `tests/work/removed_2x.py` (choice 2).
- **Modifies** `tests/work/test_removed_commands.py`,
  `tests/work/test_no_2x_names.py` and `tests/work/test_cli_config.py`: import
  `REMOVED_2X_COMMANDS` from it in place of `tests.doc_allowance.REMOVED_COMMANDS`.
- **Shared with TCW-75?** No: TCW-75 changes `tests/doc_allowance.py` and
  `tests/test_doc_allowance.py`, not these.
- **Proves:** the three test files; `tests/test_doc_allowance.py`; standing
  files. **Mutation:** add `"tcw work list"` to the tuple, and
  `test_removed_commands.py` fails for that entry.

### Task A2: `require_artifact.py` asks `tcw work path` (Design 7; criterion 20)

- **Modifies** `scripts/require_artifact.py` (choice 3).
- **Creates** `tests/test_require_artifact.py` (choice 4), with the cases of
  criterion 20: no `spec/spec.md` → the move is refused (exit 3) and the item
  stays at `spec`; an empty file and a white-space-only file → refused; a file
  with text → exit 0 and the item at `plan`, the hook having seen
  `TCW_SLUG=p/<folder>`; `TCW_SLUG` unset → exit 1; an unknown slug → exit 1;
  the script's text contains neither `--json` nor `TCW_NODE_ROOT`.
- **Shared with TCW-75?** No.
- **Proves:** `tests/test_require_artifact.py`; standing files.
  **Mutation:** drop the emptiness test from the script, and the empty-file
  case fails.

### Task A3: The spec templates, the review prompt and the create-work addition (Design 6.3, 7)

- **Modifies** `docs/lifecycle/templates/spec.md` and `spec-bug.md`: a new
  first line, `_The outline for this item's spec: the file
  `tcw work path <slug> spec` names (`spec/spec.md`)._`, and nothing else.
- **Creates** `docs/lifecycle/review.md`: the binding comment in the house
  form (`<!-- Bound to the `review` stage of `tcw work`; see
  `tcw-config.yaml`. Read as a continuation of TCW's built-in stage
  instructions, not on its own. -->`), then: before writing an accepted
  verdict, run the suite as CI does (bare `pytest`) and invoke the
  `documentation-sync` skill over the item's whole difference, and say in the
  round that both were done; and that an originating GitHub issue is answered
  and closed only after publication, which the qa round records (spec Design
  6.3).
- **Modifies** `docs/procedures/create-work.md` to match TCW-74's
  `tcw/work/procedures/create-work.md`: the `## Why` section goes in step 4's
  body; "step 1's raw inbox entry" becomes "step 1's inbox item, in filesystem
  mode" (in Jira mode step 1 creates nothing); an addition under step 3 in
  Jira mode goes in the comment that step posts, under the same dated first
  line. Step numbers 1, 3 and 4 are the procedure's own.
- **Shared with TCW-75?** No: TCW-75 owns only
  `docs/lifecycle/{abstraction,implementation,harness}.md`, and its spec gives
  `docs/lifecycle/templates/` and `docs/procedures/` to this item (TCW-75 spec
  Design 1.2).
- **Proves:** standing files. **By hand, in a scratch fixture** binding these
  files as Design 6 does: `tcw work stage prompt spec <slug>` prints the
  built-in prompt, then `abstraction.md`, `harness.md` and the template whose
  `when:` matches (a `bug`-tagged item gets only `spec-bug.md`);
  `tcw work stage prompt review <slug>` ends with `review.md`; `tcw work
  procedure create-work` ends with `create-work.md`. Output recorded in the log.

### Task A4: The guide, part 1: who it is for, and every mapping (Design 1.1-1.2, 3, 4; criteria 4, 5, 6, 8)

- **Creates** `docs/migration-guide-2.8-to-3.0.0.md` with:
  - the opening: what changes, who the guide is for (an agent working with a
    user, under Claude Code or Codex, with any Jira access), projects older
    than 2.8 upgrading first with the earlier guides;
  - the mapping tables of Design 3, in the order 3.1 to 3.9, each first column
    the 2.x name, each second column the 3.0 form, or "removed" and what
    replaces it, every name and key spelled as the epic's code spells it.
    Includes the amended rows: `renames.yaml`, list-form `capabilities.yaml`,
    other item-root files, `TCW_CONFIG_DIR`, `TCW_FORCED=1`, the
    `{{tcw:request}}…{{/tcw:request}}` pair, `judges` 1 or 0;
  - TCW-73's old-to-new command table, copied from its spec (Design 2 there;
    `git show e400dcfd:…/spec.md`), and the removed procedures with where each
    went (`tcw/work/config.py:61-73`);
  - Design 4's Jira binding and reconciling rules.
  Steps are a heading with "written in Task A5" until then.
- **Creates** `tests/test_migration_guide.py` with criteria 4, 5, 6 and 8's
  parts of choice 1.
- **Shared with TCW-75?** No: both files are new. The guide links to TCW-75's
  documents (`docs/guide/configuration.md`'s git example section,
  `docs/guide/jira.md`, `skills/configure/references/*.md`) by the headings on
  TCW-75's branch; Task B1 checks they resolve.
- **Proves:** `tests/test_migration_guide.py`; `tests/test_documented_cli_surface.py`
  (the guide stays exempt); standing files. **Mutations:** delete the
  `renames.yaml` row → criterion 4 fails naming it; swap `TCW_FROM_STAGE` and
  `TCW_STAGE` in the `TCW_STATUS` rows → criterion 5 fails.

### Task A5: The guide, part 2: rules, steps and REST forms (Design 1.2-1.8, 2; criteria 1, 2, 3, 7, 9, 10)

- **Modifies** `docs/migration-guide-2.8-to-3.0.0.md`:
  - prerequisites and rules (Design 1.2, as amended: no 2.x item worktree);
  - the section on 2.x behavior that had no key (Problem 2.3, 2.4);
  - steps 0 to 11 (Design 2), each with what to do, its **Check** (a
    read-only shell command and its expected output, paths relative to the
    configured work path) and, at steps 1 and 2, **Stop and ask**; the
    idempotence rules of Design 1.5 and 1.8 in every step that writes to Jira;
  - a REST section: the `curl` form of every Jira read and write the steps
    use (JQL search, create, transition list and transition, field edit,
    comment list and comment, issue link), with the credentials by variable
    name, and the web UI as the equivalent.
- **Modifies** `tests/test_migration_guide.py`: criteria 1, 2, 3, 7, 9 and 10's
  parts of choice 1.
- **Shared with TCW-75?** No.
- **Proves:** `tests/test_migration_guide.py`; standing files. **Mutations:**
  remove step 4's `**Check:**` → criterion 2 fails; add `**Stop and ask**` to
  step 5 → criterion 3 fails; add `` !`tcw validate` `` → criterion 9 fails;
  add `tcw work start x` to a step → the parse check fails.

### Task A6: The filesystem rehearsal (Design 5.2, 5.3; criteria 10, 25)

- **Builds** in `<scratch>/tcw76/rehearsal/` with `venv-28` (2.8.1), `HOME`
  and `XDG_CONFIG_HOME` in scratch: a 2.8 project, git-initialized, holding
  at least one of each: an item in `active/`, in `review/` (with `outcome.md`),
  in `discarded/` (tracked) and one in an ignored `discarded/` folder; a
  nested child placed by hand inside its parent's folder with no `parent:`; an
  item with `initiative:`; one with `rework.md` and `refined-outcome.md`; one
  with `refined-outcome.md` and no `outcome.md` (`judges: 0`); one with
  `post-mortem.md`; a `connected-projects` entry to a second scratch project;
  transition bindings on `start`, `submit`, `rework`, `complete`, `discard`
  and `auto-delete`, a `postmortem` `pre`, `timeout` and `output-cap`; an
  unconditional `artifacts` template after a `tags`-conditioned one and a
  `not_tags` one; a legacy bare-list stage with a `command` entry; a hook script
  comparing `TCW_STATUS` with `backlog` and testing `TCW_TRANSITION`; a
  `{{tcw:body}}…{{/tcw:body}}` pair in a prompt file; a `renames.yaml`; a
  list-form `capabilities.yaml`; an inbox entry; and a `blocked/` folder holding
  one item, placed by hand.
- **Follows** the guide, filesystem mode, step by step, with the 3.0 CLI from
  `venv` only at step 11, ending with `tcw validate` exit 0.
- **Modifies** the guide and its test wherever the rehearsal shows the guide
  wrong or unclear (one commit on the work branch).
- **Runs** `tcw <command> --help` for every `tcw` command the guide names, on
  the 3.0 CLI (criterion 10).
- **Writes** in `outcome.md` on `main` (one commit): under `## Rehearsal`, the
  2.8.1 commands and hand placements that built the project, each step's check
  output, every guide amendment, and the final `tcw validate`; under
  `## Criterion 10`, each command and its exit code. Nothing of the rehearsal
  project is committed.
- **Shared with TCW-75?** No: the guide, its test and this item's folder.

### Task A7: The Jira checklist for the owner (Design 6.2; criterion 24, first part)

- **Reads** with REST `GET` only: the `TCW` project's workflow scheme and every
  workflow in it (on 2026-10-02 only `TCW work`), its statuses and
  transitions with their screens; the issue types and their screen schemes;
  and the custom fields, looking for `TCW Project`, `TCW Item`, `Effort` and
  `Complexity`.
- **Writes** in `outcome.md` on `main` (one commit), under
  `## Jira checklist (for the owner)`, one line per change with how to confirm
  it: the statuses `Specifying`, `Planning`, `In QA`; one global transition
  with no screen fields into each of `Triage`, `To Do`, `Specifying`,
  `Planning`, `In Progress`, `In Review`, `In QA`, `Done`, `Won't Do`; every
  directed transition into a mapped status removed, listed by name from this
  read (on 2026-10-02: `Accept`, `Start`, `Submit`, `Complete`, `Rework`,
  `Cancel`, `Stop`, `Reopen`), keeping `Create`; each missing field created
  with the type TCW-71 defines (`git show 6599dd20:…/spec.md`) and added to
  the project's screens; the same changes in any other workflow an issue type
  now uses. It opens with: **do not apply any line until told the freeze has
  begun** (migration step 2), because the released 2.8.1 CLI that still moves
  `main`'s board names `Start` and finds routes by the old transitions.
- **Shared with TCW-75?** No: this item's folder on `main`.

### Task A8: A bounded review of the guide before it touches Jira

- An `adversarial-spec-reviewer` round over the guide, its test and the
  rehearsal record, given the spec and its amendments; bounded as in the
  rules. Accepted findings fixed in one commit on the work branch (the guide
  and its test); the result recorded in `outcome.md` on `main`.
- **Shared with TCW-75?** No.

## Part B — needs TCW-75 complete and the code freeze

### Task B1: Take in TCW-75 (Design 7; criterion 28, link part)

- After TCW-75 is completed and the epic branch fast-forwarded to it:
  `git merge epic/tcw-3.0` into the work branch.
- **Modifies** `tests/test_docs_describe_3_0.py`: `PENDING_TARGETS`, its use in
  the link check, and `test_the_link_check_lets_the_pending_migration_guide_through`
  are deleted (spec amendment 18).
- **Modifies** `tests/test_migration_guide.py`: a test running TCW-75's
  `link_problems` over the guide; and the guide, for any link or anchor it
  reports.
- **Proves:** `tests/test_docs_describe_3_0.py`, `tests/test_migration_guide.py`,
  standing files. **Mutation:** a link to `docs/guide/jira.md#no-such-heading`
  in the guide → the new test fails.

### Task B2: The capability descriptions that still name removed things (Design 7; spec amendment 6)

- **Modifies** `docs/capabilities/work/configure-the-work-store-location/description.md`
  (`tcw work init` → `tcw init --work-path`),
  `docs/capabilities/cli/validate-a-project/description.md` (no
  `tcw taxonomy check` or `tcw capabilities check`; the sentence says
  `tcw validate` checks the ledgers),
  `docs/capabilities/work/configure-the-work-lifecycle/description.md` (the
  removed `work.*` keys replaced by `work.stages` and `work.hooks`), each
  keeping what it promises; and `tests/doc_allowance.py`, removing every entry
  that only these records named, in the same commit, since TCW-75's
  "still named somewhere" check fails otherwise.
- **Writes** this item's `capabilities.yaml` on `main` (separate commit):
  `changed:` the three paths.
- **Proves:** `tests/test_doc_allowance.py`, `tests/test_ledger_3_0.py`,
  `tests/test_documented_cli_surface.py`, standing files; and the branch's
  `tcw validate` in a scratch fixture holding copies of the three records and
  the records they link to, recorded in the log.

### Task B3: Merge and freeze (Design 8.5.1-8.5.2; spec amendment 13)

- With the owner's answer to Notes item 8 applied (if `v2.8.2` was published,
  `feat/pi-package-support` is merged into `main` first).
- The Pi item on `main` is completed with 2.8.1, or the owner says it waits.
- `epic/tcw-3.0` is fast-forwarded to the work branch; the work worktree and
  branch are removed.
- `git merge main` into `epic/tcw-3.0`. Conflicts are resolved by keeping the
  epic's text and carrying the Pi facts into it: Pi installation in TCW-75's
  README install section; the Pi lines of `docs/lifecycle/harness.md` into
  TCW-75's version; `skills/README.md`, `skills/setup/SKILL.md` and
  `references/install.md` on TCW-74's text; `skills/work/references/procedures/delegation.md`
  stays deleted; `package.json` keeps its `pi` block; the two
  `docs/capabilities/plugin/*/description.md` take the Pi sentence. The board
  arrives unchanged.
- **The freeze begins**: the epic tip is the freeze commit; the owner is told
  that `main`'s board is frozen and that the Jira checklist may now be applied
  when step 2 asks.
- Migration worktree and branch `migrate/tcw-3.0-run-1` made from it; `venv`
  re-pointed.
- **Proves:** every test file that reads a file the merge changed (at least
  `test_docs_describe_3_0.py`, `test_shipped_text.py`,
  `test_dynamic_skill_marker.py`, `test_documented_cli_surface.py`,
  `test_skill_path_pointers.py`, `test_plugin_manifests.py`), standing files.

### Tasks B4 to B15: The migration, steps 0 to 11 (Design 2, 4, 6, 7; criteria 11-18, 24, 27, 30, 31)

One task and one commit per step, on the migration branch, following the guide
as written. Each step's check output goes in the log. TCW's particulars:

- **B4, step 0.** Prerequisites; `git status --ignored -- docs/work` lists the
  ignored discarded folders (33 on this machine on 2026-10-15); the log starts
  under `## Run 1` with the start date, the freeze commit, and each finished
  slice with its `graveyard.yaml` `location` and the `git cat-file -e` result
  (criterion 27).
- **B5, step 1 — Stop and ask.** The consolidated plan: Jira mode; every
  optional stage enabled; statuses (Design 6.2); each item's stage and
  converted fields; every disk–ticket difference, including TCW-9's
  `sync: pending`; the ~20 tickets to create and their exact comments;
  request placement per ticket; the prune list as amended (Design 2 step 1);
  the ignored discarded folders (none kept unless named); the six inbox
  entries; `<hook files>`; step 9's skipped folder (this item's); the config,
  hook, record and project-file rewrites. Approval recorded verbatim under
  `## Approved plan`.
- **B6, step 2 — Stop and ask.** The workflow is read again and the checklist
  of Task A7 updated if it changed; the owner applies it and confirms each
  line, recorded before step 3 runs.
- **B7, step 3.** `tcw-config.yaml` rewritten to spec Design 6 (choice 6),
  including the documentation entries of Design 6.4; the scratch
  `tcw validate --remote` and its findings.
- **B8 to B12, steps 4 to 8.** Including `renames.yaml`'s two pairs into the
  log at step 4; criterion 31's rerun of step 6, logged as all skips; this
  item's `outcome.md` becoming `implement/round-1.md` at step 7.
- **B13, step 9.** Live references; this item's folder is skipped.
- **B14, step 10.** The project's own files: `AGENTS.md`'s "Work Planning and
  Implementation" and Versioning (spec Design 7 row; `notes-from-tcw-74.md`
  items 1 and 3: the eval and worktree sections untouched), `.gitignore`, the
  13 `Planning doc:` lines; `require_artifact.py`, the templates and
  `create-work.md` already done in Part A, so the step's checks find them
  clean.
- **B15, step 11.** `tcw validate` and `tcw validate --remote` from `venv`
  in the migration worktree, each finding fixed or listed (criterion 15);
  `tcw work list --all --json` against the approved stages (criterion 14).

A step whose check fails after one retry stops the run and goes to the owner;
a defect in 3.0 code abandons the run (Design 8.5.3) and the next run begins
again at B3's last bullet.

### Task B16: `tests/test_repo_lifecycle.py` for 3.0 (Design 7; criteria 16, 21)

- **Creates** `tests/test_repo_lifecycle.py`: the real `tcw-config.yaml` loads
  through `tcw.config.load_config` with `TCW_NO_PERSONAL_CONFIG=1` and no
  problems, and its `work.jira` through `tcw.work.jira.config` with none;
  every bound `file:` exists and is not empty; every `command:` names a file
  that exists; `plan` binds no template; both templates carry the seven
  headings of `tcw/work/prompts/spec.md:21-23`; the documentation entries and
  triggers are those of Design 6.4 (`Jira-Change` present, no
  `Tracker-Change`, `upcoming/<folder>.md`, no `dod.yaml`).
- **Proves:** it; `tests/test_documentation_sync_wiring.py`; standing files.
  **Mutations:** rename a template heading → fails; restore
  `Tracker-Change` → fails.

### Task B17: The allowance is emptied and deleted (Design 7; criterion 28)

- With `AGENTS.md` rewritten (B14), every list is empty.
- **Deletes** `tests/doc_allowance.py` and `tests/test_doc_allowance.py`.
- **Modifies** `tests/test_documented_cli_surface.py`,
  `tests/test_shipped_text.py` and `tests/test_docs_describe_3_0.py`: the
  imports and every allowance branch and allowance-only test removed.
- **Modifies** `tests/test_migration_guide.py`: a test that no file under
  `tests/` names `doc_allowance` and the module does not exist.
- **Proves:** the four edited test files, the three code tests of Task A1,
  standing files. **Mutation:** recreate `tests/doc_allowance.py` → the new
  test fails.

### Task B18: This item's release notes and changelog (Design 7; criterion 29)

- **Creates** `docs/release-notes/upcoming/TCW-76-<title words>.md` and the
  same name under `docs/changelogs/upcoming/`, the folder name step 6 gave
  this item: release notes under `## Upgrading` (how to move a 2.8 project, a
  link to the guide); changelog under `## Added` (the guide,
  `docs/lifecycle/review.md`, the new tests) and `## Changed` (TCW's own
  configuration and board on 3.0, `require_artifact.py`, the removed
  allowance). No text before the first `##`.
- **Proves:** `tests/test_upcoming_entries.py`, `tests/test_cut_version.py`.

### Task B19: Mutation record, full suite, drift, and the evidence

- Every mutation named above re-run once, each result in the log.
- `pytest --collect-only -q` clean; **the full suite once, with bare `pytest`,
  from the migration worktree with `venv` first on `PATH`** (criterion 21).
- `tcw capabilities drift`; each line in the log with its cause (expected:
  `work/customize-the-definition-of-done`, declared by the completed
  `stop-offering-…` item and removed by a deleted child; criterion 22).
- Criterion 30 checked by reading each pruned ticket once; criterion 24's
  workflow `GET`.
- The `documentation-sync` skill evaluated over the item's whole difference.
- The log gets one line of evidence per criterion.

### Task B20: Merge the migration and enter review (Design 8.7.1; criteria 23, 26)

- The migration branch merges into `epic/tcw-3.0`;
  `git diff --stat <freeze commit>..<that merge> -- tcw skills agents web`
  prints nothing (criterion 23).
- From a checkout of the epic branch, with `venv`:
  `tcw work advance tcw/TCW-76-<words>` to review exits 0 and its `post` hook
  commits or reports nothing to commit (criterion 26). This is TCW-76's first
  3.0 move.

### Task B21: The review stage (spec Design 8.7.2, amendment 14)

- Bounded adversarial review, split into the guide and its tests (A4, A5, A8,
  B1), the migrated board and configuration (B4-B16), and the test changes
  (A1, A2, B17), then one combined pass over the whole difference since
  `5b0dcf95`. Accepted findings are fixed in the item (a rejection moves it
  back to implement, with a new implement round).
- `review/round-<n>.md` written with `verdict: accepted` and `judges:` the
  latest implement round; `tcw work advance` to qa.

### Task B22: QA by the owner, then complete TCW-76 and TCW-68 (Design 8.7.2)

- **Stop and ask:** qa is the owner's own end-of-epic review. When the owner
  accepts, `tcw work advance tcw/TCW-76-<words> --to completed --reason
  "<the owner's acceptance>"`; the completion gate reads the review verdict
  and `completed.pre` runs `tcw validate`.
- `tcw work advance tcw/TCW-68-<words> --to completed --force --reason
  "all children complete"`.

### Task B23: Main, the cut, the push, the issues (Design 8.7.3-8.7.6)

- `epic/tcw-3.0` merges to `main`; the local suite and `gh run list` for
  `main`'s CI both green.
- `python scripts/cut_version.py 3.0.0`; the tag pushed with `main`, which
  publishes the release (no further confirmation, per the owner's standing
  rule, once verification has passed).
- Only then: any originating GitHub issue answered and closed, each with text
  the owner has approved.

## Documentation Sync

The project's entries as the plan stage printed them (2.x wording), and what
answers each:

| Entry | Trigger | Answered by |
| --- | --- | --- |
| `README.md` | Public-API | TCW-75 adds the guide's index row; this item only resolves the Pi merge in Task B3 and checks the row's link in B1 |
| `docs/guide/jira.md` | Tracker-Change (becomes Jira-Change at B7) | Does not fire: no Jira behavior or key changes. TCW-75's |
| `docs/guide/<topic>.md` | Guide-Topic-Change | Does not fire: the migration guide is not under `docs/guide/` |
| `docs/release-notes/upcoming/<folder>.md` | Public-API | Task B18 |
| `docs/changelogs/upcoming/<folder>.md` | Any-Code-Change | Task B18 |
| `skills/<component>/SKILL.md` | Skill-Driven-Component | Does not fire: no skill changes, beyond resolving the Pi merge (B3) |
| `skills/configure/references/<document>.md` | Configuration-Key-Change | Does not fire: no key changes |

The entries themselves are rewritten at Task B7 (spec Design 6.4). The
`documentation-sync` skill is invoked over the whole difference in Task B19.

## Verification

What the suite cannot check, and how it is checked:

1. **The guide reads as an agent would follow it** (criteria 1-3, 7, 9 beyond
   the test): the rehearsal (A6), the review (A8), and the real run (B4-B15),
   where any wrong or unclear text is fixed before the step is redone.
2. **Criterion 10:** every command's `--help` run by hand (A6).
3. **Jira:** criterion 24's checklist confirmation and the post-migration
   workflow `GET`; criterion 30 by reading each ticket; criterion 31 by the
   rerun and a JQL `updated >=` search. All recorded in the log.
4. **Criterion 15** (`validate --remote`) needs the live site; run in B15.
5. **Criterion 21's full suite** runs once, in B19, as CI runs it.
6. **Harness:** the guide is plain Markdown using only shell, `curl` and
   `tcw`; the test forbids `` !` `` and slash commands.
7. **Review:** Tasks A8 and B21, bounded as in the rules.
8. **Board and ticket:** until B3 this item is moved on `main` with 2.8.1;
   after the migration commit, with the 3.0 CLI.

## Criterion-to-task table

| Criterion | Tasks |
| --- | --- |
| 1 Opening | A5 (test), A8 |
| 2 Steps and checks | A5 |
| 3 Stops | A5 |
| 4 Every 2.x name mapped | A4 |
| 5 Hook variables by meaning | A4 |
| 6 `artifacts` rule and status translation | A4 |
| 7 Behavior with no key | A5 |
| 8 Verdict rounds | A4, A6 |
| 9 No harness-only mechanism | A5 |
| 10 Every command exists | A5 (parse), A6 (`--help`) |
| 11-13 Folders, `item.yaml`, documents | B8-B12 |
| 14 `list --all --json` stages | B15 |
| 15 `validate`, `validate --remote` | B15, B19 |
| 16 Configuration | B7, B16 |
| 17 `Planning doc` | B14 |
| 18 `.gitignore` | B14 |
| 19 `AGENTS.md` and the link | B14 (and TCW-75 for the READMEs) |
| 20 `require_artifact.py` | A2 |
| 21 Repo test and full suite | B16, B19 |
| 22 Drift | B19 |
| 23 No code change after the freeze | B3, B20 |
| 24 The log and the checklist | A7, B4-B15, B19 |
| 25 Rehearsal | A6 |
| 26 First 3.0 move | B20 |
| 27 Sibling specs readable (amended) | B4 |
| 28 Allowance gone | A1, B1, B2, B17 |
| 29 Upcoming entries | B18 |
| 30 Prune list | B5, B10, B19 |
| 31 Step 6 rerun writes nothing | B10 |

Every task traces to a criterion: A1 to 28; A2 to 20; A3 to 16, 21 (bound
files exist; Design 6.3); A4 to 4-6, 8; A5 to 1-3, 7, 9, 10; A6 to 8, 10, 25;
A7 to 24; A8 to 1-10; B1 to 28; B2 to 28 (amendment 6); B3 to 23; B4-B15 to
11-18, 24, 27, 30, 31; B16 to 16, 21; B17 to 28; B18 to 29; B19 to 21, 22,
24, 30; B20 to 23, 26; B21 and B22 to the end of Design 8.7; B23 to Design
8.7.3-8.7.6.

## Notes

- **Abstraction litmus test.** This item adds no operation. The guide states
  every step for both backends, with Jira's form of each fact Jira owns, and
  `require_artifact.py` keeps asking TCW where a document lives (`tcw work
  path`) instead of composing a path.
- **For TCW-75, while it is still in progress** (sent to the orchestrator, not
  changed here): its Task 14 shrinks `REMOVED_COMMANDS`, which three code tests
  read as the list of commands that must stay gone, and an empty list would
  break `tests/work/test_no_2x_names.py`; Task A1 gives them their own list.
  Its `test_the_link_check_lets_the_pending_migration_guide_through` asserts
  the guide does not exist, so it goes when the guide lands (B1). `main`'s Pi
  change edits `README.md` and `docs/lifecycle/harness.md`, which TCW-75
  rewrites; carrying the Pi facts into its rewrite now would leave Task B3 a
  smaller merge.
