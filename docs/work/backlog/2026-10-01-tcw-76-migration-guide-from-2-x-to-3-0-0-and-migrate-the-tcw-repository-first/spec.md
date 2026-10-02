# Spec — Migration guide from 2.x to 3.0.0, and migrate the TCW repository first

## Capability changes

**None.** This slice writes a document and migrates this repository's own data and
configuration. No command gains, loses or changes behavior here; the behavior the
guide migrates to ships in TCW-69 to TCW-73 and TCW-77, and each of those updates
the records for what it changes (TCW-75's ticket, "Who owns the rest"). This item's
`capabilities.yaml` declares nothing.

The migration does edit capability records, but only their data, not what they
promise:

- **The `Planning doc` field is removed from every record** that carries it, 65 of
  the 105 `meta.yaml` files under `docs/capabilities/` today. TCW-73 removes the
  field from `CAP_FIELDS` and the capabilities commands; this slice removes it from
  the records (epic decision 9). See Design 3.7.
- No record carries the `Tracker` field today (0 of 105), so its removal changes
  nothing here.

Two facts about the ledger matter to the slices that do change it:

- The **46** records under `docs/capabilities/work/`, most describing 2.x behavior,
  are decided one by one by TCW-70, with TCW-71 taking the tracker ones TCW-70
  leaves and TCW-73 the later wording changes (epic decision 12). This slice
  changes none of them beyond the `Planning doc` line.
- 3.0 drift reads the declarations of completed items (TCW-69 Design 7). The two
  completed items this migration carries over declare paths that 3.0 slices may
  remove; Acceptance criterion 22 makes that visible.

## Problem

### 1. A 2.x project cannot be opened by 3.0, and nothing converts it

3.0 ships no code that detects or converts a 2.x project (ticket; TCW-69 spec,
"Constraints"). TCW-69's configuration parser reports the removed 2.x keys as
errors that name `docs/migration-guide-2.8-to-3.0.0.md` (TCW-69 spec, Design 8,
check 4), and that guide does not exist. What a 2.x project holds, all of which
3.0 replaces:

- **Status directories.** An item's status is the first folder under the work root
  (`tcw/store/fs.py:4787-4790`), one of `backlog`, `active`, `review`,
  `completed`, `discarded` (`tcw/store/base.py:989`). The inbox is loose `.md`
  files in `inbox/`.
- **Item files.** `state.yaml` holds the item's fields; the reader takes `title`,
  `created`, `resolution`, `priority`, `effort`, `complexity`, `tags`,
  `blocked_by`, `initiative`, `type`, `worktree`, `branch`, `parent`, `owner` and
  `started` (`fs.py:5370-5390`). `tracker.yaml` holds a Jira binding.
- **Lifecycle documents** at the item root, named by `WORK_ARTIFACTS`:
  `initial-request`, `spec`, `plan`, `outcome`, `refined-outcome`, `rework`,
  `post-mortem`, `intake` (`base.py:3101-3102`), plus the side files
  `capabilities.yaml`, `rollup.md` and `tracker.yaml` (`WORK_SIDECARS`,
  `base.py:3113`).
- **Store-root files.** `graveyard.yaml` records deleted items; `dod.yaml` replaces
  the built-in Definition of Done (`DEFAULT_DOD`, `base.py:3096-3097`).
- **Configuration.** `work.lifecycle` takes `stages`, `transitions`, `timeout`,
  `artifacts` and `output-cap` (`base.py:2982`). `work.tracker` takes 14 keys
  (`base.py:1359-1363`), plus `create` sub-keys (`base.py:1364-1365`) and
  per-move transition names (`base.py:1381`). `retain`, `auto-commit-transitions`,
  `publish-transitions` and `trunk-branch` sit directly under `work`
  (`fs.py:7201`, `7212`, `7227`, `7566`).

Every existing project is stranded at 2.8 until this guide exists.

### 2. Several mappings look like renames and are not

A guide that treats the 2.x-to-3.0 change as a list of renames gets these wrong:

1. **Hook variables mean different things.** In 2.x, `TCW_STATUS` is the item's
   status *when the hook runs*: the source status for a `pre` hook (`"backlog"` for
   start, `tcw/work/cli.py:1616`) and the destination for a `post` hook
   (`"active"`, `cli.py:1672`). `TCW_TRANSITION` is the move's name (`start`,
   `complete`, …) or, from `stage gate`, a stage name (`cli.py:1994`). In 3.0,
   `TCW_STAGE` is always the target and `TCW_FROM_STAGE` always the source (TCW-69
   Design 6.5). The ticket's list ("`TCW_STATUS`, `TCW_TRANSITION` and
   `TCW_NODE_ROOT` become `TCW_STAGE`, `TCW_FROM_STAGE` and `TCW_PROJECT_ROOT`")
   pairs them by position, which would turn a `pre` hook's source status into the
   target. 2.x also gives `generate` bindings `TCW_HOOK_ROLE`, `TCW_HOOK_KIND`,
   `TCW_HOOK_ID` and `TCW_HOOK_PHASE` (`tcw/work/resolve.py:191-196`).
2. **Templates are first-match, prompts are cumulative.** A 2.x
   `work.lifecycle.artifacts` list is first-match-wins: the first entry whose
   `when:` matches replaces everything after it (`base.py:2633-2648`). A 3.0
   `prompt` list includes every entry whose `when:` matches (TCW-69 Design 8).
   This repository's `spec` artifacts list (`tcw-config.yaml:104-110`) is a
   `bug`-tagged template followed by an unconditional one; moved over as-is, a bug
   item would get both.
3. **Some 2.x behavior has no key to flag.** A project that never set
   `auto-commit-transitions` still committed every move, because it defaults to
   true (`fs.py:7227-7228`); `publish-transitions` also defaults to true
   (`fs.py:7201-7202`). 3.0 removes both, so such a project silently stops
   committing unless it adopts TCW-75's opt-in example. The same holds for
   retention, whose default keeps everything (`base.py:2860`).
4. **`.gitignore` can hide items.** This repository ignores
   `docs/work/discarded/*` (`.gitignore:28-30`), so discarded items exist only on
   the machine that discarded them. 3.0 never moves a folder, so the rule stops
   matching anything, and every untracked discarded folder on that machine is
   invisible to the migration unless the guide looks for it.
5. **2.x "verify" was the requester's acceptance.** `refined-outcome.md` and
   `rework.md` record the user accepting or rejecting finished work (the
   `commands-verify-work` skill; `CLAUDE.md:43-51`). The epic's decision record
   maps them to `review` rounds; the ticket maps them to `qa` rounds. 3.0 rounds
   also need `judges: N` (TCW-69 Design 4.6), which no 2.x file has.
6. **Priority is an integer in 2.x** ("higher int = higher priority",
   `base.py:3237`) and a named scale in 3.0 (TCW-69 Design 2.2).
7. **Jira mode moves ownership, not just files.** In Jira mode `item.yaml` holds
   only the ticket link (TCW-71); title, status, priority, tags, assignee, parent
   and blocking links live in Jira. Disk and Jira disagree today whenever a 2.x
   sync did not land: `TCW-9`'s `tracker.yaml` holds a `sync: pending` record for a
   `start` move that never reached Jira.

### 3. TCW's own repository is the first project to migrate

Recounted on this branch on 2026-10-01 (the ticket's figures predate the import of
TCW-68 to TCW-77):

| What | Ticket says | This branch |
| --- | --- | --- |
| Items | 25 | **35**: 33 in `backlog/`, 2 in `completed/`; `active/`, `review/`, `blocked/` empty; `discarded/` empty in git, and ignored on disk (Problem 2.4) |
| Bound to a ticket (`tracker.yaml`) | 17 | **27**; the 8 unbound are 7 backlog items and 1 completed item |
| Inbox entries | 10 | **10** |
| `graveyard.yaml` entries | 310 | **308**: 277 `done`, 21 `wontfix`, 10 `superseded`; 247 carry a `location` commit |
| `dod.yaml` | present | 5 entries: the 4 defaults plus the GitHub-issue rule |

Their contents, which decide what the migration does:

- **Documents:** 31 `intake.md`, 12 `initial-request.md`, 4 `spec.md`, 4
  `plan.md`, 2 `outcome.md`, 2 `refined-outcome.md`, 1 `capabilities.yaml`; no
  `rework.md`, `post-mortem.md` or `rollup.md`.
- **Stages by the ticket's table:** 31 at request, 2 at plan
  (`2026-09-15-let-tcw-work-list-sort-…`, TCW-50, and TCW-69), 2 completed. These
  will change before the migration runs, as TCW-69 to TCW-77 progress.
- **Fields:** 19 items have an integer priority (7 in the "highest" band, 4 high, 4
  medium, 1 low, 3 lowest); 16 have none. 9 have a `parent` (TCW-69 to TCW-77,
  under TCW-68); 1 has `type: epic` (TCW-68); 1 live blocker (TCW-10 is blocked by
  TCW-14); 2 have `owner` and `started` (the completed items); 1 has an empty
  `phase`.
- **Capability records:** 65 carry `Planning doc:` (Design 3.7).

The repository also encodes 2.x in its own files:

- `tcw-config.yaml` uses `work.tracker`, `work.retain`, `work.lifecycle` (stages,
  `artifacts`, transitions) and `builtin: true` (`tcw-config.yaml:1-114`).
- `scripts/require_artifact.py` reads the 2.x `show --json` artifact map and cites
  `TCW_NODE_ROOT` (`scripts/require_artifact.py:9-13`, `:39-55`).
- `tests/test_repo_lifecycle.py` parses the real `tcw-config.yaml` with the 2.x
  parser and compares this repository's spec template with
  `tcw.work.templates._SPEC` (`tests/test_repo_lifecycle.py:1-55`), and pins the
  documentation entries and their triggers (`:89-112`).
- `CLAUDE.md` and its identical copy `AGENTS.md` describe `stage gate`,
  `dod.yaml`, `refined-outcome.md` and `upcoming/<work-item-slug>.md`
  (`CLAUDE.md:11-51`, `:150`). `tests/test_documentation_sync_wiring.py:26` and
  `tests/test_repo_lifecycle.py:118` read `AGENTS.md`.
- The documentation entries name `Tracker-Change`, `work.tracker`, `dod.yaml` and
  `upcoming/<slug>.md` (`tcw-config.yaml:34-76`), and the two `upcoming/README.md`
  files say `<work-item-slug>.md` (line 6 of each).
- `docs/procedures/create-work.md` continues TCW's built-in `create-work` text by
  step number (`docs/procedures/create-work.md:6`, `:34`), which TCW-74 rewrites.

### 4. The epic's own board has nowhere to live while 3.0 is built

From TCW-70 onwards the working-tree CLI is 3.0: it cannot read the 2.x board, and
it rejects this repository's 2.x `tcw-config.yaml`. `CLAUDE.md:29-41` forbids
driving the lifecycle with the CLI while `tcw/` is changing anyway. TCW-70 to TCW-75
and TCW-77 must still be tracked from the moment they start until this slice
migrates the board.

## Goals

1. **A guide an agent can follow** at `docs/migration-guide-2.8-to-3.0.0.md`, for
   both backends, with a check after every step and a fixed, small set of points
   where it stops and asks.
2. **Complete coverage.** Every 2.x configuration key, item field, document, side
   file, store-root file and hook variable has a row saying what it becomes or why
   it goes.
3. **TCW migrated in Jira mode by following the guide as written,** with
   `tcw validate` clean, landing with the change that switches TCW to 3.0.
4. **TCW's own 3.0 configuration:** the opt-in git example, a project-defined
   completion gate replacing `dod.yaml`, documentation entries rewritten.
5. **The guide proven in filesystem mode too,** on a disposable 2.8 project.
6. **A stated way to track this epic's board** until the migration.

## Non-goals

- **Migration code.** No converter, detector, command or committed script. An agent
  following the guide may write a throwaway helper for a bulk step, but nothing of
  it is committed, and every step's check is written so that it holds however the
  step was done.
- **Projects older than 2.8.** They upgrade to 2.8 first, with the earlier guides.
- **3.0 code, prompts, skills, documentation and viewer.** TCW-69 to TCW-75 and
  TCW-77. This includes `docs/lifecycle/abstraction.md`, `implementation.md` and
  `harness.md`, the README and its documentation index, the guides, and the
  `--worktree` section of `CLAUDE.md`, all TCW-75's.
- **Recreating deleted items.** Items in `graveyard.yaml` stay deleted, and their
  old slugs stop resolving.
- **Rewriting history.** Old slugs in changelogs, release notes and finished
  documents are left as they are.
- **Deciding which backlog items still matter.** The guide offers a prune step
  (Design 2, step 1); the decisions are the project owner's. For TCW they are
  already made (Design 2, step 1, "TCW's prune list").
- **The eval harness.** `evals/seed_fixture.py` builds 2.x boards; updating it is
  TCW-74's (epic decision 14).
- **Other slices' documents.** The `upcoming/README.md` files, the README, the
  guides and `docs/lifecycle/{abstraction,implementation,harness}.md` are TCW-75's
  (TCW-75 Design 1.2); skills and built-in prompts are TCW-74's.

## Design

### 1. The guide's form

1. **One file,** `docs/migration-guide-2.8-to-3.0.0.md`, in the style of the
   earlier guides (`docs/migration-guide-1.X-to-2.0.0.md`): plain language, tables
   for mappings, a "Check for it" command where one exists.
2. **Written for an agent working with a user.** It opens with:
   - the prerequisites: the project is on 2.8.x; the 3.0 CLI is installed; the
     working tree has no uncommitted changes; no 2.x worktrees are open
     (`git worktree list` shows only the main one), because 3.0 no longer knows
     about them; a branch or tag marks the 2.x state so it can be returned to;
     every project the configuration declares (`connected-projects`) is present
     on this machine, because 3.0 stops with exit 5 when a declared project is
     missing (epic decision 4), which would mask the migration's own findings;
   - the rules: do the steps in order; after each, run its check and do not go on
     until it passes; stop at every **Stop and ask** point.
3. **Every step** has three parts: what to do, a **Check**, and where it applies a
   **Stop and ask**.
4. **[Decision] Checks are read-only shell commands with stated expected output**
   (`find`, `grep`, `ls`, `diff`), not the `tcw` CLI, until the final step. The
   same guide then works in this repository, where the CLI may not be driven
   mid-migration, and anywhere else, and no check depends on a command that only
   understands a fully migrated project. Examples the guide uses:
   - `find docs/work -mindepth 1 -maxdepth 1 -type d \( -name backlog -o -name active -o -name review -o -name blocked -o -name completed -o -name discarded \)`
     prints nothing once the store is flattened. `inbox/` is deliberately not in
     this list: it survives until step 8, and step 8 has its own check;
   - `find docs/work -name state.yaml` prints nothing once items are converted,
     and `find docs/work -name tracker.yaml` prints nothing once they are bound
     (Jira mode) or converted (filesystem mode);
   - `grep -nE 'TCW_(STATUS|TRANSITION|NODE_ROOT|RESOLUTION)\b' <hook files>`
     prints nothing once hooks are rewritten. **[Decision]** `<hook files>` is a
     fixed list, written into the approved plan at step 1: the configuration
     files (`tcw-config.yaml` and, where present, `tcw-config.local.yaml`), every
     file a `command:` or `generate:` binding in them runs, every file a `file:`
     binding in them names, and the agent guides (`AGENTS.md`, `CLAUDE.md`).
     It is never the whole repository: changelogs, release notes, finished items'
     documents, tests and the migration guide itself legitimately name the 2.x
     variables. For TCW today that list is `tcw-config.yaml`,
     `scripts/require_artifact.py`, `docs/guide/examples/commit-item-after-move.sh`
     (bound in Design 6.5), `docs/procedures/create-work.md`,
     `docs/lifecycle/*.md`, `docs/lifecycle/templates/*.md`, `CLAUDE.md` and
     `AGENTS.md`; of these only `scripts/require_artifact.py:12` names one now
     (`git grep` finds the names elsewhere in `docs/changelogs`,
     `docs/release-notes`, `docs/guide`, `docs/capabilities`, `docs/work`,
     `skills/work`, `tcw/work` and two test files, none of which is in scope).

   Paths are written relative to the project's configured work path, which
   defaults to `docs/work`.
5. **[Decision] Three kinds of stop, and only three:**
   - **The consolidated plan** (step 1): one question, covering every decision the
     migration needs, answered once.
   - **Changes the agent cannot make itself:** Jira administration (statuses,
     workflow, custom fields) when the agent lacks the access.
   - **A check that fails after one retry.** The agent reports what it expected,
     what it saw, and stops.

   **[Decision] A step interrupted partway** for a reason that is not a defect
   (a lost session, a Jira error such as a 5xx response or a timeout) is not a
   stop: the agent reruns the same step from its beginning. Every action in a
   step is written so that doing it again after it already took effect changes
   nothing: a folder already moved or renamed is skipped, a ticket that already
   exists is reused, a comment already posted is not posted again (Design 1.8).
   Only when the rerun's check fails as well does the general stop apply.
6. **Commits.** TCW never changes git state: it reads git (to find the
   repository root, for example) but never commits, stages or branches. The
   project may commit. The guide recommends one commit per step after its check
   passes, so a bad step can be reverted, and says so as the project's choice.
7. **[Decision] Jira writes are given as REST requests** (`curl` with the
   credentials named in the project's config), with the web UI and any Jira tool
   the agent has as equivalents. A REST call works under Claude and Codex alike, so
   no step depends on one harness's tools.
8. **[Decision] Every Jira write is safe to repeat, and Jira, not the log, says
   what was already done.** A migration that is abandoned and restarted (Design
   8.5), or a step rerun after an interruption (Design 1.5), meets its own
   earlier Jira changes, since reverting git does not undo them. So before each
   write the agent reads the ticket and skips the write when its effect is
   already there:
   - **creating a ticket:** the agent searches with
     `project = <KEY> AND reporter = currentUser() AND created >= "<start date>"`
     and compares summaries exactly; a match is the ticket an earlier run made,
     and is reused. `<start date>` is the date the first run began, written in
     the log at step 0 and kept unchanged across restarts. The reporter and date
     terms are what tell the migration's own ticket apart from someone else's
     with the same summary;
   - **posting a comment:** every comment the migration posts begins with a fixed
     first line naming its kind (for example `Carried over from TCW 2.x: verdict
     accepted`, or the discard reason). The agent reads the ticket's comments and
     skips the post when one by the same account already begins with that line;
   - **moving a ticket, or setting a field, label or link:** skipped when the
     ticket already has that status, value or link.

   **The migration log** is one file, named in the approved plan, recording the
   approved plan, every Jira write (ticket key and what changed) as it is made,
   and every amendment to the guide. For TCW it is TCW-76's 2.x `outcome.md`
   until step 7 moves it to `implement/round-1.md` (Design 8.6). It is committed
   with each step. **[Decision]** When a run is abandoned (Design 8.5.3), its
   branch is kept, not deleted, and the next run starts by copying the log
   forward under a heading `Run <N>`, so the record of every run survives. A log
   lost anyway costs only the record, because the reads above, not the log,
   decide whether a write is repeated.

### 2. The steps

The ticket's order, with two changes: a survey step comes first, so that the one
consolidated question can be asked before anything changes, and the Jira
compatibility check moves after the configuration is written, because it reads
that configuration.

0. **Prepare.** Check the prerequisites (Design 1.2). On the 2.8 CLI, `tcw
   validate` should be clean; anything it reports is fixed under 2.8 first, where
   the tools for it still exist. Find untracked item folders hidden by
   `.gitignore` (`git status --ignored -- docs/work`) and list them. Only then
   start the migration log (Design 1.8) with the start date and the commit the
   run starts from (`git rev-parse HEAD`), which for TCW is the freeze commit
   (Design 8.5). **Check:** before the log is started, `git status --porcelain`
   prints nothing and `git worktree list` prints one line; afterwards the log
   holds the start date and that commit.
   **[Decision, owner 2026-10-01]** For TCW, the list is shown at the survey and
   none of them is kept unless the owner names it (Design 3.1).
1. **Survey, then Stop and ask.** The agent reads the whole board and config
   (and in Jira mode the tickets) and presents one plan:
   - the backend, and which optional stages to enable;
   - in Jira mode, the status for each enabled stage, and which statuses,
     transitions and fields must be added;
   - each item's stage (Design 3.1), its converted fields, and every difference
     between disk and its ticket (Design 4);
   - tickets to create, items without a ticket that are kept or deleted, and
     request text to place (Design 4.4);
   - **[Decision] a prune list:** items and inbox entries whose subject 3.0
     removes (tracker sync, claims, `start` records, worktrees, retention,
     graveyard, the Definition of Done, `scaffold`, status directories), proposed
     for discarding or deleting rather than migrating. Migrating them would create
     tickets and folders for work that no longer applies;
   - the config rewrite (Design 3.5), the hook rewrites (Design 3.6), the
     capability-record edits (Design 3.7) and the project files to change
     (Design 3.8).

   The plan also fixes the list of `<hook files>` (Design 1.4) and the folders
   step 9's check skips.

   **Check:** the user's approval is recorded verbatim in the migration log under
   a heading `## Approved plan`; `grep -c '^## Approved plan' <log>` prints `1`.

   **TCW's prune list. [Decision, owner 2026-10-01]** Every candidate is
   discarded at the migration with the reason `subject removed by TCW 3.0
   (TCW-68)`:
   - the bound items TCW-33 (`scaffold`), TCW-10 (tracker workflow against
     `statuses`), TCW-40 (claim exclusivity), TCW-26 (mapped tracker fields) and
     TCW-54 (aggregating child boards in `tcw serve`): each ticket is moved to
     `Won't Do` with the reason as its comment (Design 4.3);
   - the four unbound tracker and start items
     `2026-09-21-two-tracker-create-runs-…`,
     `2026-09-22-let-a-leftover-start-record-…`,
     `2026-09-22-refuse-an-unconfigured-start-…` and
     `2026-09-24-give-a-strict-tracker-claim-…`;
   - five inbox entries, named one by one in the question the owner answered on
     2026-10-01: `2026-09-29-a-plain-binding-s-stuck-start-record-never-clears`,
     `2026-09-29-store-git-root-compared-by-text-with-node-paths` (it is about
     the 2.x store's own git root, `FsWorkStore.store_git_root`, which 3.0's
     stores do not keep: they change no git state and only read where the
     repository root is),
     `2026-09-30-a-detached-worktree-s-unbranched-commits-are-lost-at-teardown`,
     `2026-09-30-can-a-custom-merge-driver-make-already-integrated-pass-unmerged-work`
     and `2026-09-30-let-the-worktree-merge-back-wait-out-a-store-commit-s-index-lock`.
     The sixth entry in that question is closed as done, below.

   An unbound item or inbox entry has no ticket, and a Jira-mode item without one
   is not legal (TCW-71), so each pruned one is created as a ticket and moved
   straight to `Won't Do` with the reason as a comment (the "yes" route of
   Design 4.1, with discarded as the target stage). The discard is then recorded
   in Jira, where 3.0 reads it, and not only in git history.

   The inbox entry `2026-09-30-keep-an-item-s-folder-in-one-place-and-its-status-only-in-state-yaml`
   is not pruned but **closed as done by the epic** [Decision, owner
   2026-10-01]: 3.0 never moves a folder and has no `state.yaml`. It is created
   as a ticket and moved straight to `Done` with the comment `Delivered by the
   TCW 3.0 redesign (TCW-68)`.

   The other four inbox entries (`editing-a-damaged-item-gives-a-bare-yaml-error`,
   `tcw-validate-crashes-on-a-duplicate-slug`, `follow-renames-in-the-web-app-…`
   and `run-ci-on-python-3-12-or-3-13`) are migrated as ordinary inbox items;
   the survey notes that the first two describe 2.x code and may no longer
   reproduce, for the owner to decide then. Entries added to the board before the
   migration starts go through the survey like any other.
2. **Jira mode: prepare Jira.** Add one status per enabled stage that has none,
   the transitions `advance` needs, and the TCW Project, TCW Item, effort and
   complexity fields (TCW-71 defines their types). **Stop and ask** for anything the
   agent cannot do itself. **Check:** deferred to the end of step 3, since the
   check reads the new configuration.

   **For TCW, [Decision, owner 2026-10-01]** the owner does all of this Jira
   administration by hand, from a checklist the agent writes into the TCW-76
   implement round (Design 6.2, "The Jira checklist"). The agent makes no
   workflow, status or field change itself; it stops here until the owner says
   the checklist is done.
3. **Rewrite the configuration**, key by key (Design 3.5). **Check:**
   `grep -nE '^\s*(tracker|lifecycle|retain|auto-commit-transitions|publish-transitions|trunk-branch):|builtin: true' tcw-config.yaml`
   prints nothing. **[Decision]** In Jira mode the agent then builds a scratch
   folder outside the repository holding the new `tcw-config.yaml`, every file it
   binds at the same relative path, and empty folders at the configured work,
   taxonomy and capabilities paths, and runs `tcw validate --remote` there. That
   runs TCW-71's workflow compatibility check against the real Jira project
   without the half-migrated board's errors drowning it, and without using the
   CLI on the board. `validate --remote` prints findings only, one per line, and a
   move it could not check is itself a finding, a `warning` starting `unchecked:`
   (epic decision 10; TCW-71 Design 9). With no items, the checked issue type is
   the configured one (TCW-71 Design 9.2, item 6). The agent reads every line and
   acts only on the Jira-workflow findings: a move with two candidate transitions
   that `advance` could not choose between (epic decision 5) is fixed in Jira
   before going on; an unchecked move is listed for step 11. Any other finding
   there (for example one caused by the scratch folder not being a git
   repository) is noted in the log and left to step 11, which validates the real
   tree. This is also step 2's check: no Jira-workflow finding other than
   `unchecked:` remains.
4. **Flatten the store and give every item a stage.** Move each item folder up out
   of its status directory (and each nested child out of its parent's folder);
   write the stage (Design 3.1). Delete the status directories, their `.gitkeep`
   files, `graveyard.yaml` and `dod.yaml` (Design 3.4). **[Decision]** In Jira mode
   too, this step writes the full filesystem-form `item.yaml` (title, stage and
   properties). It is the "disk" side of reconciling in step 6, which then reduces
   it to the ticket link. One conversion procedure then serves both modes.
   **Check:** the status-directory `find` above prints nothing, and
   `for d in docs/work/*/; do [ "$d" = docs/work/inbox/ ] || [ -f "$d/item.yaml" ] || echo "$d"; done`
   prints nothing (`inbox/` is converted at step 8).
5. **Convert item fields** (Design 3.2) and delete `state.yaml`. In filesystem
   mode `tracker.yaml` is deleted too. **[Decision]** In Jira mode `tracker.yaml`
   stays until step 6, which reads the binding from it and then deletes it, so the
   ticket key is never held anywhere but the file 2.x wrote it in.
   **Check:** `find docs/work -name state.yaml` prints nothing (filesystem mode:
   the `tracker.yaml` `find` too); no `item.yaml` has an integer `priority`
   (`grep -nE '^priority: [0-9]' docs/work/*/item.yaml` prints nothing).
6. **Jira mode: bind** (Design 4): reconcile bound tickets with disk; create
   tickets for items and inbox entries that have none; set TCW Project and TCW
   Item; rename folders to `<KEY>-<title words>`; reduce each `item.yaml` to
   `ticket: <url>`; delete `tracker.yaml`. **Check:** the `tracker.yaml` `find`
   prints nothing; every folder name other than `inbox` matches
   `^<project key>-[0-9]+-[a-z0-9-]+$` (for TCW,
   `ls docs/work | grep -vxE 'inbox|TCW-[0-9]+-[a-z0-9-]+'` prints nothing),
   every `item.yaml` is the one `ticket:` line, and the key in that line equals
   the folder's prefix.
7. **Move documents** (Design 3.3). **Check:** no 2.x document name remains at an
   item root (`find docs/work -maxdepth 2 \( -name intake.md -o -name initial-request.md -o -name spec.md -o -name plan.md -o -name outcome.md -o -name refined-outcome.md -o -name rework.md -o -name post-mortem.md -o -name rollup.md \)`
   prints nothing); every verdict round has `verdict:` and `judges:` front matter.
8. **Convert the inbox.** Filesystem mode: each entry becomes an inbox-stage item
   as TCW-70 stores one. Jira mode: each entry's ticket was created in step 6; the
   file is deleted. **Check:** the `inbox/` folder is gone.
9. **Rewrite live references** (Design 3.9). **Check:** for every renamed folder,
   `grep -rn '<old folder name>'` over open items' documents and the project's
   live files prints nothing. **[Decision]** The search skips the migration log
   and every document of the item that runs the migration, if the project has
   one: they name the old folders on purpose, and the log is kept verbatim. For
   TCW that is TCW-76's whole folder. The skipped folders are named in the
   approved plan.
10. **Review the project's own files** (Design 3.8), and capability records
    (Design 3.7). The agent fixes what the approved plan covers and points out text
    that relies on removed behavior. **Check:** the variable `grep` of Design 1.4
    over the plan's `<hook files>` prints nothing, and
    `grep -rln '^Planning doc:' <capabilities path>` prints nothing.
11. **Validate.** `tcw validate` (and `tcw validate --remote` in Jira mode) exits 0.
    Each remaining warning or finding, including unchecked moves, is either fixed
    or listed for the user with its reason.

### 3. The mappings

#### 3.1 Status folder to stage

| 2.x folder | 3.0 stage |
| --- | --- |
| `inbox/` (loose `.md`) | filesystem: an item at `inbox`; Jira: a ticket in the inbox status, with no item |
| `backlog/` | the furthest of request, spec, plan whose document exists: `plan` if `plan.md`, else `spec` if `spec.md`, else `request` |
| `active/` | `implement` |
| `review/` | `qa` (2.x review was the requester's acceptance; Design 3.3) |
| `blocked/` | not a 2.8 status (`WORK_STATUSES`, `tcw/store/base.py:989`); a leftover from earlier versions. TCW's holds only a `.gitkeep`, added in commit `0b527e77`. It is deleted with the other status folders; an item found in one is listed in the plan and staged by the `backlog` rule, extended to `implement` when `outcome.md` exists |
| `completed/` | `completed` |
| `discarded/` (tracked or ignored) | `discarded`; the resolution (`wontfix`, `duplicate`, `superseded`) and any reason become a comment |

The rule picks a stage whose document is already written; a later stage would trip
TCW-69's "stage ahead of artifacts" warning (TCW-69 Design 9). When a stage the rule
picks is disabled in the new config, the item takes the next enabled flow stage.

**[Decision] Ignored discarded folders** (Problem 2.4) are listed in the
consolidated plan. Kept ones become tracked `discarded` items, since 3.0 no longer
has a folder to ignore; the `.gitignore` rule is removed in step 10. **[Decision,
owner 2026-10-01]** For TCW none is kept unless the owner names it at the survey;
the rest stay untracked on that machine and are never migrated.

#### 3.2 Item fields (`state.yaml` and `tracker.yaml` to `item.yaml`)

| 2.x | 3.0 |
| --- | --- |
| `slug` | dropped; the folder name is the identity |
| `title` | `title` (Jira: Summary) |
| `created` | dropped; the folder's date prefix (filesystem) or the ticket's creation date (Jira) |
| `priority` (integer) | **[Decision, from the ticket]** ≥ 40 `highest`, 30–39 `high`, 20–29 `medium`, 10–19 `low`, < 10 `lowest`. Missing: `medium` in filesystem mode; in Jira mode the ticket's priority stands (Design 4.2), and a Jira project without the Priority field has none, which 3.0 allows (`Item.priority` may be `None`, epic decision 16) |
| `effort`, `complexity` | carried over (the scale is the same four values) |
| `tags` | carried over (Jira: Labels) |
| `owner` | filesystem: `assignee`. Jira: dropped, because it is a git identity, not a Jira account; listed in the plan |
| `blocked_by` | `blocked-by` as full slugs (`<project>/<folder>`), using the folders' final names. A free-text blocker is dropped and listed, since 3.0 blockers are items (TCW-69 Design 2.4). Jira: a Blocks link; a link to a ticket that has no item shows as an untracked reference (`Item.untracked`, epic decision 16) |
| `parent` | `parent` as a full slug; for a child made before `parent` was recorded, the folder it was nested in (`fs.py:4792-4800`). Jira: the ticket's Parent, untracked when the parent ticket has no item |
| `initiative` | `parent`, as a full slug in the named project, when the item has no `parent`; if it has both, `parent` stays and the `initiative` is listed |
| `type` | dropped; an item with children is an epic (TCW-69 Design 2.6) |
| `resolution` | dropped; the stage says it (Design 3.1) |
| `started`, `completed`, `phase`, `worktree`, `branch` | dropped |
| `tracker.yaml` `ticket` | Jira: `ticket: <url>` in `item.yaml` |
| `tracker.yaml` `schema`, `provider`, `project`, `part`, `bound`, `unlinked`, `sync` | dropped when step 6 deletes the file, after binding (filesystem mode: at step 5); a `sync: pending` record is reported as "Jira lagged" in step 1 |

#### 3.3 Documents

| 2.x | Filesystem mode | Jira mode |
| --- | --- | --- |
| `intake.md`, `initial-request.md` | `request/request.md` | the ticket body (Design 4.4) |
| `spec.md` | `spec/spec.md` | same |
| `plan.md` | `plan/plan.md` | same |
| `outcome.md` | `implement/round-1.md`, no front matter | same |
| `rework.md` | `qa/round-N.md`, `verdict: rejected` | a ticket comment |
| `refined-outcome.md` | `qa/round-N.md`, `verdict: accepted` | a ticket comment |
| `post-mortem.md` | `postmortem/postmortem.md` | same |
| `capabilities.yaml` | stays at the item root; an `added:` key becomes `new:` | same |
| `rollup.md` | deleted (generated by the removed `reconcile`) | same |

- **When both request files exist**, **[Decision]** `initial-request.md` becomes
  the request, as 2.x reads it first (`BODY_ORDER`, `base.py:3109`), and
  `intake.md` is appended under an "Original intake" heading when its text is not
  already contained in the request. Nothing is lost.
- **[Decision] Acceptance history maps to `qa`, not `review`.** Reasons:
  - 2.x verify recorded the requester accepting or rejecting the finished work,
    which is what 3.0 qa is for ("product behavior verification: QA, product,
    requester", TCW-68 epic). 3.0 review is engineers checking the code against
    the spec and plan, which 2.x had no stage for.
  - Mapping to review would manufacture a code-review verdict that never happened,
    and would satisfy the completion gate's review check for in-flight items.
  - The decision record's reason for review ("no QA history exists before 3.0") is
    about naming; the ticket, which supersedes the record, chose qa.
- **Round numbers and `judges`.** `outcome.md` is the only implement round, so
  every converted verdict round has `judges: 1`. When both files exist, `rework.md`
  is round 1 and `refined-outcome.md` round 2, since a rejection precedes the
  acceptance that ends the item.
- **Jira mode keeps no qa files** (qa is an external stage, TCW-69 Design 4.12).
  Each verdict becomes a ticket comment, posted oldest first, beginning with a line
  that names the verdict and says it was carried over from 2.x.
- **Consequence for in-flight items:** an item mapped to `qa` with review enabled
  has no review round, so the completion gate will refuse it until a review round
  is written or the move is forced with a reason. The plan says so for each such
  item. (TCW's board has none today: `review/` is empty.)
- **Relative links** inside moved documents keep working when they point outside
  the work folder, because the removed status-folder level is replaced by the new
  stage-folder level. Links between documents of one item (`plan.md` →
  `../plan/plan.md`) and links into other items are rewritten in open items only
  (Design 3.9).

#### 3.4 Store-root files

| 2.x | 3.0 |
| --- | --- |
| status directories and their `.gitkeep` | deleted |
| `graveyard.yaml` | deleted; git history keeps it |
| `dod.yaml` | deleted; its entries are mapped as in Design 6.3 |
| `inbox/` | deleted after step 8 |

#### 3.5 Configuration

The guide's table covers every key 2.x accepts; the target names follow the sibling
specs (TCW-69 for `work.*`, TCW-71 for `work.jira`, TCW-72 for `inherit`, TCW-73
for renamed project keys).

| 2.x | 3.0 |
| --- | --- |
| `work.lifecycle.stages.<stage>` | `work.stages.<stage>`; `verify` becomes `qa` (and the agent asks whether its bindings also belong to `review`); a bare-list stage entry becomes its `prompt:`, with a `command` entry in it becoming `generate` (2.x accepted `command` there, `base.py:1178`, `:2692-2698`) |
| `builtin: true` | `inherit: true` (TCW-72) |
| `work.lifecycle.transitions.start` | `work.stages.implement` `pre`/`post` |
| `…transitions.submit` | the first enabled stage after implement (review if enabled, else qa); a submit hook guards "implementation is finished", which is what entering it means |
| `…transitions.rework` | `work.stages.implement`; merged with start's list. A hook that must run for only one of them tests `TCW_FROM_STAGE` itself, since `when:` has no source-stage condition |
| `…transitions.complete` | `work.stages.completed` |
| `…transitions.discard` | `work.stages.discarded` |
| `…transitions.auto-delete` | removed, since 3.0 never deletes; its hooks are listed in the plan |
| `pre`/`post` on `postmortem` | removed (a side stage takes neither, TCW-69 Design 8, check 3); listed |
| `work.lifecycle.timeout`, `output-cap` | `work.hooks.timeout`, `work.hooks.output-cap` |
| `work.lifecycle.artifacts.<doc>` | `file` entries with their `when:` in that stage's `prompt` list. Because prompts are cumulative (Problem 2.2), each later entry must stay silent wherever an earlier one matched. 2.x `tags` means "has any of these" and `not_tags` "has none of these" (`tcw/store/base.py:1203-1207`), and 3.0 keeps both meanings (TCW-69 Design 8). So **when every earlier entry's condition is `tags` alone**, its tags are added to each later entry's `not_tags`, and the same single template applies as before. **[Decision]** Any other shape (an earlier entry with `not_tags`, or with both keys) has an "or" as its negation, which one `when:` cannot say; the agent lists the list in the plan with a proposed rewrite (for example, adding a tag to the affected items), and the user chooses. A `builtin` fallback entry is dropped, since `inherit: true` already supplies the built-in text |
| a `skill` binding in `pre` | an error in 3.0: moved to `post` (reported, not run) or to prompt text, as the user chooses |
| `when: {type: …}` | an error in 3.0: removed; an epic condition becomes a tag the user adds to the epics |
| `work.tracker.provider` | `work.backend: jira` |
| `work.tracker.base-url` | `work.jira.site` |
| `work.tracker.credentials.*` | `work.jira.credentials.*` (same variable names) |
| `work.tracker.statuses.<status>` | `work.stages.<stage>.status`: `backlog` → `request`, `active` → `implement`, `review` → see Design 6.2, `completed` → `completed`, `discarded` → `discarded`. spec, plan, qa and any newly enabled stage need new statuses |
| `work.tracker.pre-backlog` | `work.stages.inbox.status` (its key); its transition name is dropped |
| `work.tracker.inbox-query` | dropped when it only selects the inbox status of the configured project, which the default inbox does; otherwise `work.jira.inbox-query` |
| `work.tracker.candidate-query` | removed; "what can I pick up" is `tcw work list --stage request --mine` |
| `work.tracker.transitions.*`, `strict`, `exclusive-claim-transition` | removed: `advance` finds the transition by its destination status; when several lead there it takes the one whose screen asks for nothing but a comment, and refuses with exit 3, listing them, when that still leaves more than one (epic decision 5). Claims are gone. A 2.x `transitions` entry that existed to pick between two routes into one status is a sign the workflow needs that fix; the plan lists it |
| `work.tracker.create.project` | `work.jira.project` |
| `work.tracker.timeout-seconds` | `work.jira.timeout` (seconds; default 15, the same as 2.x, TCW-71 Design 1) |
| `work.tracker.create.issue-type` | `work.jira.issue-type`, the type of a new top-level ticket (default `Task`, TCW-71 Design 1) |
| `work.tracker.create.issue-types` (`epic`, `bug`), `create.components`, `create.on-new`, `comments`, `link` | **[Decision]** removed, as TCW-71's key list has none of them (TCW-71 Design 1). What replaces each: a child's type follows its parent's hierarchy level (TCW-71 Design 11.2), and bug is a tag; components are not set by TCW, so a project that relied on them sets them in Jira (listed in the plan); `on-new` is the only behavior in Jira mode, since `tcw work new` always creates the ticket; a move's note always travels with its transition as a comment (TCW-69 Design 5.2), so `comments: true` has nothing left to turn on; `link` gives way to the TCW Item field, which names the item on every ticket |
| `work.retain` | removed. 3.0 never deletes; a project that prunes does it itself |
| `work.auto-commit-transitions`, `work.publish-transitions` (set or defaulted, Problem 2.3) | removed; the project adopts TCW-75's opt-in git example if it wants commits |
| `work.trunk-branch` | removed |
| `work.tags`, `work.documentation`, `work.path`, `work.repository` | kept; `documentation` entries are reviewed for 2.x wording |
| `work.procedures.<id>` | kept for procedures TCW-74 keeps (TCW-74 Design 5.1: `documentation-sync`, `create-work`, `audit-backlog`, `search`, `triage-issues` and `unattended-work` survive, all but the first rewritten, and `pause-work` is new; `post-mortem`, `consolidate-plans`, `decompose` and `delegation` are deleted); a binding for a procedure TCW-74 deletes is removed and its text reviewed |
| `connected-projects` | `projects`, with the same `parent`, `children` and `upstream` entries (TCW-73 Design 9.3; **[Decision, owner 2026-10-01]** the name `projects` is settled). The Feature `connected-project-registry` becomes `project-registry` (TCW-73), so a project whose own capability records or taxonomy link to that Feature renames the link. The other renamed commands and flags, such as `tcw work nodes`, `provision --refresh` and `validate --no-recurse`, come from TCW-73's old-to-new command table (TCW-73 Design 2), which the guide copies |

#### 3.6 Hook variables

**Mapped by meaning, not by position** (Problem 2.1; confirmed as epic decision
11). Hooks and `generate` scripts still run with the project root as their working
directory (epic decision 11), so a relative path in a hook command keeps working.

| 2.x | 3.0 |
| --- | --- |
| `TCW_SLUG` (a bare folder name, `cli.py:1616`) | `TCW_SLUG`, now the full slug `<project>/<folder>` (epic decision 11; TCW-69 Design 6.5). The name is unchanged, so the variable `grep` cannot find it: the guide has the agent search hook scripts for `TCW_SLUG` and list each use that treats it as a folder name, which switches to `TCW_ITEM_PATH` or passes the slug to `tcw` as it is |
| `TCW_STATUS` in a transition's `pre` hook (the source status) | `TCW_FROM_STAGE` |
| `TCW_STATUS` in a transition's `post` hook (the destination status) | `TCW_STAGE` |
| `TCW_STATUS` in a stage's `pre` hook run by `tcw work stage gate` (the item's current status, `hook_env(…, slug, status, step.id)` at `tcw/work/cli.py:1993-1994`) | `TCW_FROM_STAGE`: in 3.0 the stage's `pre` hook runs when the item is advanced into that stage, from wherever it is |
| `TCW_TRANSITION` (`start`, `submit`, `complete`, `rework`, `discard`, `auto-delete`, or a stage name) | `TCW_STAGE`, compared against the target stage's name instead of the move's |
| `TCW_NODE_ROOT` | `TCW_PROJECT_ROOT` |
| `TCW_RESOLUTION` | removed: `TCW_STAGE` is `completed` or `discarded`, and the reason is in `TCW_REASON` |
| `TCW_ITEM_PATH` | `TCW_ITEM_PATH`; the folder no longer moves, so it is the same before and after |
| (none) | new: `TCW_FORCED` and `TCW_REASON` on forced moves |
| `TCW_HOOK_ROLE`, `TCW_HOOK_KIND`, `TCW_HOOK_ID`, `TCW_HOOK_PHASE` (`generate` bindings, `resolve.py:191-196`) | unchanged (TCW-69 Design 8). A `generate` script also gets the 3.0 hook variables, with `TCW_STAGE` set to the stage whose prompt is being composed and no `TCW_FROM_STAGE` |
| the JSON a `generate` script reads on stdin (`resolve.py:183-196`) | one object, `{"schema": 1, "item": <TCW-70 item record>, "request": <text or null>, "hook": {"role", "kind", "id", "phase", "body_truncated"}}`; a script that read 2.x fields such as the status or the artifact map reads `item` and `request` instead. `{{tcw:body}}` in prompt text becomes `{{tcw:request}}` (cross-slice decision R13) |

**[Decision] Status values inside comparisons are translated per hook, by the
3.0 stage the hook ends up bound to** (Design 3.5), not by one global table,
because a hook moved to a new stage sees new values:

- a value compared with `TCW_STAGE` becomes the stage the hook is now bound to
  when the 2.x test was "this move's destination". A former `submit` `post` hook
  testing `$TCW_STATUS = review`, moved to `stages.review`, tests
  `$TCW_STAGE = review`, not `qa`; moved to `stages.qa` (review disabled), it
  tests `qa`;
- a value compared with `TCW_FROM_STAGE` becomes the set of stages an item can
  come from in the new configuration. A start `pre` hook testing `= backlog`
  (`cli.py:1616`) tests membership of the enabled stages before implement (for
  TCW, `request`, `spec` or `plan`), since a forced skip can enter implement
  from any of them;
- the other 2.x statuses translate by Design 3.1 (`active` → `implement`,
  `completed` and `discarded` unchanged);
- a test that becomes always true or always false after the move (for example a
  `rework` hook testing `TCW_TRANSITION = rework` once merged into implement,
  Design 3.5) is rewritten to test `TCW_FROM_STAGE`, or removed, and listed in
  the plan.

#### 3.7 Capability records

- **`Planning doc` is removed** (epic decision 9: TCW-73 removes the field from
  `CAP_FIELDS` and the capabilities commands, and this slice removes it from the
  records). It was the capability-to-work pointer that 2.x drift followed
  (`tcw/capabilities/cli.py:200-222`). 3.0 drift reads completed items'
  declarations instead (TCW-69 Design 7; TCW-70 Design 10.3), TCW-74 drops
  planning-doc pointers from the capabilities skill, and TCW-77 drops the field
  from the viewer. Its values are 2.x slugs, most naming items that are now only
  `graveyard.yaml` entries, which this migration deletes, so they would point at
  nothing. Keeping it as free text would leave 65 dangling pointers that nothing
  reads. The vocabulary check rejects fields not in `CAP_FIELDS`
  (`fs.py:3530-3532`), so once TCW-73 removes the field from `CAP_FIELDS`
  (`base.py:844-847`), records that keep it fail `tcw validate`. The guide removes
  the line from every record. Between TCW-73 landing and this slice, TCW's own 65
  records carry a field the working-tree CLI rejects; that is harmless, because the
  working-tree CLI already refuses this repository's 2.x configuration then
  (TCW-70 Design 8), but no test may validate this repository's ledger in that
  window.
- `Tracker` goes the same way, for the same reason (TCW-77: work items point at
  capabilities, not the other way).
- Existing `Missing` records are left alone: each is a true statement of a known
  gap. An in-flight item whose 2.x plan seeded one still has to make it
  `Supported` (or remove it) before review, which the records gate enforces.

#### 3.8 The project's own files

The guide tells the agent to search for, and list in the plan:

- hook scripts and commands bound in config: the variables in Design 3.6
  (including every use of `TCW_SLUG`), 2.x status names, and calls to removed or
  renamed commands (`start`, `submit`, `rework`, `complete`, `drop`, `stage gate`,
  `inbox`, `tracker`, `reconcile`, `scaffold`, `delete`, `tombstone`, and the rest
  of TCW-73's old-to-new table);
- prompt and procedure files bound in config, and the agent guides (`AGENTS.md`,
  `CLAUDE.md`): text that relies on removed behavior (status folders,
  `state.yaml`, the Definition of Done, `refined-outcome.md`, claims, retention,
  automatic commits);
- `.gitignore`: rules naming status folders are removed; **[Decision]** the line
  `/tcw-config.local.yaml` is added, in the form TCW-72's `tcw init` writes for new
  projects (TCW-72 Design 10.2), because `init` does it only for new ones;
- identity: `TCW_WORK_OWNER` and the git-identity fallback are gone (TCW-72), so a
  filesystem-mode user sets `user.name` in personal configuration.

#### 3.9 Live references

Rewritten: `parent` and `blocked-by` (filesystem mode, in `item.yaml`; Jira mode,
as Parent and Blocks links) and mentions of renamed folders in **open** items'
documents, the project's config, and its live documents. Left alone: completed
and discarded items' documents, changelogs and release notes. A `tcw://work/<old
slug>` reference in live text is rewritten to the new slug.

### 4. Jira mode: binding and reconciling

1. **Every item needs a ticket.** For an item without one, the plan offers:
   - **yes:** the agent creates it in the Jira project, with the summary from
     `title`, the body by Design 4.4, and the status of the item's stage;
     completed items are created and then moved straight to the completed status.
     These are REST writes (Design 1.7), not `tcw work new`: TCW creates a ticket
     at the inbox status and moves it one transition at a time (TCW-71 Notes), and
     the folder already exists. A ticket is created at the project's default
     status and moved with one transition into the target status, which the
     global transitions of Design 6.2 provide;
   - **no:** the folder is deleted (git history keeps it), since a Jira-mode item
     without a ticket is not legal (TCW-71).
2. **Reconciling disk with the ticket.** Disk wins where they disagree, since 2.x
   treated disk as the source (ticket). **[Decision]** Three refinements:
   - an absent or empty value on disk is not a disagreement: the ticket's
     priority, labels or assignee stand. Otherwise "disk wins" would reset every
     ticket priority to medium for the 16 TCW items that have none on disk;
   - a title that differs only by a leading `<KEY> — ` prefix is not a
     disagreement; TCW's imported items carry that prefix (`state.yaml` of
     TCW-69: `title: 'TCW-69 — Core work model: …'`), and the prefix is dropped;
   - labels on the ticket that disk does not have are listed, and removed only
     when the user agrees in the plan.

   Every difference, and every `sync: pending` record (Jira lagged), is shown in
   the consolidated plan.
3. **Status moves made by the migration carry no comment.** They are bookkeeping,
   not lifecycle moves. Discard reasons do become comments (Design 3.1).
4. **The request in Jira mode.**
   - An `intake.md` whose text the ticket body already contains (ignoring the
     "Imported on … from [KEY]" line and whitespace) is deleted without asking.
   - **[Decision]** Other request text goes to the ticket body when the body is
     empty. When the body has text, it is posted as a comment headed "Request as
     written in the repository before 3.0", and the body is left as it is: Jira
     owns the body, and someone outside engineering may have written it. The plan
     offers "replace" or "append" instead, per ticket.
   - Every comment's exact text is shown in the plan before anything is posted, as
     `CLAUDE.md` requires.
5. **TCW Project and TCW Item** are set on every ticket that has an item, and TCW
   Project alone on the redesign's tickets that have none (TCW-67). TCW Item is the
   full slug, `tcw/<folder>`, using the renamed folder.
6. **Folder names** become `<KEY>-<title words>`, with the title words computed
   from the ticket's summary by TCW-69's rule (Design 1.3 there).
7. **Tickets without items.** Tickets in the project that no item is bound to, and
   that are not at the inbox, completed or discarded statuses, are listed. In 3.0
   they appear in no list, since the default inbox shows only the inbox status
   (TCW-71); one linked as an item's parent or blocker shows only as an untracked
   reference in that item's `show` (epic decision 16). The user chooses per
   ticket: move to the inbox status, or leave.

### 5. Proving the guide

1. **TCW's own Jira-mode migration** (Design 6 to 8) follows the guide as written.
   Where the guide is wrong or unclear, the guide is fixed first, then the step is
   redone from the fixed text. Every amendment is recorded in the implement round.
2. **[Decision] A filesystem-mode rehearsal** on a disposable project built with
   the released 2.8 CLI in a scratch folder and environment. TCW's board has no
   items in `active`, `review` or `discarded`, no nested children, `initiative`,
   `rework.md`, `post-mortem.md`, connected projects, transition bindings other
   than `complete`, or `timeout`, so the Jira migration alone leaves most of the
   guide unexercised. The rehearsal project has at least one of each, plus an
   unconditional `artifacts` template after a conditional one, a legacy
   bare-list stage, a hook comparing `TCW_STATUS` with a status name, and a
   leftover `blocked/` folder holding one item. 2.8 cannot create a nested child
   (it records `parent:` instead, `tcw/store/fs.py:4792-4800`) or a `blocked/`
   folder (`base.py:989`), so **[Decision]** those two are placed by hand after
   the 2.8 commands, as earlier versions left them. The guide is followed in
   filesystem mode and ends with `tcw validate` clean. The 2.8 commands and the
   hand placements used to build it are recorded in the implement round so it can
   be rebuilt; nothing of it is committed.
3. **Every `tcw` command the guide names exists in 3.0.** Migration guides are
   exempt from `tests/test_documented_cli_surface.py` (`:37-47`), so this is
   checked by hand: each command's `--help` exits 0.

### 6. TCW's own 3.0 configuration

#### 6.1 Shape

Key names under `work.jira` follow TCW-71's sketch and change with its spec.

```yaml
id: tcw
work:
  backend: jira
  jira:
    site: https://proposit.atlassian.net
    project: TCW
    credentials: {email-env: TCW_JIRA_EMAIL, token-env: TCW_JIRA_API_KEY}
    fields: {project: TCW Project, item: TCW Item, effort: Effort, complexity: Complexity}
    priorities: {highest: Highest, high: High, medium: Medium, low: Low, lowest: Lowest}
  tags: [bug, capabilities, cli, docs, remote, skills, store, taxonomy, tech-debt, web, work]
  documentation: [...]        # Design 6.4
  procedures:
    create-work:              # if TCW-74 keeps the procedure
    - inherit: true
    - file: docs/procedures/create-work.md
  stages:
    inbox:     {status: Triage}
    request:   {status: To Do, prompt: [...], post: [...]}
    spec:
      status: Specifying
      prompt:
      - inherit: true
      - file: docs/lifecycle/abstraction.md
      - file: docs/lifecycle/harness.md
      - file: docs/lifecycle/templates/spec-bug.md
        when: {tags: [bug]}
      - file: docs/lifecycle/templates/spec.md
        when: {not_tags: [bug]}
      post: [...]
    plan:
      status: Planning
      pre:    [{command: python scripts/require_artifact.py spec}]
      prompt: [{inherit: true}, {file: docs/lifecycle/abstraction.md}]
      post: [...]
    implement:
      status: In Progress
      pre:
      - command: python scripts/require_artifact.py spec
      - command: python scripts/require_artifact.py plan
      prompt: [{inherit: true}, {file: docs/lifecycle/implementation.md}, {file: docs/lifecycle/harness.md}]
      post: [...]
    review:    {status: In Review, prompt: [{inherit: true}, {file: docs/lifecycle/review.md}], post: [...]}
    qa:        {status: In QA, post: [...]}
    completed: {status: Done, pre: [{command: tcw validate}], post: [...]}
    discarded: {status: "Won't Do", post: [...]}
```

`prompt: [...]` and `post: [...]` stand for the git example in Design 6.5. In every
stage that shows a prompt list, the example's pull `blob` is added at the head of
that list, and the list keeps its single `inherit: true`, since TCW-72 refuses a
second one in one list (TCW-72 Design 3.5). `postmortem` takes the pull prompt and
no `post` (TCW-69 Design 8).

#### 6.2 Stages and statuses

- **[Decision, owner 2026-10-01] Every optional stage is enabled** (spec, plan,
  review, qa, postmortem). The repository already works spec and plan for every item, runs
  code reviews, and has the owner accept the result, which are review and qa.
- **[Decision, owner 2026-10-01] Statuses:** inbox `Triage`, request `To Do`, implement
  `In Progress`, completed `Done` and discarded `Won't Do` keep the statuses 2.x
  mapped to them (`tcw-config.yaml:14-21`, statuses and `pre-backlog`). `In Review` maps to 3.0 **review**,
  which its name describes; 2.x `review` items move to the new qa status. Three new
  statuses: `Specifying`, `Planning` (TCW-71's sketch uses `Specifying`) and
  `In QA`.
- **[Decision, owner 2026-10-01] A global transition into each mapped status.** When several
  transitions lead to the target's status, `advance` takes the one whose screen
  asks for nothing but a comment, and refuses with exit 3 only when that still
  leaves more than one, or none (epic decision 5; TCW-71 Design 5). TCW's workflow
  therefore gets one global transition (a Jira transition that every status can
  take) into each mapped status, with no screen fields, so that every needed move
  and every forced skip has a route. A global transition and an older transition
  into the same status, both without screen fields, would be two equal candidates
  and `advance` would refuse, so the older ones are removed, leaving exactly one
  transition into each mapped status. The compatibility check (Design 2, step 3)
  confirms no move is left with two candidates.
- **The live workflow, read on 2026-10-02** (REST GET of the `TCW work`
  workflow, the only one in the `TCW work scheme`, which every issue type,
  Epic included, uses). It has these transitions, none with a screen:

  | Transition | From | To |
  | --- | --- | --- |
  | `Create` | (initial) | `Triage` |
  | `Accept` | `Triage` | `To Do` |
  | `Start` | `To Do` | `In Progress` |
  | `Submit` | `In Progress` | `In Review` |
  | `Complete` | `In Progress`, `In Review` | `Done` |
  | `Rework` | `In Review` | `In Progress` |
  | `Cancel` | `Triage`, `To Do`, `In Progress`, `In Review` | `Won't Do` |
  | `Stop` | `In Progress`, `In Review` | `To Do` |
  | `Reopen` | `Done`, `Won't Do` | `To Do` |

  So removing only `Start` and `Accept` (named in 2.x's config,
  `tcw-config.yaml:12-13`, `:20-21`) is not enough: `Submit`, `Complete`,
  `Rework`, `Cancel`, `Stop` and `Reopen` would each tie with the new global
  transition into the same status, and `advance` would refuse those moves with
  exit 3. **[Decision]** Every directed transition into a mapped status is
  removed, all eight of the table's rows after `Create`, which is the
  ticket-creation step and not a move. This carries out the owner's stated aim,
  "one global transition per mapped status" (owner answer of 2026-10-01), which
  naming only `Start` and `Accept` would not achieve; the owner confirms it at
  the checklist (Notes, "Questions only the owner can answer").
- **From step 2 on, the released 2.8 CLI can no longer move TCW tickets** the
  way 2.x expects (its `start` names `Start`, and its other moves find the
  route by target status, which the global transitions change). That is
  harmless during the migration, because `main`'s board is frozen from Design
  8.5.2 onwards and the epic board is moved by hand (epic decision 7). It does
  matter if the migration is abandoned for good: the Jira changes would then
  have to be undone by hand, which the risk of shared Jira changes (Risks)
  already covers.
- **The Jira checklist. [Decision, owner 2026-10-01]** The owner makes the Jira
  changes by hand (Design 2, step 2). The agent writes the checklist into the
  TCW-76 implement round before the migration's step 2, one line per change, each
  with how to confirm it was made:
  - add the statuses `Specifying`, `Planning` and `In QA` to the TCW workflow;
  - add one global transition, with no screen fields, into each of `Triage`,
    `To Do`, `Specifying`, `Planning`, `In Progress`, `In Review`, `In QA`,
    `Done` and `Won't Do`;
  - remove the transitions `Accept`, `Start`, `Submit`, `Complete`, `Rework`,
    `Cancel`, `Stop` and `Reopen`, keeping `Create`; before writing the
    checklist the agent reads the workflow again (a REST GET) and lists by name
    every transition into a mapped status other than the new global ones, in case
    it changed since 2026-10-02;
  - create whichever of the TCW Project, TCW Item, Effort and Complexity fields
    do not exist yet, with the types TCW-71 defines, and add them to the TCW
    project's screens;
  - if any issue type has come to use a workflow other than `TCW work` by then
    (on 2026-10-02 none does), make the same status and transition changes
    there.

  Only the `TCW` project is in the checklist. TCW-71's live tests run against the
  separate `TCWTEST` project, which TCW-71 prepares and keeps using (owner answer
  of 2026-10-01); nothing here changes it.

#### 6.3 The Definition of Done becomes a gate and prompt text

**[Decision, owner 2026-10-01]** Each `dod.yaml` entry (`docs/work/dod.yaml`)
goes where 3.0 can enforce or state it:

| `dod.yaml` entry | 3.0 |
| --- | --- |
| reviewed | the built-in completion gate (an accepted, current review verdict) |
| capabilities reconciled | the built-in records gate after implement |
| tests pass, docs synced | a new prompt file `docs/lifecycle/review.md` bound to the review stage: run the suite as CI does, and run the documentation-sync evaluation, before writing an accepted verdict. The suite runs far longer than the 300-second hook limit, and documentation-sync is a skill, which `pre` cannot run, so neither can be a gate |
| originating GitHub issue answered and closed | unchanged in substance in `CLAUDE.md`, which already defers it until publication; the deferral is recorded in the qa acceptance instead of `refined-outcome.md` |

**The project-defined gate** is `completed.pre: tcw validate`, carried over from
`transitions.complete.pre` (`tcw-config.yaml:111-114`): nothing completes while the
project does not validate. The built-in gates do not run `validate`, so this is a
real project addition, and it is the demonstration the ticket asks for.

#### 6.4 Documentation entries

- **[Decision] `Tracker-Change` becomes `Jira-Change`**, described as: update
  `docs/guide/jira.md` when what a `tcw work` command does to a ticket, a
  `work.jira` key, a stage's `status`, or `tickets list|adopt` changes. The
  `Guide-Topic-Change` description's mention of it is updated. No other trigger is
  renamed; their meanings survive 3.0.
- `docs/release-notes/upcoming/<slug>.md` and `docs/changelogs/upcoming/<slug>.md`
  become `…/upcoming/<folder>.md`: named by the item's folder name, never the full
  slug, whose `/` would make a subfolder (TCW-75). `CLAUDE.md:150` changes to
  match; both `upcoming/README.md` files are TCW-75's, which makes the same change
  (TCW-75 Design 10.5). Entry files already written under 2.x names keep them;
  `scripts/cut_version.py` merges files whatever their names.
- The `Configuration-Key-Change` description drops `docs/work/dod.yaml`.

#### 6.5 The git example

TCW adopts TCW-75's opt-in example as TCW-75 writes it (TCW-75 Design 8):

- pulling is prompt text: the example's `blob` asking for `git pull --ff-only`,
  at the head of every stage's `prompt` list;
- committing is a `post` hook on every stage an item can be moved into (request to
  discarded). **[Decision, owner 2026-10-01]** TCW binds TCW-75's script where it is,
  `command: sh docs/guide/examples/commit-item-after-move.sh`, rather than
  copying it into `scripts/`, so the example TCW documents is the one it runs. The
  script works from `TCW_ITEM_PATH`, commits only the item's folder, and succeeds
  when there is nothing to commit, as is usual in Jira mode where a move changes no
  file;
- **[Decision, owner 2026-10-01] No push hook.** The owner pushes, as today
  (`CLAUDE.md:150`: publishing stays a human step). TCW-75's optional push entry
  is left out; the owner can add it later without any other change.

### 7. TCW's own files

| File | Change |
| --- | --- |
| `tcw-config.yaml` | Design 6 |
| `scripts/require_artifact.py` | asks `tcw work path "$TCW_SLUG" <stage>` for the document's path and fails unless that file exists and is not empty. `TCW_SLUG` is the full slug (epic decision 11), which `tcw work path` accepts as it is, and the hook runs from the project root, so `python scripts/require_artifact.py` keeps resolving. It keeps failing closed when `TCW_SLUG` is unset or `tcw` fails. `path` is the shared layout in both modes, so the check still composes no path itself, which was the script's reason for asking the CLI (`:9-13`). The `TCW_NODE_ROOT` mention goes |
| `docs/lifecycle/templates/spec.md`, `spec-bug.md` | each gains a first line saying it is the outline for `spec/spec.md`, since it is now read as prompt text rather than copied in as a skeleton |
| `docs/lifecycle/review.md` | new (Design 6.3) |
| `tests/test_repo_lifecycle.py` | TCW-70 deletes the 2.x file with the parser it guards (TCW-70 Design 15.1); this slice writes it again against the 3.0 parser: the config parses with no problems; every bound file exists and is not empty; plan binds no template; both templates carry the spec's seven required headings; the documentation entries and triggers are as in Design 6.4. The check that the moved rules are reachable (today `:76-83`) is not rewritten here: TCW-75 moves its four phrases into `tests/test_docs_describe_3_0.py` (TCW-75 Design 11). The old test comparing the template with `tcw.work.templates._SPEC` is not restored: TCW-70 deletes that module (epic decision 13), and in 3.0 the template adds to the built-in text instead of replacing it |
| `CLAUDE.md` and `AGENTS.md` (kept identical) | "Work Planning and Implementation" (lines 11-51) rewritten for 3.0: `advance --dry-run` instead of `stage gate`; the bindings table gains review and completed; the exception rewritten (Design 8.6); the GitHub-issue paragraph without `dod.yaml` and `refined-outcome.md`; it says when TCW's own process advances an item to implement, which TCW-75 removes from `implementation.md` (TCW-75 Design 7.2). Versioning (line 150): `upcoming/<work-item-folder>.md`. The `--worktree` section is TCW-75's |
| `docs/procedures/create-work.md` | made consistent with TCW-74's rewritten `create-work` procedure (TCW-74 Design 5.1); step-number references fixed |
| `.gitignore` | `docs/work/discarded/*` and its exception removed; `/tcw-config.local.yaml` added |
| `docs/capabilities/**/meta.yaml` | `Planning doc:` lines removed (65 files) |
| `docs/release-notes/upcoming/`, `docs/changelogs/upcoming/` | this item's entries, named by this item's folder name and linking the guide, with all their text under `##` headings: only TCW-75's entry carries the 3.0.0 introduction before its first `##` (epic decision 15). The README files are TCW-75's (Design 6.4) |
| the documented-surface allowance (the module TCW-70 creates for `tests/test_documented_cli_surface.py`, TCW-70 Design 14) | both its lists, removed commands and refused configuration keys, are empty when this slice ends, so 3.0.0 is never cut with them (epic decision 6). TCW-71 and TCW-73 add to it and TCW-74 and TCW-75 shrink it; if an entry remains, the document that still names the removed thing belongs to another slice, so this slice reports it and that slice fixes it on the epic branch before the migration restarts (Design 8.5.3). **[Decision]** Once both lists are empty, the module and its guard test are deleted, so nothing can be added to it after 3.0.0 |
| TCW-75's link-resolution test (`tests/test_docs_describe_3_0.py`) | the constant that exempts `docs/migration-guide-2.8-to-3.0.0.md` from link resolution is removed once the guide exists (TCW-75 Design 11 and its criterion 3) |

### 8. Sequencing: how this epic's board is tracked until the migration

1. **Until TCW-70 lands,** the 2.x CLI works and may be used as usual. (TCW-69
   changes no command.)
2. **From TCW-70 onwards,** on the epic branch:
   - **the board stays in 2.x form and is changed by hand** (epic decision 7), as
     `CLAUDE.md:29-41` requires: folders moved between status directories,
     `state.yaml` edited, documents written;
   - **read-only commands may use a released 2.8 `tcw` outside the checkout**
     (epic decision 7), for example in an isolated environment, run against the
     epic branch's files. Reading prompts (`stage prompt`), `list`, `show` and
     `validate` is not driving the lifecycle, and that CLI is not under
     modification. No moves are made with it;
   - **each slice's Jira ticket is moved by hand when its item moves** (epic
     decision 7): to `In Progress` when it starts, `In Review` when it is
     submitted, `Done` when it completes. Step 6 still reconciles any that lag,
     disk winning.
3. **[Decision] Completed epic items are kept** in `completed/` despite
   `retain: {completed: false}` (`tcw-config.yaml:77-78`), so their documents and
   `capabilities.yaml` reach 3.0. They are the first completed items 3.0 drift can
   read.
4. **The repository's `tcw-config.yaml` stays in 2.x form until this slice.** From
   TCW-70 the 3.0 code rejects it, so no test may load it in the meantime. TCW-70
   deletes `tests/test_repo_lifecycle.py` and the `self` case of
   `tests/test_lifecycle_baseline.py` for that reason (TCW-70 Design 15.1); this
   slice writes the 3.0 replacement (Design 7).
5. **The migration itself:**
   1. starts when TCW-69 to TCW-75 and TCW-77 are complete (moved to `completed/`
      by hand). The slices land in the order 69 → 70 → 71 → 73 → 72 → {74, 77
      in parallel} → 75 → 76 (cross-slice decision R1), so this slice is last and
      relies on everything the others build. "Code frozen" means no further
      change under `tcw/`, `skills/`, `agents/` or `web/` until the epic merges.
      **The freeze commit** is the epic-branch commit the migration branch starts
      from, after the merge of 8.5.2; step 0 writes it into the migration log. A
      restart after a code fix (8.5.3) starts from a new commit, which the new
      run's log records, and criterion 23 uses the last run's;
   2. **[Decision] merges `main` into the epic branch first,** so items created on
      `main` during the epic are migrated too, and from then until the epic merges,
      `main`'s board is frozen. If `main`'s board must change in that window, it is
      merged again and the guide's steps are run for the new items;
   3. runs on its own branch off the epic branch, one commit per step. If a step
      exposes a defect in 3.0 code, that branch is abandoned, the code is fixed on
      the epic branch, and the migration restarts from step 0 on a new branch.
      The abandoned branch is kept, for its log. Jira writes survive the restart
      and are safe to repeat (Design 1.8);
   4. uses the working-tree CLI only for the final `tcw validate` (and the
      read-only `tcw validate --remote` in a scratch folder at step 3), run from an
      environment installed from the epic branch, since the editable install
      points at the primary checkout (`CLAUDE.md:80-101`).
6. **After the migration commit,** the 3.0 code is frozen and the board is 3.0, so
   the reason for the hand-edit exception no longer holds: **[Decision]** TCW-76's
   remaining moves (review, qa, completed) are made with the 3.0 CLI, its first
   real use. TCW-76's running notes are kept in 2.x `outcome.md` until the step
   that converts it to `implement/round-1.md`. The rewritten `CLAUDE.md` exception
   says that, whenever `tcw/` is being changed again, Jira tickets are moved by
   hand in Jira (each such move is reported by `validate --remote` as a stage ahead
   of its documents when it skips one) and files in item folders are edited
   directly.
7. **[Decision] The order of the end**, following `CLAUDE.md:43-51` (complete
   every work item, then cut the version, then push, then close issues):
   1. the migration branch merges into the epic branch;
   2. TCW-76 is advanced to review, qa and completed with the 3.0 CLI (8.6), and
      TCW-68, whose children are then all completed, is advanced to completed;
   3. the epic merges to `main`;
   4. 3.0.0 is cut straight after (`scripts/cut_version.py`), once the
      documented-surface allowance is empty (Design 7; epic decision 6);
   5. the tag is pushed, which publishes the release;
   6. only then are any originating GitHub issues answered and closed.

   So `main` never holds a half-migrated board, and the window in which `main`
   holds a 3.0 board but PyPI holds 2.8 is as short as possible.

### 9. Abstraction litmus test and harness compatibility

- **No operation is added.** The guide introduces nothing into the model or a
  backend interface; there is nothing for the litmus test to judge in the code.
- **The guide applies the litmus test to its own steps.** Each step is stated for
  both backends, with Jira's form of every fact Jira owns (status, request,
  properties, links) and the shared files for what git owns in both modes.
- **`require_artifact.py`** keeps asking TCW where a document lives (`tcw work
  path`) instead of composing a path, the reason it was written the way it was.
- **Harness.** The guide is plain Markdown that any agent can read. It uses no
  Claude-only mechanism (no context injection, no hooks, no slash commands), and
  every Jira write has a REST form (Design 1.7), so a Codex agent can finish every
  step.

## Acceptance criteria

Criteria 1 to 10 are checked by reading the guide; criteria 11 to 26 and 28 to 30
on the epic branch after the migration commit; 27 on the epic branch before it;
31 during the migration, at step 6.

**The guide**

1. `docs/migration-guide-2.8-to-3.0.0.md` exists and opens with the prerequisites
   and rules of Design 1.2.
2. It has steps 0 to 11 in the order of Design 2, and every step has a **Check**.
   Every check except step 2's contains a shell command and its expected output
   (step 1's is the `grep -c '^## Approved plan'` of the log); step 2's says it is
   the Jira-workflow reading at the end of step 3. No check of steps 4 to 7
   names `inbox` as something that must be gone, and step 8's check is that
   `inbox/` is gone. The checks of steps 9 and 10 name their scope (the plan's
   skipped folders, and `<hook files>`) rather than the whole repository.
3. It has exactly the stops of Design 1.5: one consolidated-plan stop (step 1), a
   stop for Jira changes the agent cannot make (step 2), and the general rule that
   a check failing after one retry stops the migration. No step asks a question
   per item.
4. Each of these names appears in the first column of a mapping table row, and
   that row's second column gives its 3.0 form or "removed" with what replaces
   it. Checked per name with `grep -E '^\| [^|]*<name>'` on the guide, which
   matches only a table row's first cell, and by reading the matched row:
   - every key in `TRACKER_KEYS` (`base.py:1359-1363`), `TRACKER_CREATE_KEYS`
     (`base.py:1364-1365`) and `TRACKER_TRANSITION_KEYS` (`base.py:1381`);
   - every `work.lifecycle` key (`base.py:2982`), every 2.x stage (`base.py:1136`)
     and transition (`base.py:1155-1156`);
   - `retain`, `auto-commit-transitions`, `publish-transitions`, `trunk-branch`;
   - every `state.yaml` field read at `fs.py:5370-5390`, and every `tracker.yaml`
     key;
   - every `WORK_ARTIFACTS` name (`base.py:3101-3102`) and `WORK_SIDECARS` file
     (`base.py:3113-3139`), `graveyard.yaml`, `dod.yaml`, the status folders and
     `inbox/`;
   - every variable set at `hooks.py:60-69` and `resolve.py:191-196`.
5. The hook-variable table maps `TCW_STATUS` to `TCW_FROM_STAGE` for `pre` hooks
   and `TCW_STAGE` for `post` hooks, and `TCW_TRANSITION` to `TCW_STAGE`, and
   says that `TCW_SLUG` keeps its name but becomes the full slug.
6. The `artifacts` row says that an earlier entry's `tags`-only condition is
   added as `not_tags` to later ones, shows this repository's `spec` templates as
   the example, and says that any other shape of earlier condition is listed in
   the plan for the user rather than converted by the rule. The hook-variable
   section says status values are translated by the stage each hook is bound to
   after Design 3.5, with the former-`submit`-hook example of Design 3.6.
7. The guide has a section on 2.x behavior that had no key: automatic commits,
   publishing, retention, and ignored discarded folders.
8. `refined-outcome.md` and `rework.md` map to `qa` rounds with `verdict:` and
   `judges: 1` in filesystem mode, and to ticket comments in Jira mode.
9. The guide contains no `` !` ``, no slash command, and no step that requires a
   particular tool for a Jira write; each Jira write has a REST form.
10. Every `tcw` command the guide names exits 0 with `--help` on the 3.0 CLI (run
    by hand; recorded in the implement round).

**TCW's migration**

11. `find docs/work -mindepth 1 -maxdepth 1 -not -type d` prints nothing, and every
    directory under `docs/work/` matches `^TCW-[0-9]+-[a-z0-9-]+$`.
12. Every `docs/work/*/item.yaml` contains exactly one non-empty line,
    `ticket: https://proposit.atlassian.net/browse/<KEY>`, and `<KEY>` equals its
    folder's prefix.
13. `find docs/work \( -name state.yaml -o -name tracker.yaml -o -name intake.md -o -name initial-request.md -o -name outcome.md -o -name refined-outcome.md -o -name rework.md -o -name post-mortem.md -o -name rollup.md \)`
    prints nothing, and every `spec.md` and `plan.md` under `docs/work` sits at
    `<folder>/spec/spec.md` or `<folder>/plan/plan.md`.
14. `tcw work list --all --json` lists every folder, and each item's stage equals
    the stage recorded for it in the approved plan.
15. `tcw validate` exits 0, and `tcw validate --remote` exits 0. Every warning
    either is gone or is listed in the implement round with its reason.
16. `tcw-config.yaml` parses with no problems under the 3.0 parser and matches
    Design 6, except where a sibling spec renamed a key, which the implement round
    notes.
17. `grep -rln '^Planning doc:' docs/capabilities` prints nothing.
18. `.gitignore` has no line containing `docs/work/discarded`, and has a line
    `/tcw-config.local.yaml`.
19. `diff CLAUDE.md AGENTS.md` prints nothing, and neither file contains
    `dod.yaml`, `refined-outcome.md`, `stage gate` or `<work-item-slug>`. Neither
    `upcoming/README.md` contains `<work-item-slug>` (TCW-75 makes that change;
    this criterion confirms it before the cut).
20. A pytest test runs `scripts/require_artifact.py spec` as a `pre` hook in a
    temporary 3.0 project: it exits non-zero for an item with no `spec/spec.md`,
    with an empty one, and with `TCW_SLUG` unset, and exits 0 when the file has
    text, with `TCW_SLUG` set to the full slug `<project>/<folder>` as the 3.0 hook
    runner sets it. The script contains neither `--json` nor `TCW_NODE_ROOT`.
21. `tests/test_repo_lifecycle.py` passes as rewritten (Design 7), and the full
    suite passes when run as CI runs it, with bare `pytest`.
22. `tcw capabilities drift` prints nothing, or each line it prints is recorded in
    the implement round with its cause and the slice that owns the fix.
23. `git diff --stat <freeze commit>..<migration merge> -- tcw skills agents web`
    prints nothing, where `<freeze commit>` is the one the last run's log
    recorded at step 0 (Design 8.5.1) and `<migration merge>` is the commit that
    merges the migration branch into the epic branch.
24. The implement round (TCW-76's `implement/round-1.md`) records, for every run:
    its start date and freeze commit; the approved plan verbatim under
    `## Approved plan`; every Jira write; and every amendment made to the guide.
    It also records the Jira checklist of Design 6.2, listing by name every
    removed transition, with the owner's confirmation that each line was done,
    written before step 3 ran. A REST GET of the `TCW work` workflow after the
    migration shows exactly one non-initial transition into each of the nine
    mapped statuses.
25. The implement round records the filesystem rehearsal of Design 5.2: the 2.8
    commands that built it, and a clean `tcw validate` at the end.
26. TCW-76's first move after the migration, `tcw work advance <TCW-76 slug>` to
    review, exits 0, and its `post` hook commits or reports nothing to commit.

**Sequencing**

27. Until the migration starts, `docs/work/completed/` on the epic branch holds the
    folder of every finished slice among TCW-69 to TCW-75 and TCW-77, and
    `graveyard.yaml` gains no entry for any of them.

**Release readiness**

28. The temporary documentation allowance module (TCW-70 Design 14) and its
    guard test no longer exist, `tests/test_documented_cli_surface.py` passes
    without them, and TCW-75's link test no longer exempts
    `docs/migration-guide-2.8-to-3.0.0.md`; bare `pytest` still passes.
29. This item's two `upcoming/` entry files are named by its folder name after
    the migration (`TCW-76-<title words>.md`, the name step 6 gives the folder),
    and have no text before their first `##` heading.
30. On TCW's prune list (Design 2, step 1), as fixed by the approved plan:
    - every **item** (bound or unbound) has a folder whose ticket is at
      `Won't Do`;
    - every **inbox entry** has a ticket at `Won't Do` and **no** folder: no
      `item.yaml` under `docs/work` names its key (Design 3.1);
    - each of those tickets has exactly one comment beginning with
      `subject removed by TCW 3.0 (TCW-68)`, so a repeated post fails this
      criterion (Design 1.8);
    - the ticket for "keep an item's folder in one place" is at `Done`, has no
      folder, and has exactly one comment naming TCW-68;
    - `tcw work list --json` (open items only) shows none of them.

    Checked by reading each ticket once, recorded in the implement round.
31. Rerunning step 6 once more, right after its check first passes, writes
    nothing to Jira (Design 1.5, 1.8): a JQL search for the project's tickets
    with `updated >=` the rerun's start time returns none, and every action the
    rerun logs is a skip. Recorded in the implement round.

### Coverage

| Design | Criteria |
| --- | --- |
| 1 The guide's form | 1, 2, 3, 9, 24, 31 |
| 2 Steps | 2, 3, 24, 30, 31 |
| 3.1–3.4 Stages, fields, documents, store root | 4, 8, 11, 12, 13, 14 |
| 3.5 Configuration | 4, 6, 16 |
| 3.6 Hook variables | 4, 5, 6 |
| 3.7 Capability records | 17, 22 |
| 3.8–3.9 Project files, references | 7, 18, 19 |
| 4 Jira binding | 12, 14, 15, 24, 30, 31 |
| 5 Proving | 10, 24, 25 |
| 6 TCW's configuration | 16, 24, 26 |
| 7 TCW's files | 18, 19, 20, 21, 28, 29 |
| 8 Sequencing | 23, 24, 26, 27, 28 |

## Risks

- **The guide depends on seven sibling specs that are written but not built.**
  TCW-70 to TCW-75 and TCW-77 are specified, and the guide's storage details
  (inbox items, `item.yaml` keys, `work.jira` keys, renamed commands, surviving
  procedures) come from them, but each may still change before it lands.
  Mitigation: this spec fixes what maps to what and why; the guide's exact names
  are written last, from the finished code, and criterion 10 checks every command.
- **One real migration proves only what it contains.** TCW's board exercises a
  narrow part of the guide. Mitigation: the filesystem rehearsal (Design 5.2) is
  built to cover the rest.
- **Jira changes are shared and do not roll back.** Workflow and field changes
  affect everyone using the TCW Jira project, and a reverted git branch leaves its
  tickets and comments behind. Mitigation: the Jira changes are approved in the
  plan; every write is logged and safe to repeat (Design 1.8).
- **Replacing existing transitions with global ones** (Design 6.2) changes how
  people move tickets by hand in Jira. With epic decision 5, an old transition
  only has to go when it competes with a global one on equal terms, and in TCW's
  live workflow all eight directed transitions do (Design 6.2). People who move
  tickets by hand then see one transition per target status in place of `Submit`, `Rework` and the rest. Mitigation: the owner chose one
  global transition per mapped status (owner answer of 2026-10-01), confirms the
  full removal list, and makes every Jira change by hand from the checklist
  (Design 6.2).
- **Board changes on `main` during the freeze** would be lost or need a second
  pass. Mitigation: merge first, freeze `main`'s board, re-merge if it must change
  (Design 8.5).
- **The published plugin may run ahead of the published CLI.** Merging 3.0 skills
  to `main` before 3.0.0 is on PyPI could give plugin users 3.0 instructions with a
  2.8 CLI. Mitigation: merge and cut back to back (Design 8.7), and check CI is
  green before tagging, since a red suite blocks the release without saying so.
- **A `judges` number written wrong makes a verdict `stale`.** That blocks the item
  rather than letting it through. All converted rounds use `judges: 1`.
- **Drift on carried-over items.** The completed item
  `2026-09-17-stop-offering-a-version-cut-after-every-completed-work-item` declares
  `changed:` paths such as `work/customize-the-definition-of-done`, which a 3.0
  slice may remove. Unless that slice declares the removal, drift reports it.
  Mitigation: criterion 22.
- **A large one-off ticket creation.** TCW needs up to 18 new tickets (8 unbound
  items, 10 inbox entries). The prune does not reduce that number, since pruned
  entries are recorded as `Won't Do` tickets (Design 2, step 1), but only 7 of the
  18 stay open: 3 backlog items and 4 inbox entries. Of the other 11, 9 go
  straight to `Won't Do` (the prune list) and 2 straight to `Done`: the
  completed item `2026-09-17-stop-offering-a-version-cut-after-every-completed-work-item`,
  which has no `tracker.yaml`, and "keep an item's folder in one place".

## Notes

Reconciled with the epic's cross-slice decisions on 2026-10-01, and revised on
2026-10-02 after review and the cross-slice answers R1 to R20 (see "Review
2026-10-02" below).

### Decisions made in this spec, for the owner to confirm

Each is marked **[Decision]** above:

- checks are read-only shell commands; the CLI is used only at the end (1.4);
- three kinds of stop only (1.5);
- Jira writes have REST forms (1.7) and are safe to repeat and logged (1.8);
- a survey step with one consolidated plan, including a prune list (2.1); TCW's
  prune list confirmed by the owner on 2026-10-01;
- the Jira compatibility check runs in a scratch folder after the config rewrite
  (2.3);
- Jira mode writes a full `item.yaml` first and reduces it at binding (2.4);
- ignored discarded folders are listed and, if kept, tracked (3.1); for TCW none
  is kept unless named (confirmed 2026-10-01);
- `initial-request.md` wins over `intake.md`, which is appended when different
  (3.3);
- acceptance history maps to `qa` rounds, `judges: 1`, rework before acceptance
  (3.3);
- the 2.x tracker keys that TCW-71 does not accept (`create.issue-types`,
  `create.components`, `create.on-new`, `comments`, `link`) are removed, each with
  what replaces it (3.5);
- `/tcw-config.local.yaml` is added to `.gitignore` (3.8);
- empty disk values and `<KEY> — ` title prefixes are not disagreements; extra
  Jira labels are removed only on agreement (4.2);
- request text goes to an empty body, otherwise to a comment (4.4);
- a filesystem-mode rehearsal proves the rest of the guide (5.2);
- TCW enables every optional stage, with `Specifying`, `Planning` and `In QA` as
  new statuses and `In Review` as review (6.2; confirmed 2026-10-01);
- one global transition into each mapped status, with `Start` and `Accept`
  removed (6.2; confirmed 2026-10-01);
- the owner does TCW's Jira administration from a checklist in the implement
  round (2.2, 6.2; confirmed 2026-10-01);
- the Definition of Done splits into the built-in gates, `tcw validate` as the
  project gate, and `docs/lifecycle/review.md`: "tests pass" and "docs synced" are
  review-stage instructions, not gates, because the suite outlasts the 300-second
  hook limit and documentation-sync is a skill, which `pre` cannot run (6.3;
  confirmed 2026-10-01);
- `Tracker-Change` becomes `Jira-Change`; upcoming files are named by folder
  (6.4);
- TCW binds TCW-75's commit script where it is, and has no push hook (6.5;
  confirmed 2026-10-01);
- the documentation allowance module and its guard test are deleted once empty
  (7);
- completed epic items are kept, not deleted (8.3);
- `main` is merged in and its board frozen before the migration (8.5);
- after the migration commit, TCW-76 is moved with the 3.0 CLI (8.6);
- a step interrupted for a reason that is not a defect is rerun, and every action
  in it skips what is already done (1.5);
- Jira, not the log, decides whether a write is repeated: tickets by reporter,
  start date and exact summary, comments by a fixed first line (1.8);
- the migration log is TCW-76's implement round, copied forward across runs, and
  an abandoned branch is kept (1.8, 8.5.3);
- `<hook files>` is a fixed list in the plan, never the whole repository (1.4);
- step 9's check skips the migration log and the migrating item's folder (2.9);
- in Jira mode `tracker.yaml` survives until step 6 binds (2.5);
- the scratch folder for `validate --remote` holds the config and its bound
  files, and only Jira-workflow findings are acted on there (2.3);
- `artifacts` conditions other than `tags` alone are listed for the user (3.5);
- status values in hook comparisons are translated by each hook's new stage
  (3.6);
- the rehearsal's nested child and `blocked/` folder are placed by hand (5.2);
- all eight directed transitions into mapped statuses are removed, not only
  `Start` and `Accept` (6.2; the owner confirms, below);
- the end of the epic runs: merge the migration, complete TCW-76 and TCW-68,
  merge to `main`, cut, push, close issues (8.7).

Settled by the epic's decisions rather than by this spec: hook variables mapped by
meaning (decision 11), `Planning doc` and `Tracker` removed from records
(decision 9), and the epic board kept in 2.x form, read with a released 2.8 CLI,
with each ticket moved by hand (decision 7).

### Contradictions in the ticket, and how this spec resolves them

- **`capabilities.yaml`:** the artifact table says `spec/capabilities.yaml`; the
  "Update from TCW-69's spec" section and the owner's confirmed decision say the
  item root. It is already at the item root in 2.x (a side file,
  `base.py:3113-3117`), so nothing moves (epic decision 19).
- **Order:** step 2 runs `tcw validate --remote` before step 3 writes the
  configuration it reads. Resolved in Design 2, step 3.
- **Acceptance records:** the ticket says qa, the decision record says review.
  Resolved for qa (Design 3.3).
- **Hook variables:** the ticket's list pairs them by position. Resolved by
  meaning (Design 3.6; epic decision 11).
- **"Missing priority becomes medium"** would overwrite Jira-owned priorities in
  Jira mode. Applied in filesystem mode only (Design 4.2).

### Cross-slice findings

Nothing has been posted to these tickets. Most findings from the first draft are
now settled:

- **TCW-69.**
  - The 46 `work/` capability records: settled by epic decision 12 (TCW-70
    decides each).
  - The value of `TCW_SLUG`: settled by epic decision 11 (the full slug), now in
    TCW-69 Design 6.5.
  - Renames by position: settled by epic decision 11 (by meaning, this spec's
    table).
- **TCW-70.**
  - Retiring the 2.x `tests/test_repo_lifecycle.py`: settled; TCW-70 deletes it
    (TCW-70 Design 15.1) and this slice writes its 3.0 replacement.
  - Where an inbox item's text is stored: settled; the request document,
    `request/request.md` (TCW-70 Design 3.3, "There is no `intake.md`").
  - The suggested message naming the guide for a leftover status folder:
    adopted; both "not part of a work store" messages end with a pointer to the
    guide, without code that recognizes 2.x (TCW-70 Design 10.1).
  - The documentation allowance: TCW-70 creates it and states that this slice
    requires it empty before the cut (TCW-70 Design 14; epic decision 6); this
    spec adds deleting it once empty (Design 7), which TCW-70 should not object
    to but has not said.
  - The variables and JSON payload given to `generate` prompt bindings
    (`resolve.py:183-196`): settled. TCW-69 Design 8 keeps the four
    `TCW_HOOK_*` variables unchanged, and cross-slice decision R13 fixes the
    stdin object and `{{tcw:request}}` (Design 3.6).
- **TCW-71.**
  - The 2.x tracker keys with no stated fate: settled; `timeout-seconds` and
    `create.issue-type` become `timeout` and `issue-type` (TCW-71 Design 1), and
    this spec removes the rest (Design 3.5).
  - The compatibility check on a project with no items: settled; with no items
    the checked type is the configured `issue-type` and unsampled moves are
    reported as unchecked findings (TCW-71 Design 9.2; epic decision 10).
  - Two routes into one status: settled by epic decision 5; TCW's own workflow is
    handled in Design 6.2.
  - Live tests: settled by the owner on 2026-10-01; TCW-71's live tests keep
    using the `TCWTEST` project, so this slice's Jira checklist covers only `TCW`
    (Design 6.2).
  - Creating completed tickets: TCW-71 notes that TCW cannot create a ticket
    directly at a later status; the guide uses REST writes for it and never
    `tcw work new` (Design 4.1).
- **TCW-72.** Adding `/tcw-config.local.yaml` to existing projects' `.gitignore`:
  agreed by both specs (TCW-72 Notes; Design 3.8). TCW-72's `me()` is replaced by
  `current_user()` (epic decision 17), which changes nothing here.
- **TCW-73.**
  - `Planning doc` and `Tracker` in `CAP_FIELDS`: settled by epic decision 9.
  - `spec/capabilities.yaml` in its ticket: settled by epic decision 19.
  - The "node" key names: settled by the owner on 2026-10-01:
    `connected-projects` becomes `projects` and the Feature
    `connected-project-registry` becomes `project-registry` (TCW-73), and the
    guide's configuration table lists both (Design 3.5).
- **TCW-74.**
  - `spec/capabilities.yaml`: settled by epic decision 19.
  - Whether `create-work` survives: settled; it is rewritten (TCW-74 Design 5.1),
    so TCW keeps its `work.procedures.create-work` binding.
  - The eval harness: settled by epic decision 14 (TCW-74).
  - Suggested, still open: the setup skill names the guide when it meets a 2.x
    project.
- **TCW-75.**
  - `spec/capabilities.yaml`: settled by epic decision 19.
  - The `abstraction.md` phrases asserted by `tests/test_repo_lifecycle.py`:
    settled; TCW-75 moves them into its own test (TCW-75 Design 11).
  - Ownership: the `upcoming/README.md` files are TCW-75's, and this spec no
    longer edits them (Design 6.4). TCW-75's link test exempts the guide until it
    exists; this slice removes the exemption (Design 7).
- **TCW-77.** `spec/capabilities.yaml`: settled by epic decision 19. Its removal of
  the `Planning doc` and `Tracker` fields from the viewer agrees with Design 3.7 and
  epic decision 9.

### Questions only the owner can answer

All five questions this spec asked were settled by the owner on 2026-10-01:

1. Status names and stages. Settled by the owner on 2026-10-01: every optional
   stage is enabled, with spec `Specifying`, plan `Planning` and qa `In QA`
   (Design 6.2).
2. The TCW Jira workflow. Settled by the owner on 2026-10-01: `Start` and
   `Accept` are removed, leaving one global transition per mapped status
   (Design 6.2).
3. Jira administration. Settled by the owner on 2026-10-01: the owner does it by
   hand from a checklist this slice writes; TCW-71's live tests reuse `TCWTEST`
   (Design 2, step 2; Design 6.2).
4. The prune list. Settled by the owner on 2026-10-01: the whole list is
   discarded with the reason `subject removed by TCW 3.0 (TCW-68)`, and "keep an
   item's folder in one place" is closed as done by the epic (Design 2, step 1).
5. Untracked discarded items. Settled by the owner on 2026-10-01: they are
   listed at the survey and none is kept unless the owner names it (Design 3.1).

The inbox entries in the prune list are the six the owner's question named
(Design 2, step 1): five discarded, one closed as done.

One new question, raised by the 2026-10-02 review (Jira administration):

6. **Removing all eight directed transitions.** The live `TCW work` workflow
   (read 2026-10-02) has `Submit`, `Complete`, `Rework`, `Cancel`, `Stop` and
   `Reopen` as well as `Start` and `Accept`, all without screens, so each would
   tie with a new global transition and `advance` would refuse with exit 3. This
   spec removes all eight to reach the owner's "one global transition per mapped
   status" (Design 6.2). The owner confirms that, or chooses another way to break
   the ties (for example, giving the old transitions a screen with a field, so
   that epic decision 5 prefers the global one and they stay usable by hand).

### Other notes

- **The ticket's numbers are out of date** (Problem 3). The guide's survey
  recounts at migration time, since the board keeps changing until then.
- **The owner's own notes outside the repository** describe 2.x behavior (for
  example, how a Jira sync reverses a manual move). They are not part of this
  slice, but will need revisiting after the migration.
- **Driving this item.** This item's implementation changes no code under `tcw/`,
  but the code is in flux until the freeze, so its board is driven by editing
  files, per `CLAUDE.md`, until Design 8.6 applies.

### Review 2026-10-02

Each finding of the 2026-10-02 review, verified against the repository, the
sibling specs and (for finding 3) the live Jira workflow, read with REST GET
calls only:

1. **ACCEPTED.** Steps 4 and 6 required `inbox/` gone before step 8 deletes it.
   The status-folder `find` no longer lists `inbox` (Design 1.4), step 4's loop
   and step 6's name check skip it, and step 8 keeps its own check.
2. **ACCEPTED.** Every Jira write now skips when its effect is already in Jira:
   tickets found by reporter, first-run start date and exact summary; comments by
   a fixed first line; moves and fields by current value (Design 1.8). The log's
   home and its survival across restarts are stated (1.8, 8.5.3), as is rerunning
   an interrupted step (1.5). Criteria 30 and 31 fail a repeated write.
3. **ACCEPTED, and confirmed.** The live `TCW work` workflow has eight directed
   transitions into mapped statuses, none with a screen; removing only `Start`
   and `Accept` leaves six ties. Design 6.2 now lists the workflow, removes all
   eight, and states what the 2.8 CLI loses from step 2; the owner confirms the
   wider removal (question 6).
4. **ACCEPTED.** Step 9's check skips the migration log and the migrating item's
   folder (TCW-76's), named in the plan.
5. **ACCEPTED.** `<hook files>` is a fixed list in the plan (Design 1.4); `git
   grep` confirms the names appear across `docs/`, `tests/`, `skills/work` and
   `tcw/work`, and in scope only at `scripts/require_artifact.py:12`.
6. **ACCEPTED.** Criterion 30 now requires folders for pruned items and no folder
   for pruned inbox entries (Design 3.1), so inventing folders fails it.
7. **ACCEPTED.** Status values are translated per hook by the stage it is bound
   to after Design 3.5, `backlog` becomes the set of stages before implement,
   and the `stage gate` case (`tcw/work/cli.py:1993-1994`) has its own row
   (Design 3.6).
8. **ACCEPTED.** TCW-69 Design 8 keeps the four `TCW_HOOK_*` variables; R13
   settles the stdin JSON. Design 3.6's rows and the cross-slice note are updated.
9. **ACCEPTED.** The `not_tags` rule is limited to `tags`-only earlier conditions
   (`tcw/store/base.py:1203-1207`); other shapes go to the plan. Criterion 6
   checks the limit.
10. **ACCEPTED.** `blocked` is not in `WORK_STATUSES` (`tcw/store/base.py:989`),
    and 2.8 records `parent:` instead of nesting (`tcw/store/fs.py:4792-4800`).
    The `blocked/` row is rewritten and the rehearsal places both by hand.
11. **ACCEPTED.** In Jira mode `tracker.yaml` now survives until step 6 binds and
    deletes it (steps 5 and 6, Design 3.2).
12. **NARROWED.** No sibling spec says whether 3.0 `validate` reports a missing
    git repository or missing bound files, so the spec cannot settle what those
    findings look like. It now says what the scratch folder holds (the config,
    its bound files, empty store folders) and that only Jira-workflow findings
    are acted on there.
13. **ACCEPTED.** Criterion 2 matches the design (steps 1 and 2 named), criterion
    4 greps only a table row's first cell, and criterion 29 names the folder
    after step 6.
14. **ACCEPTED.** 3 items stay open, not 4; the completed unbound item goes to
    `Done`. Risks now count 7 open, 9 `Won't Do`, 2 `Done`.
15. **ACCEPTED.** Design 8.7 states the order (migration merge, complete TCW-76
    and TCW-68, merge to `main`, cut, push, close issues), following
    `CLAUDE.md:43-51`; the freeze commit is defined in 8.5.1 and recorded at
    step 0, and criterion 23 names it.

Cross-slice answers applied: R1 (the order, Design 8.5.1), R4 (git wording,
Design 1.6 and the prune reason in step 1), R7 (the checklist covers only `TCW`,
already so), R13 (Design 3.6), R14 (retired capability fields are errors and the
epic board runs on 2.8 until this slice, already Design 3.7). R16 does not
conflict: TCW-71 Design 9 reports an unchecked move as a `warning` finding, which
is a check that ran, not one that was skipped. R20 (plain `validate` is offline)
is consistent with step 11 running both forms.
