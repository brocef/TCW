# Plan — Migration guide from 2.x to 3.0.0, and migrate the TCW repository first

This plan follows the spec as reviewed on 2026-10-02 and amended before
planning on 2026-10-15 (spec, "Pre-plan amendments", 1 to 21; 21 is the
owner's addition of step 12, revisiting agent instructions and memories), and
after the plan review of 2026-10-15 (spec amendments 22 and 23). Where it names
a file, line or function of 3.0, it was read on `epic/tcw-3.0` at `e301bef5`,
which holds TCW-75 (nothing under `tcw/` changed between `5b0dcf95` and
`e301bef5`); where it names 2.x code, at the tag `v2.8.1`.

The work splits in two:

- **Part A** runs now, on a work branch made from `e301bef5`. TCW-75 is
  complete and already on that commit, so Part A waits for nothing.
- **Part B** needs the code freeze (Task B3), which waits for the blockers
  below. It holds the migration itself and the end of the epic.

## Rules for this item (the owner's, for the TCW 3.0 epic)

- **Where the work happens.**
  - Part A, and Part B up to the freeze: a worktree
    `.worktrees/2026-10-01-tcw-76-migration-guide-from-2-x-to-3-0-0-and-migrate-the-tcw-repository-first`
    on branch `work/2026-10-01-tcw-76-migration-guide-from-2-x-to-3-0-0-and-migrate-the-tcw-repository-first`,
    made by hand with `git worktree add` from `epic/tcw-3.0` at `e301bef5` (the
    3.0 CLI has no `--worktree`). Called "the work branch" below.
  - Every change to `epic/tcw-3.0` itself (B3's fast-forward and merge of
    `main`, B21's merge of the migration branch, B21 to B23's moves): a
    worktree `.worktrees/tcw-3-0-epic` with `epic/tcw-3.0` checked out, made
    at B3 with `git worktree add .worktrees/tcw-3-0-epic epic/tcw-3.0` and
    kept until B24. Called "the epic worktree" below. The primary checkout
    stays on `main`.
  - The migration (Tasks B4 to B20): a worktree `.worktrees/tcw-3-0-migration-run-<N>`
    on branch `migrate/tcw-3.0-run-<N>`, made from the freeze commit (Task B3).
    It is deliberately not a `work/` branch (spec amendment 20). An abandoned
    run's branch is kept (spec Design 8.5.3).
  - The board: `docs/work/` on `main`, driven with the released 2.8.x `tcw`
    (2.8.2 once published) installed outside the checkout, until Task B3 merges `main` into the epic
    branch and freezes `main`'s board (spec amendment 1). This item's
    `plan.md`, `outcome.md` (the migration log, spec Design 1.8) and
    `capabilities.yaml` are committed on `main` until then, and on the
    migration branch after.
  - **Before Task A1** the item is started on `main` with the released 2.8.x
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
    --no-deps` at Task B3, and with `pip install -e .worktrees/tcw-3-0-epic
    --no-deps` at Task B21.
  - 2.8.1, for building the rehearsal project (Task A7) and reading `main`'s
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
  `tests/test_shipped_text.py` (the last two until Task B18 deletes or edits
  them). `pytest --collect-only -q` stays clean after every task. For this
  last child, the full suite (criterion 21) runs **once**, with bare `pytest`,
  in Task B20.
- **New 3.0 tests only.** Write the tests the spec calls for. A 2.x test that
  breaks because 2.x behavior is gone is deleted or skipped, not ported, and
  listed in the log.
- **Every new guard is mutation-checked**: break what it claims to observe,
  confirm it goes red for the stated reason, restore. Each task names its
  mutation; Task B20 records them all.
- **One commit per task** (per migration step in B4 to B16), with no co-author
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
  this item's qa stage (Task B23).

## Blockers

- `blocked_by`: TCW-75 (`state.yaml`) is satisfied: TCW-75 completed on
  2026-10-15 (`560e312f`, deleted by retention in `b5b7756f`), and its work is
  on `e301bef5`, where the work branch starts.
- **Blocker of Task B3 (the freeze): the code follow-ups the reviews left.**
  These inbox entries on `main` name changes under `tcw/` (and, for two of
  them, `web/` or `skills/`), which the freeze forbids until the epic merges:
  - `docs/work/inbox/2026-10-13-tidy-what-tcw-71-s-reviews-left-for-the-jira-backend.md`
  - `docs/work/inbox/2026-10-13-tidy-what-tcw-72-s-reviews-left-for-personal-configuration.md`
  - `docs/work/inbox/2026-10-13-tidy-what-tcw-73-s-reviews-left-for-the-cli.md`
  - `docs/work/inbox/2026-10-15-tidy-what-tcw-74-and-tcw-77-s-reviews-left-elsewhere.md`
  - `docs/work/inbox/2026-10-15-tidy-what-tcw-75-s-reviews-left-in-code-text.md`

  They are accepted on `main` as one small work item of their own, whose
  changes under `tcw/`, `skills/`, `agents/` and `web/` are made on the epic
  branch and completed before B3 begins. What in them touches only `tests/`
  or documents may wait. Not in this list: `…-tidy-what-tcw-74-s-reviews-left-for-the-eval-harness.md`
  (only `evals/`, which the freeze does not cover) and
  `…-settle-the-jira-live-check-questions-that-need-a-second-account.md`
  (only `tests/work/jira/`).
- **No version may be cut** between now and Task B24.
- **The owner's questions** (spec, Notes, items 7 to 9) were settled on
  2026-10-15: the deleted children stay deleted; this item rewords the three
  capability descriptions (Task A10); 2.8.2 (Pi) is merged into `main`
  (`dc0aaa7a`, `74630308`) and published from the tag `v2.8.2`.

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
- `tests/doc_allowance.py` (five lists; after TCW-75, `REMOVED_COMMANDS` holds
  `tcw work stage gate`, `tcw work init`, `tcw taxonomy check` and
  `tcw capabilities check`, `REFUSED_KEYS` the six removed `work.*` keys, the
  other three are empty), its guard `tests/test_doc_allowance.py` (whose
  `test_an_entry_is_still_named_by_some_live_document` fails for an entry no
  live document names), and the three code tests that read `REMOVED_COMMANDS`
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
  `64a2eb94`, TCW-77 `0a23906f`, TCW-75 `560e312f`.
- TCW-75's `tests/test_docs_describe_3_0.py` holds `PENDING_TARGETS` (line 44),
  its use in the link check (line 227), and
  `test_the_link_check_lets_the_pending_migration_guide_through` (lines
  267-270), which asserts the guide does not exist. Its README index already
  links the guide (`test_the_documentation_index_links_the_guides_it_must`).

## Choices this plan makes

1. **The guide's own test**, `tests/test_migration_guide.py`, checks what can be
   checked mechanically, by section:
   - the guide's first two `##` sections are `## Before you start` (the
     prerequisites of spec Design 1.2: on 2.8.x, the 3.0 CLI installed, no
     uncommitted changes, no `work/` item worktree, a branch or tag marking the
     2.x state, every connected project present) and `## Rules` (in order,
     check, stop), each prerequisite named in the first, and both come before
     any mapping table (criterion 1);
   - steps are the headings `### Step 0: …` to `### Step 12: …`, in order;
     every step section holds one paragraph starting `**Check:**`; every check
     but step 2's holds a backticked or fenced shell command and the words
     "prints" or "exits" with the expected output; step 2's names step 3
     (criterion 2);
   - `**Stop and ask**` appears in steps 1, 2 and 12 only, and the rules
     section states the general "a check that fails after one retry" stop
     (criterion 3);
   - step 12's section names each place criterion 32 lists, the worktree rule
     (the primary checkout's untracked per-user files), and contains the words
     delete, rewrite and keep (criterion 32);
   - step 12's two searches (spec amendment 22): a fenced `grep -rlE`
     files-to-read command whose pattern holds `\btcw\b`, `NAMES` and
     `WORDS`, followed by the instruction to read each printed file in full;
     and a fenced `grep -rE` check command with `NAMES` alone, compared by
     `diff` with the log's expected block. The test reads `NAMES` and `WORDS`
     from the guide's fenced definitions, splits them on `|`, and requires
     every backticked span in a mapping table's first column to be covered:
     the span itself, or its last dotted part (`work.tracker.create.issue-types`
     by `issue-types`), is one of the alternatives. Spans that are kept
     unchanged in 3.0 (`TCW_ITEM_PATH`, `work.tags`, …) or whose pattern form
     differs (`{{tcw:body}}…{{/tcw:body}}` as `tcw:body`) are listed by hand in
     a constant `STEP_12_EXCEPTIONS`, each with its reason. The test also
     requires that `NAMES` holds no bare `tcw` and that every status-folder
     form in it is written with its trailing `/` and no leading one;
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
     `--help` run stays by hand (Task A7).
   From Task A4, it also runs TCW-75's `link_problems` on the guide.
2. **The code tests' own list.** `tests/work/removed_2x.py` holds
   `REMOVED_2X_COMMANDS`, the 21 entries `REMOVED_COMMANDS` held at
   `5b0dcf95`, verbatim (`git show 5b0dcf95:tests/doc_allowance.py`), with a
   comment saying it is permanent: it lists the 2.x commands that must stay
   gone, which is not what the allowance is for. TCW-75 has since shrunk
   `REMOVED_COMMANDS` to four entries, so until A1 the three code tests check
   only those four.
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
   `implement/round-1.md`. Part A writes into it the rehearsal record (A7),
   criterion 10's `--help` run (A7) and the Jira checklist (A8). Each run
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

## Part A — before the freeze

Every Part A task runs on the work branch, made from `e301bef5`, except where it
names `main`. TCW-75 is on that commit, so no Part A task waits for it, and
the tasks that used to wait (B1 and B2) are now A4 and A10. Task A1 comes
first, because A10 and B14 remove allowance entries the three code tests still
read; A2 to A10 may then run in the order given.

### Task A1: The code tests keep their own list of removed 2.x commands (Design 7; criterion 28, first part)

- **Creates** `tests/work/removed_2x.py` (choice 2).
- **Modifies** `tests/work/test_removed_commands.py`,
  `tests/work/test_no_2x_names.py` and `tests/work/test_cli_config.py`: import
  `REMOVED_2X_COMMANDS` from it in place of `tests.doc_allowance.REMOVED_COMMANDS`.
- **Proves:** the three test files; `tests/test_doc_allowance.py`; standing
  files. **Mutation:** add `"tcw work list"` to the tuple, and
  `test_removed_commands.py` fails for that entry. That shows the new tuple is
  read by that file, not that no file still reads the allowance: Task B18's
  test (no file under `tests/` names `doc_allowance`, and the module is gone)
  is what proves all three imports were switched.

### Task A2: `require_artifact.py` asks `tcw work path` (Design 7; criterion 20)

- **Modifies** `scripts/require_artifact.py` (choice 3).
- **Creates** `tests/test_require_artifact.py` (choice 4), with the cases of
  criterion 20: no `spec/spec.md` → the move is refused (exit 3) and the item
  stays at `spec`; an empty file and a white-space-only file → refused; a file
  with text → exit 0 and the item at `plan`, the hook having seen
  `TCW_SLUG=p/<folder>`; `TCW_SLUG` unset → exit 1; an unknown slug → exit 1;
  the script's text contains neither `--json` nor `TCW_NODE_ROOT`.
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
- **Proves:** standing files. **By hand, in a scratch fixture** binding these
  files as Design 6 does: `tcw work stage prompt spec <slug>` prints the
  built-in prompt, then `abstraction.md`, `harness.md` and the template whose
  `when:` matches (a `bug`-tagged item gets only `spec-bug.md`);
  `tcw work stage prompt review <slug>` ends with `review.md`; `tcw work
  procedure create-work` ends with `create-work.md`. Output recorded in the log.

### Task A4: The guide, part 1: who it is for, and every mapping (Design 1.1-1.2, 3, 4; criteria 4, 5, 6, 8)

- **Creates** `docs/migration-guide-2.8-to-3.0.0.md` with:
  - the opening, as paragraphs under the title with no `##` heading of its
    own (so A5's prerequisites and rules are the first two `##` sections):
    what changes, who the guide is for (an agent working with a user, under
    Claude Code or Codex, with any Jira access), projects older than 2.8
    upgrading first with the earlier guides;
  - the mapping tables of Design 3, in the order 3.1 to 3.10 (3.10, the
    deleted skills and agents, is spec amendment 22), each first column
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
  parts of choice 1, and a test running TCW-75's `link_problems` (from
  `tests/test_docs_describe_3_0.py`) over the guide. The guide links to
  TCW-75's documents (`docs/guide/configuration.md`'s git example section,
  `docs/guide/jira.md`, `skills/configure/references/*.md`) by their headings
  at `e301bef5`, and the guide is fixed for any link or anchor it reports.
- **Modifies** `tests/test_docs_describe_3_0.py`, in this same commit:
  `PENDING_TARGETS` (line 44), its use in the link check (line 227), and
  `test_the_link_check_lets_the_pending_migration_guide_through` (lines
  267-270) are deleted (spec amendments 18 and 23). The last asserts the guide
  does not exist, so the commit that creates the guide would otherwise turn it
  red; and without `PENDING_TARGETS`, README's index link to the guide is
  checked like any other.
- **Proves:** `tests/test_migration_guide.py`; `tests/test_docs_describe_3_0.py`;
  `tests/test_documented_cli_surface.py` (the guide stays exempt); standing
  files. **Mutations:** delete the `renames.yaml` row → criterion 4 fails
  naming it; swap `TCW_FROM_STAGE` and `TCW_STAGE` in the `TCW_STATUS` rows →
  criterion 5 fails; a link to `docs/guide/jira.md#no-such-heading` in the
  guide → the link test fails; rename the guide file → README's index link
  fails in `tests/test_docs_describe_3_0.py`.

### Task A5: The guide, part 2: rules, steps and REST forms (Design 1.2-1.8, 2; criteria 1, 2, 3, 7, 9, 10)

- **Modifies** `docs/migration-guide-2.8-to-3.0.0.md`:
  - prerequisites and rules (Design 1.2, as amended: no 2.x item worktree), as
    `## Before you start` and `## Rules`, inserted straight after the opening
    and before the first mapping table, so the guide opens with them
    (criterion 1);
  - the section on 2.x behavior that had no key (Problem 2.3, 2.4);
  - steps 0 to 11 (Design 2), each with what to do, its **Check** (a
    read-only shell command and its expected output, paths relative to the
    configured work path) and, at steps 1 and 2, **Stop and ask** (step 12 is
    Task A6); the
    idempotence rules of Design 1.5 and 1.8 in every step that writes to Jira;
  - a REST section: the `curl` form of every Jira read and write the steps
    use (JQL search, create, transition list and transition, field edit,
    comment list and comment, issue link), with the credentials by variable
    name, and the web UI as the equivalent.
- **Modifies** `tests/test_migration_guide.py`: criteria 1, 2, 3, 7, 9 and 10's
  parts of choice 1.
- **Proves:** `tests/test_migration_guide.py`; standing files. **Mutations:**
  remove step 4's `**Check:**` → criterion 2 fails; add `**Stop and ask**` to
  step 5 → criterion 3 fails; add `` !`tcw validate` `` → criterion 9 fails;
  add `tcw work start x` to a step → the parse check fails; move `## Rules`
  below the first mapping table → criterion 1 fails.

### Task A6: The guide, part 3: revisit agent instructions and memories (Design 1.5, 2 step 12; criteria 2, 3, 32; spec amendments 21 and 22)

- **Modifies** `docs/migration-guide-2.8-to-3.0.0.md`: the fourth stop in the
  rules section, and `### Step 12: Revisit agent instructions and memories`
  as Design 2 step 12 gives it (spec amendment 22):
  - where to look, as a list, in three groups:
    - the project: `CLAUDE.md` and `AGENTS.md` and every file they link to or
      import; `.claude/skills/`, `.claude/commands/`, `.claude/agents/`,
      `.codex/`, `.agents/skills/`; the `hooks` and `permissions.allow`
      entries of `.claude/settings.json` and `.claude/settings.local.json`;
      the prompt and procedure files the 2.x configuration bound (the step-1
      survey's list);
    - the user's own files: `~/.claude/CLAUDE.md`, `~/.codex/AGENTS.md`,
      `~/.claude/skills/`, `~/.claude/commands/`, `~/.claude/agents/`,
      `~/.codex/skills/`, `~/.agents/skills/`, `~/.codex/prompts/`
      (whichever exist), `~/.claude/settings.json`, `~/.codex/rules/`;
    - saved memories: `~/.codex/memories/`, and every Claude Code project
      folder belonging to the project, found by content, not by a naming
      rule: for each path `git worktree list --porcelain` prints,
      `grep -lE '"cwd":"<path>("|/)' ~/.claude/projects/*/*.jsonl` names
      transcripts, and each one's folder's `memory/` and `MEMORY.md` are
      searched;
  - the worktree rule: a run made in a worktree also searches the primary
    checkout's untracked per-user files, by the primary checkout's absolute
    path (`git -C <primary checkout> status --ignored --porcelain -- .claude
    .codex` lists them), since a worktree holds only tracked files;
  - what to look for: the first column of the mapping tables (3.1 to 3.10),
    the status folders with `inbox/`, `state.yaml`, `dod.yaml`, `--worktree`,
    the bare 2.x verbs and stage names, and text relying on automatic commits,
    publishing or retention, which memory prose often describes without naming
    a command;
  - the two searches, each fenced and written out in full: `NAMES` and `WORDS`
    defined as `grep -E` alternatives (each name word-bounded, status folders
    as `backlog/` and the like, with no leading slash); the files-to-read
    search `grep -rlE '\btcw\b|<NAMES>|<WORDS>' <places>`, case-sensitive,
    and the instruction to read each printed file in full and judge every
    passage, not only matched lines; the check's search
    `grep -rE '<NAMES>' <places> | sort`;
  - the one question to the user: each finding with the proposed action
    (delete; rewrite, with the proposed text; keep, with the reason). Nothing
    is changed before the answer, and only what is approved is applied;
  - files outside the repository are the person running the migration's own,
    and each other contributor repeats the step for theirs;
  - the log section `## Agent instructions`: one line per finding (file and
    line as found, the decision, what was done), ending with a fenced block
    of the lines expected to match `NAMES` afterwards, as `<file>:<text>`:
    kept lines as they stand, and rewritten lines' approved text where it
    still matches;
  - **Check:** `grep -c '^## Agent instructions' <log>` prints `1`; the
    check's search, sorted, compared by `diff` with the expected block,
    prints nothing (no line numbers compared; a rewritten line that still says
    `tcw` is not a failure, since `NAMES` has no `tcw`); if a bound file
    changed, `tcw validate` exits 0.
- **Modifies** `tests/test_migration_guide.py`: criterion 32's parts of choice
  1 (the places, the worktree rule, the two searches and the coverage of every
  first-column name by `NAMES` or `WORDS`), and the step and stop counts for
  criteria 2 and 3.
- **Proves:** `tests/test_migration_guide.py`; standing files. **Mutations:**
  remove `~/.codex/AGENTS.md` from step 12 → criterion 32 fails naming it;
  remove step 12's **Stop and ask** → criterion 3 fails; remove `verifier`
  from `WORDS` and `NAMES` → the coverage test fails naming the Design 3.10
  row; add `tcw` to `NAMES` → the test fails; remove "in full" from the
  files-to-read instruction → the test fails.

### Task A7: The filesystem rehearsal (Design 5.2, 5.3; criteria 10, 25)

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
  list-form `capabilities.yaml`; an inbox entry; a `blocked/` folder holding
  one item, placed by hand; and, for step 12 (spec amendment 22):
  - a project `CLAUDE.md` naming `tcw work start --worktree`;
  - a memory file under the scratch `HOME`'s `.claude/projects/<folder>/memory/`
    (with a transcript beside it whose `cwd` is the rehearsal project, so the
    folder is found by content) holding a line that names `tcw` and, on
    another line with no `tcw` and no name from `NAMES` or `WORDS`, a 2.x
    instruction in plain prose ("write the user's acceptance into a file in
    the item's folder before closing it");
  - a second memory file with no `tcw` in it at all, naming `refined-outcome.md`;
  - a skill under the scratch `HOME`'s `.claude/skills/` naming
    `tcw work submit`;
  - a `.claude/settings.local.json` allowing `Bash(tcw work submit:*)`,
    ignored by the rehearsal project's `.gitignore`, and the step run from a
    worktree of the rehearsal project, so the primary checkout's copy is the
    only one.
- **Follows** the guide, filesystem mode, step by step, with the 3.0 CLI from
  `venv` only at step 11, and step 12 finding every planted instruction,
  including the prose line, which only reading the file in full finds (the
  rehearsal answers its question itself, rewriting, deleting and keeping at
  least one each), its check's `diff` printing nothing, ending with
  `tcw validate` exit 0.
- **Modifies** the guide and its test wherever the rehearsal shows the guide
  wrong or unclear (one commit on the work branch).
- **Runs** `tcw <command> --help` for every `tcw` command the guide names, on
  the 3.0 CLI (criterion 10).
- **Writes** in `outcome.md` on `main` (one commit): under `## Rehearsal`, the
  2.8.1 commands and hand placements that built the project, each step's check
  output, every guide amendment, and the final `tcw validate`; under
  `## Criterion 10`, each command and its exit code. Nothing of the rehearsal
  project is committed.

### Task A8: The Jira checklist for the owner (Design 6.2; criterion 24, first part)

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
  begun** (migration step 2), because the released 2.8.x CLI that still moves
  `main`'s board names `Start` and finds routes by the old transitions.

### Task A9: A bounded review of the guide before it touches Jira

- An `adversarial-spec-reviewer` round over the guide, its test and the
  rehearsal record, given the spec and its amendments; bounded as in the
  rules. Accepted findings fixed in one commit on the work branch (the guide
  and its test); the result recorded in `outcome.md` on `main`.

### Task A10: The capability descriptions that still name removed things (Design 7; spec amendment 6; formerly Task B2)

- **Modifies** `docs/capabilities/work/configure-the-work-store-location/description.md`
  (`tcw work init` → `tcw init --work-path`),
  `docs/capabilities/cli/validate-a-project/description.md` (no
  `tcw taxonomy check` or `tcw capabilities check`; the sentence says
  `tcw validate` checks the ledgers),
  `docs/capabilities/work/configure-the-work-lifecycle/description.md` (the
  removed `work.*` keys replaced by `work.stages` and `work.hooks`), each
  keeping what it promises; and `tests/doc_allowance.py`, removing every entry
  that only these records named, in the same commit, since TCW-75's
  "still named somewhere" check fails otherwise. After this, only
  `tcw work stage gate` is left, named by `AGENTS.md:16`, and B14 removes it.
  Runs after A1, which gives the three code tests their own list.
- **Writes** this item's `capabilities.yaml` on `main` (separate commit):
  `changed:` the three paths.
- **Proves:** `tests/test_doc_allowance.py`, `tests/test_ledger_3_0.py`,
  `tests/test_documented_cli_surface.py`, standing files; and the branch's
  `tcw validate` in a scratch fixture holding copies of the three records and
  the records they link to, recorded in the log.
  **Mutation:** put `tcw work init` back into `REMOVED_COMMANDS` →
  `test_an_entry_is_still_named_by_some_live_document` fails naming it.

## Part B — needs the code freeze

### Tasks B1 and B2: moved into Part A

TCW-75 is on `e301bef5`, where the work branch starts, so there is nothing to
merge. B1's removal of `PENDING_TARGETS` and its link test are in Task A4;
B2's capability descriptions are Task A10. The numbers B1 and B2 are kept
unused so that B3 to B24 keep theirs.

### Task B3: Merge and freeze (Design 8.5.1-8.5.2; spec amendments 13 and 23)

- **Waits for** the code follow-up item of the Blockers section, completed and
  merged into `epic/tcw-3.0`. 2.8.2 (Pi) is already merged into `main`
  (`dc0aaa7a`, `74630308`) and published from `v2.8.2`.
- The Pi item on `main` (`review/2026-10-07-make-the-plugin-installable-in-pi`)
  is completed with the released 2.8.2, or the owner says it waits.
- In the epic worktree (`.worktrees/tcw-3-0-epic`, made here; see the rules):
  `epic/tcw-3.0` is fast-forwarded to the work branch
  (`git merge --ff-only <work branch>`); the work worktree and branch are
  removed.
- `git merge main` into `epic/tcw-3.0`, in the epic worktree. A trial with
  `git merge-tree --write-tree main e301bef5` on 2026-10-15 conflicted in
  `README.md`, `docs/lifecycle/harness.md`, `skills/setup/SKILL.md` and
  `skills/work/references/procedures/delegation.md` (changed on `main`,
  deleted on the epic). Conflicts are resolved by keeping the epic's text and
  carrying the Pi facts into it: Pi installation in TCW-75's README install
  section; the Pi lines of `docs/lifecycle/harness.md` into TCW-75's version
  (its Agentskills link, which `74630308` restored on `main`, is already in
  TCW-75's text at line 10); `skills/setup/SKILL.md` on TCW-74's text;
  `delegation.md` stays deleted. The same trial merged these without conflict,
  and each is read after the merge all the same: `package.json` (keeps
  `main`'s `pi` block and the epic's removal of `fastify` and `esbuild`),
  `.codex-plugin/plugin.json` (the epic's long description with `main`'s
  2.8.2 version), `skills/README.md` and `skills/setup/references/install.md`
  (TCW-74's text with the Pi facts). The two
  `docs/capabilities/plugin/*/description.md` take the Pi sentence. All five
  version files say 2.8.2 after the merge. The board arrives unchanged.
- **The freeze begins**: the epic tip is the freeze commit; the owner is told
  that `main`'s board is frozen and that the Jira checklist may now be applied
  when step 2 asks.
- Migration worktree and branch `migrate/tcw-3.0-run-1` made from it; `venv`
  re-pointed.
- **Proves:** every test file that reads a file the merge changed (at least
  `test_docs_describe_3_0.py`, `test_shipped_text.py`,
  `test_dynamic_skill_marker.py`, `test_documented_cli_surface.py`,
  `test_skill_path_pointers.py`, `test_plugin_manifests.py`), standing files.

### Tasks B4 to B16: The migration, steps 0 to 12 (Design 2, 4, 6, 7; criteria 11-18, 24, 27, 30, 31, 32)

One task and one commit per step, on the migration branch, following the guide
as written. Each step's check output goes in the log. TCW's particulars:

- **B4, step 0.** Prerequisites; `git status --ignored -- docs/work` lists the
  ignored discarded folders (33 on this machine on 2026-10-15); the log starts
  under `## Run 1` with the start date, the freeze commit, and each finished
  slice with its `graveyard.yaml` `location` and the `git cat-file -e` result
  (criterion 27): TCW-69 to TCW-74 and TCW-77 as listed under "Before the
  first task", and TCW-75 at `560e312f` (deleted in `b5b7756f`).
- **B5, step 1 — Stop and ask.** The consolidated plan: Jira mode; every
  optional stage enabled; statuses (Design 6.2); each item's stage and
  converted fields; every disk–ticket difference, including TCW-9's
  `sync: pending`; the tickets to create (up to 21 on 2026-10-15) and their
  exact comments; request placement per ticket; the prune list as amended
  (Design 2 step 1); the ignored discarded folders (none kept unless named);
  the inbox entries (seven on `main` on 2026-10-15, fewer once the code
  follow-up item of the Blockers section has taken five; recounted here); `<hook files>`; step 9's skipped folder (this item's); the config,
  hook, record and project-file rewrites. Approval recorded verbatim under
  `## Approved plan`.
- **B6, step 2 — Stop and ask.** The workflow is read again and the checklist
  of Task A8 updated if it changed; the owner applies it and confirms each
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
  clean. **The same commit removes `tcw work stage gate` from
  `REMOVED_COMMANDS`** in `tests/doc_allowance.py` (spec amendment 23):
  `AGENTS.md:16` is the only live document naming it, so once that line is
  rewritten `tests/test_doc_allowance.py`'s
  `test_an_entry_is_still_named_by_some_live_document` fails for the entry.
  This empties `REMOVED_COMMANDS`, which A1 made safe for the three code
  tests. Proves: `tests/test_doc_allowance.py`,
  `tests/test_documentation_sync_wiring.py`, `tests/test_docs_describe_3_0.py`,
  standing files.
- **B15, step 11.** `tcw validate` and `tcw validate --remote` from `venv`
  in the migration worktree, each finding fixed or listed (criterion 15);
  `tcw work list --all --json` against the approved stages (criterion 14).
- **B16, step 12 — Stop and ask** (the owner's addition; criterion 32; spec
  amendment 22). Step 12 carried out on TCW itself, from the migration
  worktree, over:
  - in the repository: `AGENTS.md` (which `CLAUDE.md` links to) and the files
    it links to; `.claude/settings.json` and anything else tracked under
    `.claude/`; the prompt and procedure files the configuration binds
    (`docs/lifecycle/*.md`, `docs/lifecycle/templates/*.md`,
    `docs/procedures/create-work.md`, the step-1 survey's list);
  - the primary checkout's untracked per-user files, by absolute path, since
    the migration worktree does not have them:
    `/Users/brian/Projects/TCW/.claude/settings.local.json` (ignored by the
    owner's global git ignore file; 33 lines name `tcw` on 2026-10-15), and
    whatever else `git -C /Users/brian/Projects/TCW status --ignored
    --porcelain -- .claude .codex` lists then;
  - the owner's own files: `~/.claude/CLAUDE.md`, `~/.codex/AGENTS.md`,
    `~/.claude/skills/` (on 2026-10-15
    `~/.claude/skills/autonomous-work/SKILL.md` names
    `tcw work list --status backlog` at line 14, the `tcw-verifier` agent,
    `tcw work submit` and `tcw work complete` at lines 49-54),
    `~/.claude/agents/`, `~/.claude/commands/` (absent on 2026-10-15),
    `~/.codex/skills/`, `~/.agents/skills/`, `~/.codex/prompts/` (absent),
    `~/.claude/settings.json` (the allow entry `Bash(tcw *)` at line 81 and
    the auto-mode text describing `tcw` at about lines 339-374), and
    `~/.codex/rules/default.rules` (15 lines name `tcw`);
  - memories: `~/.codex/memories/` (its `MEMORY.md`, `memory_summary.md`,
    `raw_memories.md` and several `rollout_summaries/` files name `tcw`), and
    every `~/.claude/projects/*` folder the transcript search finds for the
    paths `git worktree list --porcelain` prints at the time, each with its
    `memory/` and `MEMORY.md`. On 2026-10-15 that search, run for
    `/Users/brian/Projects/TCW`, found only
    `/Users/brian/.claude/projects/-Users-brian-Projects-TCW/`; the
    migration worktree adds its own path, and any folder found for it is
    searched too.
  The skills under `skills/` are the product, already rewritten by TCW-74,
  and are not in scope. Every file the files-to-read search prints is read in
  full. Expected findings, for the proposal: `AGENTS.md`'s
  rule against driving the lifecycle with the `tcw` CLI while TCW's own code
  changes, and its worktree section; memories that describe 2.x behavior
  (`tcw-can-be-driven-by-manual-edits`, `the-item-is-truth-always-applies`
  and its sync wording, `triage-writes-the-request-read-it-first`,
  `fold-small-follow-ups-into-the-current-item` and its "verify" stage,
  `venv-instead-of-repointing-the-shared-tcw-install`, which names
  `tcw work start --worktree`); `skills-restructure-resume-point`, finished
  since v2.2.0; and the epic's own memories
  (`skip-full-suite-during-tcw-3-0-epic`,
  `tcw-3-0-epic-adversarial-review-is-approval`, `tcw-3-0-epic-resume-point`),
  whose proposal is "delete at the end of the epic" (Task B24) rather than
  now, since this run still relies on them. `.claude/settings.local.json`
  allows `tcw` commands by name (33 lines name `tcw` on 2026-10-15), and each
  allowed 2.x command is proposed for removal; `.claude/settings.json` enables
  the plugin and wires `scripts/remote_session_setup.sh`, and is expected to
  be kept; the owner's `Bash(tcw *)` allow entry is expected to be kept, and
  the `autonomous-work` skill's 2.x commands and agent name rewritten.
  The owner decides each; the log's `## Agent instructions` records each
  finding, decision and action, and its expected block; the check's `diff`
  prints nothing. Changes inside the repository are this step's commit;
  changes to `settings.local.json`, the memory folders and the owner's
  personal files are not in git, and the log says so for each.

A step whose check fails after one retry stops the run and goes to the owner;
a defect in 3.0 code abandons the run (Design 8.5.3) and the next run begins
again at B3's last bullet.

### Task B17: `tests/test_repo_lifecycle.py` for 3.0 (Design 7; criteria 16, 21)

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

### Task B18: The allowance is emptied and deleted (Design 7; criterion 28)

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

### Task B19: This item's release notes and changelog (Design 7; criterion 29)

- **Creates** `docs/release-notes/upcoming/TCW-76-<title words>.md` and the
  same name under `docs/changelogs/upcoming/`, the folder name step 6 gave
  this item: release notes under `## Upgrading` (how to move a 2.8 project, a
  link to the guide); changelog under `## Added` (the guide,
  `docs/lifecycle/review.md`, the new tests) and `## Changed` (TCW's own
  configuration and board on 3.0, `require_artifact.py`, the removed
  allowance). No text before the first `##`.
- **Proves:** `tests/test_upcoming_entries.py`, `tests/test_cut_version.py`.

### Task B20: Mutation record, full suite, drift, and the evidence

- Every mutation named above re-run once, each result in the log.
- `pytest --collect-only -q` clean; **the full suite once, with bare `pytest`,
  from the migration worktree with `venv` first on `PATH`** (criterion 21).
- `tcw capabilities drift`; each line in the log with its cause (expected:
  `work/customize-the-definition-of-done`, declared by the completed
  `stop-offering-…` item and removed by a deleted child; criterion 22).
- Criterion 30 checked by reading each pruned ticket once; criterion 24's
  workflow `GET`.
- Criterion 10 again, over the final guide: `tcw <command> --help` for every
  `tcw` command it names, on the 3.0 CLI from `venv`, each exit code in the
  log (A7 ran it on the guide as it stood then; the run and A9 may have
  changed it since).
- The `documentation-sync` skill evaluated over the item's whole difference.
- The log gets one line of evidence per criterion.

### Task B21: Merge the migration and enter review (Design 8.7.1; criteria 23, 26)

- In the epic worktree, `.worktrees/tcw-3-0-epic`: the migration branch
  merges into `epic/tcw-3.0`;
  `git diff --stat <freeze commit>..<that merge> -- tcw skills agents web`
  prints nothing (criterion 23).
- `venv` re-pointed to the epic worktree (`pip install -e
  .worktrees/tcw-3-0-epic --no-deps`), and from that worktree:
  `tcw work advance tcw/TCW-76-<words>` to review exits 0 and its `post` hook
  commits or reports nothing to commit (criterion 26). This is TCW-76's first
  3.0 move. B22 and B23 run from the same worktree.

### Task B22: The review stage (spec Design 8.7.2, amendment 14)

- Bounded adversarial review, split into the guide and its tests (A4 to A7,
  A9), the migrated board, configuration and records (A3, A10, B3 to B17), and
  the test changes (A1, A2, B14's allowance entry, B18), then one combined pass
  over the whole difference since the work branch's start,
  `e301bef5..<B21's merge>`. Accepted findings are fixed in the item (a rejection moves it
  back to implement, with a new implement round).
- `review/round-<n>.md` written with `verdict: accepted` and `judges:` the
  latest implement round; `tcw work advance` to qa.

### Task B23: QA by the owner, then complete TCW-76 and TCW-68 (Design 8.7.2)

- **Stop and ask:** qa is the owner's own end-of-epic review. When the owner
  accepts, `tcw work advance tcw/TCW-76-<words> --to completed --reason
  "<the owner's acceptance>"`; the completion gate reads the review verdict
  and `completed.pre` runs `tcw validate`.
- `tcw work advance tcw/TCW-68-<words> --to completed --force --reason
  "all children complete"`.

### Task B24: Main, the cut, the push, the issues (Design 8.7.3-8.7.6)

- `epic/tcw-3.0` merges to `main`; the local suite and `gh run list` for
  `main`'s CI both green.
- The memories step 12 marked "delete at the end of the epic" are deleted
  and removed from `MEMORY.md`, as the owner approved.
- `python scripts/cut_version.py 3.0.0`. **Before the tag is pushed**, on the
  cut commit: `pytest tests/test_upcoming_entries.py tests/test_cut_version.py
  tests/test_plugin_manifests.py` passes (the cut rewrote the version files
  and folded the `upcoming/` entries, which the full run in B20 predates).
- The tag pushed with `main`, which publishes the release (no further
  confirmation, per the owner's standing rule, once verification has
  passed). Then the `release` workflow run for the tag is watched to the end
  (`gh run list --workflow release.yml`, `gh run watch <id>`), and
  `https://pypi.org/pypi/tcw-cli/3.0.0/json` answers with version `3.0.0`; a
  red run or a missing version goes to the owner.
- Only then: any originating GitHub issue answered and closed, each with text
  the owner has approved.

## Documentation Sync

The project's entries as the plan stage printed them (2.x wording), and what
answers each:

| Entry | Trigger | Answered by |
| --- | --- | --- |
| `README.md` | Public-API | TCW-75 added the guide's index row (on `e301bef5`); A4's removal of `PENDING_TARGETS` makes TCW-75's link check cover it; this item only resolves the Pi merge in Task B3 |
| `docs/guide/jira.md` | Tracker-Change (becomes Jira-Change at B7) | Does not fire: no Jira behavior or key changes. TCW-75's |
| `docs/guide/<topic>.md` | Guide-Topic-Change | Does not fire: the migration guide is not under `docs/guide/` |
| `docs/release-notes/upcoming/<folder>.md` | Public-API | Task B19 |
| `docs/changelogs/upcoming/<folder>.md` | Any-Code-Change | Task B19 |
| `skills/<component>/SKILL.md` | Skill-Driven-Component | Does not fire: no skill changes, beyond resolving the Pi merge (B3) |
| `skills/configure/references/<document>.md` | Configuration-Key-Change | Does not fire: no key changes |

The entries themselves are rewritten at Task B7 (spec Design 6.4). The
`documentation-sync` skill is invoked over the whole difference in Task B20.

## Verification

What the suite cannot check, and how it is checked:

1. **The guide reads as an agent would follow it** (criteria 1-3, 7, 9 beyond
   the test): the rehearsal (A7), the review (A9), and the real run (B4-B16,
   including step 12 on TCW's own instructions and memories),
   where any wrong or unclear text is fixed before the step is redone.
2. **Criterion 10:** every command's `--help` run by hand (A7), and again over the final guide (B20).
3. **Jira:** criterion 24's checklist confirmation and the post-migration
   workflow `GET`; criterion 30 by reading each ticket; criterion 31 by the
   rerun and a JQL `updated >=` search. All recorded in the log.
4. **Criterion 15** (`validate --remote`) needs the live site; run in B15.
5. **Criterion 21's full suite** runs once, in B20, as CI runs it.
6. **Harness:** the guide is plain Markdown using only shell, `curl` and
   `tcw`; the test forbids `` !` `` and slash commands.
7. **Review:** Tasks A9 and B22, bounded as in the rules.
8. **Board and ticket:** until B3 this item is moved on `main` with the released 2.8.x;
   after the migration commit, with the 3.0 CLI.

## Criterion-to-task table

| Criterion | Tasks |
| --- | --- |
| 1 Opening | A4 (the opening, with no `##` of its own), A5 (puts `## Before you start` and `## Rules` first; the test checks they are the first two `##` sections and come before any mapping table), A9 |
| 2 Steps and checks | A5, A6 (step 12) |
| 3 Stops | A5, A6 (step 12's stop) |
| 4 Every 2.x name mapped | A4 (including Design 3.10) |
| 5 Hook variables by meaning | A4 |
| 6 `artifacts` rule and status translation | A4 |
| 7 Behavior with no key | A5 |
| 8 Verdict rounds | A4, A7 |
| 9 No harness-only mechanism | A5 |
| 10 Every command exists | A5 (parse), A7 and B20 (`--help`) |
| 11-13 Folders, `item.yaml`, documents | B8-B12 |
| 14 `list --all --json` stages | B15 |
| 15 `validate`, `validate --remote` | B15, B20 |
| 16 Configuration | B7, B17 |
| 17 `Planning doc` | B14 |
| 18 `.gitignore` | B14 |
| 19 `AGENTS.md` and the link | B14 (TCW-75 already changed the READMEs on `e301bef5`) |
| 20 `require_artifact.py` | A2 |
| 21 Repo test and full suite | B17, B20 |
| 22 Drift | B20 |
| 23 No code change after the freeze | B3, B21 |
| 24 The log and the checklist | A8, B4-B16, B20 |
| 25 Rehearsal | A7 |
| 26 First 3.0 move | B21 |
| 27 Sibling specs readable (amended) | B4 |
| 28 Allowance gone | A1, A4 (`PENDING_TARGETS`), A10, B14, B18 |
| 29 Upcoming entries | B19 |
| 30 Prune list | B5, B10, B20 |
| 31 Step 6 rerun writes nothing | B10 |
| 32 Step 12, instructions and memories (owner's addition) | A6, A7, B16 |

Every task traces to a criterion: A1 to 28; A2 to 20; A3 to 16, 21 (bound
files exist; Design 6.3); A4 to 4-6, 8, 28; A5 to 1-3, 7, 9, 10; A6 to 2, 3, 32; A7 to 8, 10, 25, 32;
A8 to 24; A9 to 1-10; A10 to 28 (amendment 6); B3 to 23; B4-B16 to
11-18, 24, 27, 28 (B14), 30, 31, 32; B17 to 16, 21; B18 to 28; B19 to 29; B20 to 10, 21,
22, 24, 30; B21 to 23, 26; B22 and B23 to the end of Design 8.7; B24 to Design
8.7.3-8.7.6.

## Notes

- **Abstraction litmus test.** This item adds no operation. The guide states
  every step for both backends, with Jira's form of each fact Jira owns, and
  `require_artifact.py` keeps asking TCW where a document lives (`tcw work
  path`) instead of composing a path.
- **TCW-75, now complete** (`e301bef5`): it shrank `REMOVED_COMMANDS` to four
  entries, which three code tests still read as the list of commands that must
  stay gone, and an empty list would break `tests/work/test_no_2x_names.py`;
  Task A1 gives them their own list before A10 and B14 empty it. Its
  `test_the_link_check_lets_the_pending_migration_guide_through` asserts the
  guide does not exist, so it goes in A4, the commit that creates the guide.
  `main`'s Pi change edits `README.md` and `docs/lifecycle/harness.md`, which
  TCW-75 rewrote; Task B3 carries the Pi facts into its text.
