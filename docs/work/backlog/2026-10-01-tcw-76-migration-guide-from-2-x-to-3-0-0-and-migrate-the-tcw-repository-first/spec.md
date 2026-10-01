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
  the 105 `meta.yaml` files under `docs/capabilities/` today. See Design 3.7.
- No record carries the `Tracker` field today (0 of 105), so its removal changes
  nothing here.

Two facts about the ledger matter to the slices that do change it, and are listed
as cross-slice findings in Notes:

- TCW-69's spec says `work/archive-a-resolved-item-before-it-is-deleted` is "the
  ledger's one `work/` capability today". There are **46** folders under
  `docs/capabilities/work/`, most describing 2.x behavior (`start-a-work-item`,
  `submit-a-work-item-for-review`, `customize-the-definition-of-done`,
  `customize-lifecycle-artifact-templates`, `hold-a-tracker-ticket`, and others).
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
  (Design 2, step 1); the decisions are the owner's.
- **The eval harness.** `evals/seed_fixture.py` builds 2.x boards; who updates it is
  a cross-slice finding (Notes), not this slice's work.

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
   - the rules: do the steps in order; after each, run its check and do not go on
     until it passes; stop at every **Stop and ask** point.
3. **Every step** has three parts: what to do, a **Check**, and where it applies a
   **Stop and ask**.
4. **[Decision] Checks are read-only shell commands with stated expected output**
   (`find`, `grep`, `ls`, `diff`), not the `tcw` CLI, until the final step. The
   same guide then works in this repository, where the CLI may not be driven
   mid-migration, and anywhere else, and no check depends on a command that only
   understands a fully migrated project. Examples the guide uses:
   - `find docs/work -mindepth 1 -maxdepth 1 -type d \( -name backlog -o -name active -o -name review -o -name blocked -o -name completed -o -name discarded -o -name inbox \)`
     prints nothing once the store is flattened;
   - `find docs/work -name state.yaml -o -name tracker.yaml` prints nothing once
     items are converted;
   - `grep -rnE 'TCW_(STATUS|TRANSITION|NODE_ROOT|RESOLUTION)\b' <project files>`
     prints nothing once hooks are rewritten.

   Paths are written relative to the project's configured work path, which
   defaults to `docs/work`.
5. **[Decision] Three kinds of stop, and only three:**
   - **The consolidated plan** (step 1): one question, covering every decision the
     migration needs, answered once.
   - **Changes the agent cannot make itself:** Jira administration (statuses,
     workflow, custom fields) when the agent lacks the access.
   - **A check that fails after one retry.** The agent reports what it expected,
     what it saw, and stops.
6. **Commits.** TCW never commits, but the project may. The guide recommends one
   commit per step after its check passes, so a bad step can be reverted, and says
   so as the project's choice.
7. **[Decision] Jira writes are given as REST requests** (`curl` with the
   credentials named in the project's config), with the web UI and any Jira tool
   the agent has as equivalents. A REST call works under Claude and Codex alike, so
   no step depends on one harness's tools.
8. **[Decision] Every Jira write is safe to repeat.** A migration that is
   abandoned and restarted (Design 8.5) leaves its Jira changes behind, since
   reverting git does not undo them. So before creating a ticket, the agent
   searches the Jira project for one with the same summary that it created earlier,
   and it records every Jira write (ticket key and what changed) in the
   migration's log as it goes (for TCW: the TCW-76 implement round).

### 2. The steps

The ticket's order, with two changes: a survey step comes first, so that the one
consolidated question can be asked before anything changes, and the Jira
compatibility check moves after the configuration is written, because it reads
that configuration.

0. **Prepare.** Check the prerequisites (Design 1.2). On the 2.8 CLI, `tcw
   validate` should be clean; anything it reports is fixed under 2.8 first, where
   the tools for it still exist. Find untracked item folders hidden by
   `.gitignore` (`git status --ignored -- docs/work`) and list them.
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

   **Check:** the user's approval, recorded verbatim in the migration log.
2. **Jira mode: prepare Jira.** Add one status per enabled stage that has none,
   the transitions `advance` needs, and the TCW Project, TCW Item, effort and
   complexity fields (TCW-71 defines their types). **Stop and ask** for anything the
   agent cannot do itself. **Check:** deferred to the end of step 3, since the
   check reads the new configuration.
3. **Rewrite the configuration**, key by key (Design 3.5). **Check:**
   `grep -nE '^\s*(tracker|lifecycle|retain|auto-commit-transitions|publish-transitions|trunk-branch):|builtin: true' tcw-config.yaml`
   prints nothing. **[Decision]** In Jira mode the agent then copies the new
   `tcw-config.yaml` alone into a scratch folder with an empty work folder and runs
   `tcw validate --remote` there. That runs TCW-71's workflow compatibility check
   against the real Jira project without the half-migrated board's errors drowning
   it, and without using the CLI on the board.
4. **Flatten the store and give every item a stage.** Move each item folder up out
   of its status directory (and each nested child out of its parent's folder);
   write the stage (Design 3.1). Delete the status directories, their `.gitkeep`
   files, `graveyard.yaml` and `dod.yaml` (Design 3.4). **[Decision]** In Jira mode
   too, this step writes the full filesystem-form `item.yaml` (title, stage and
   properties). It is the "disk" side of reconciling in step 6, which then reduces
   it to the ticket link. One conversion procedure then serves both modes.
   **Check:** the status-directory `find` above prints nothing, and
   `for d in docs/work/*/; do [ -f "$d/item.yaml" ] || echo "$d"; done` prints
   nothing.
5. **Convert item fields** (Design 3.2) and delete `state.yaml` and
   `tracker.yaml`. In Jira mode `tracker.yaml` is read first, for the binding.
   **Check:** the `state.yaml`/`tracker.yaml` `find` prints nothing; no `item.yaml`
   has an integer `priority` (`grep -nE '^priority: [0-9]' docs/work/*/item.yaml`
   prints nothing).
6. **Jira mode: bind** (Design 4): reconcile bound tickets with disk; create
   tickets for items and inbox entries that have none; set TCW Project and TCW
   Item; rename folders to `<KEY>-<title words>`; reduce each `item.yaml` to
   `ticket: <url>`. **Check:** every folder name matches `^<project key>-[0-9]+-[a-z0-9-]+$`
   (for TCW, `^TCW-[0-9]+-[a-z0-9-]+$`), every `item.yaml` is the one `ticket:` line, and the key in
   that line equals the folder's prefix.
7. **Move documents** (Design 3.3). **Check:** no 2.x document name remains at an
   item root (`find docs/work -maxdepth 2 \( -name intake.md -o -name initial-request.md -o -name spec.md -o -name plan.md -o -name outcome.md -o -name refined-outcome.md -o -name rework.md -o -name post-mortem.md -o -name rollup.md \)`
   prints nothing); every verdict round has `verdict:` and `judges:` front matter.
8. **Convert the inbox.** Filesystem mode: each entry becomes an inbox-stage item
   as TCW-70 stores one. Jira mode: each entry's ticket was created in step 6; the
   file is deleted. **Check:** the `inbox/` folder is gone.
9. **Rewrite live references** (Design 3.9). **Check:** for every renamed folder,
   `grep -rn '<old folder name>'` over open items' documents and the project's
   live files prints nothing.
10. **Review the project's own files** (Design 3.8), and capability records
    (Design 3.7). The agent fixes what the approved plan covers and points out text
    that relies on removed behavior. **Check:** the variable `grep` in Design 1.4,
    and `grep -rln '^Planning doc:' <capabilities path>` prints nothing.
11. **Validate.** `tcw validate` (and `tcw validate --remote` in Jira mode) exits 0.
    Each remaining warning is either fixed or listed for the user with its reason.

### 3. The mappings

#### 3.1 Status folder to stage

| 2.x folder | 3.0 stage |
| --- | --- |
| `inbox/` (loose `.md`) | filesystem: an item at `inbox`; Jira: a ticket in the inbox status, with no item |
| `backlog/` | the furthest of request, spec, plan whose document exists: `plan` if `plan.md`, else `spec` if `spec.md`, else `request` |
| `active/` | `implement` |
| `review/` | `qa` (2.x review was the requester's acceptance; Design 3.3) |
| `blocked/` | the stage its documents imply, by the `backlog` rule, extended to `implement` when `outcome.md` exists; `blocked-by` is kept |
| `completed/` | `completed` |
| `discarded/` (tracked or ignored) | `discarded`; the resolution (`wontfix`, `duplicate`, `superseded`) and any reason become a comment |

The rule picks a stage whose document is already written; a later stage would trip
TCW-69's "stage ahead of artifacts" warning (TCW-69 Design 9). When a stage the rule
picks is disabled in the new config, the item takes the next enabled flow stage.

**[Decision] Ignored discarded folders** (Problem 2.4) are listed in the
consolidated plan. Kept ones become tracked `discarded` items, since 3.0 no longer
has a folder to ignore; the `.gitignore` rule is removed in step 10.

#### 3.2 Item fields (`state.yaml` and `tracker.yaml` to `item.yaml`)

| 2.x | 3.0 |
| --- | --- |
| `slug` | dropped; the folder name is the identity |
| `title` | `title` (Jira: Summary) |
| `created` | dropped; the folder's date prefix (filesystem) or the ticket's creation date (Jira) |
| `priority` (integer) | **[Decision, from the ticket]** ≥ 40 `highest`, 30–39 `high`, 20–29 `medium`, 10–19 `low`, < 10 `lowest`. Missing: `medium` in filesystem mode; in Jira mode the ticket's priority stands (Design 4.2) |
| `effort`, `complexity` | carried over (the scale is the same four values) |
| `tags` | carried over (Jira: Labels) |
| `owner` | filesystem: `assignee`. Jira: dropped, because it is a git identity, not a Jira account; listed in the plan |
| `blocked_by` | `blocked-by` as full slugs (`<project>/<folder>`), using the folders' final names. A free-text blocker is dropped and listed, since 3.0 blockers are items (TCW-69 Design 2.4). Jira: a Blocks link |
| `parent` | `parent` as a full slug; for a child made before `parent` was recorded, the folder it was nested in (`fs.py:4792-4800`). Jira: the ticket's Parent |
| `initiative` | `parent`, as a full slug in the named project, when the item has no `parent`; if it has both, `parent` stays and the `initiative` is listed |
| `type` | dropped; an item with children is an epic (TCW-69 Design 2.6) |
| `resolution` | dropped; the stage says it (Design 3.1) |
| `started`, `completed`, `phase`, `worktree`, `branch` | dropped |
| `tracker.yaml` `ticket` | Jira: `ticket: <url>` in `item.yaml` |
| `tracker.yaml` `schema`, `provider`, `project`, `part`, `bound`, `unlinked`, `sync` | dropped once binding is done; a `sync: pending` record is reported as "Jira lagged" in step 1 |

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
| `work.lifecycle.artifacts.<doc>` | `file` entries with their `when:` in that stage's `prompt` list. Because prompts are cumulative (Problem 2.2), each earlier entry's condition is added as a negated condition (`not_tags`) to the later ones, so the same single template applies as before; a `builtin` fallback entry is dropped, since `inherit: true` already supplies the built-in text |
| a `skill` binding in `pre` | an error in 3.0: moved to `post` (reported, not run) or to prompt text, as the user chooses |
| `when: {type: …}` | an error in 3.0: removed; an epic condition becomes a tag the user adds to the epics |
| `work.tracker.provider` | `work.backend: jira` |
| `work.tracker.base-url` | `work.jira.site` |
| `work.tracker.credentials.*` | `work.jira.credentials.*` (same variable names) |
| `work.tracker.statuses.<status>` | `work.stages.<stage>.status`: `backlog` → `request`, `active` → `implement`, `review` → see Design 6.2, `completed` → `completed`, `discarded` → `discarded`. spec, plan, qa and any newly enabled stage need new statuses |
| `work.tracker.pre-backlog` | `work.stages.inbox.status` (its key); its transition name is dropped |
| `work.tracker.inbox-query` | dropped when it only selects the inbox status of the configured project, which the default inbox does; otherwise `work.jira.inbox-query` |
| `work.tracker.candidate-query` | removed; "what can I pick up" is `tcw work list --stage request --mine` |
| `work.tracker.transitions.*`, `strict`, `exclusive-claim-transition` | removed: `advance` finds the transition by its destination, and claims are gone |
| `work.tracker.create.project` | `work.jira.project` |
| `work.tracker.timeout-seconds`, `comments`, `link`, `create.issue-type`, `create.issue-types`, `create.components`, `create.on-new` | as TCW-71's spec decides (Notes, cross-slice findings) |
| `work.retain` | removed. 3.0 never deletes; a project that prunes does it itself |
| `work.auto-commit-transitions`, `work.publish-transitions` (set or defaulted, Problem 2.3) | removed; the project adopts TCW-75's opt-in git example if it wants commits |
| `work.trunk-branch` | removed |
| `work.tags`, `work.documentation`, `work.path`, `work.repository` | kept; `documentation` entries are reviewed for 2.x wording |
| `work.procedures.<id>` | kept for procedures TCW-74 keeps; a binding for a procedure TCW-74 deletes is removed and its text reviewed |
| `connected-projects` and other "node" keys | renamed as TCW-73 decides |

#### 3.6 Hook variables

**[Decision] Mapped by meaning, not by position** (Problem 2.1):

| 2.x | 3.0 |
| --- | --- |
| `TCW_SLUG` (a bare folder name) | `TCW_SLUG`, in the form TCW-69 fixes (Notes) |
| `TCW_STATUS` in a `pre` hook (the source status) | `TCW_FROM_STAGE` |
| `TCW_STATUS` in a `post` hook (the destination status) | `TCW_STAGE` |
| `TCW_TRANSITION` (`start`, `submit`, `complete`, `rework`, `discard`, `auto-delete`, or a stage name) | `TCW_STAGE`, compared against the target stage's name instead of the move's |
| `TCW_NODE_ROOT` | `TCW_PROJECT_ROOT` |
| `TCW_RESOLUTION` | removed: `TCW_STAGE` is `completed` or `discarded`, and the reason is in `TCW_REASON` |
| `TCW_ITEM_PATH` | `TCW_ITEM_PATH`; the folder no longer moves, so it is the same before and after |
| (none) | new: `TCW_FORCED` and `TCW_REASON` on forced moves |
| `TCW_HOOK_ROLE`, `TCW_HOOK_KIND`, `TCW_HOOK_ID`, `TCW_HOOK_PHASE` (`generate` bindings) | as TCW-69 or TCW-72 settles (Notes) |

Status values inside comparisons are translated by Design 3.1 (`active` →
`implement`, `review` → `qa`).

#### 3.7 Capability records

- **[Decision] `Planning doc` is removed.** It was the capability-to-work pointer
  that 2.x drift followed (`tcw/capabilities/cli.py:200-222`). 3.0 drift reads
  completed items' declarations instead (TCW-69 Design 7), TCW-74 drops
  planning-doc pointers from the capabilities skill, and TCW-77 drops the field
  from the viewer. Its values are 2.x slugs, most naming items that are now only
  `graveyard.yaml` entries, which this migration deletes, so they would point at
  nothing. Keeping it as free text would leave 65 dangling pointers that nothing
  reads. The vocabulary check rejects fields not in `CAP_FIELDS`
  (`fs.py:3531-3532`), so once TCW-73 removes the field from `CAP_FIELDS`
  (`base.py:844-847`), records that keep it fail `tcw validate`. The guide removes
  the line from every record.
- `Tracker` goes the same way, for the same reason (TCW-77: work items point at
  capabilities, not the other way).
- Existing `Missing` records are left alone: each is a true statement of a known
  gap. An in-flight item whose 2.x plan seeded one still has to make it
  `Supported` (or remove it) before review, which the records gate enforces.

#### 3.8 The project's own files

The guide tells the agent to search for, and list in the plan:

- hook scripts and commands bound in config: the variables in Design 3.6, 2.x
  status names, and calls to removed commands (`start`, `submit`, `rework`,
  `complete`, `drop`, `stage gate`, `inbox`, `tracker`, `reconcile`, `scaffold`,
  `delete`, `tombstone`);
- prompt and procedure files bound in config, and the agent guides (`AGENTS.md`,
  `CLAUDE.md`): text that relies on removed behavior (status folders,
  `state.yaml`, the Definition of Done, `refined-outcome.md`, claims, retention,
  automatic commits);
- `.gitignore`: rules naming status folders are removed; **[Decision]**
  `tcw-config.local.yaml` is added, because TCW-72 has `tcw init` add it only for
  new projects;
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
     completed items are created and then moved straight to the completed status;
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
   they appear nowhere, since the default inbox shows only the inbox status
   (TCW-71). The user chooses per ticket: move to the inbox status, or leave.

### 5. Proving the guide

1. **TCW's own Jira-mode migration** (Design 6 to 8) follows the guide as written.
   Where the guide is wrong or unclear, the guide is fixed first, then the step is
   redone from the fixed text. Every amendment is recorded in the implement round.
2. **[Decision] A filesystem-mode rehearsal** on a disposable project built with
   the released 2.8 CLI in a scratch folder and environment. TCW's board has no
   items in `active`, `review`, `blocked` or `discarded`, no nested children,
   `initiative`, `rework.md`, `post-mortem.md`, connected projects, transition
   bindings other than `complete`, or `timeout`, so the Jira migration alone leaves
   most of the guide unexercised. The rehearsal project has at least one of each,
   plus an unconditional `artifacts` template after a conditional one and a
   legacy bare-list stage. The guide is followed in filesystem mode and ends with
   `tcw validate` clean. The 2.8 commands used to build it are recorded in the
   implement round so it can be rebuilt; nothing of it is committed.
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

`prompt: [...]` and `post: [...]` stand for the git example in Design 6.5.

#### 6.2 Stages and statuses

- **[Decision] Every optional stage is enabled** (spec, plan, review, qa,
  postmortem). The repository already works spec and plan for every item, runs
  code reviews, and has the owner accept the result, which are review and qa.
- **[Decision] Statuses:** inbox `Triage`, request `To Do`, implement
  `In Progress`, completed `Done` and discarded `Won't Do` keep the statuses 2.x
  mapped to them (`tcw-config.yaml:14-21`, statuses and `pre-backlog`). `In Review` maps to 3.0 **review**,
  which its name describes; 2.x `review` items move to the new qa status. Three new
  statuses: `Specifying`, `Planning` (TCW-71's sketch uses `Specifying`) and
  `In QA`.
- **[Decision] One way into each status.** TCW-71's `advance` refuses when the
  current status offers no transition, or more than one, to the target's status.
  TCW's workflow therefore gets one global transition into each mapped status (a
  Jira transition that every status can take) and loses the others (2.x's `Start`
  and `Accept`, `tcw-config.yaml:12-13`, `:20-21`). That gives exactly one route
  from any status to any other, which forced skips also need.

#### 6.3 The Definition of Done becomes a gate and prompt text

**[Decision]** Each `dod.yaml` entry (`docs/work/dod.yaml`) goes where 3.0 can
enforce or state it:

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
  slug, whose `/` would make a subfolder (TCW-75). Both `upcoming/README.md` files
  and `CLAUDE.md:150` change to match. Entry files already written under 2.x names
  keep them; `scripts/cut_version.py` merges files whatever their names.
- The `Configuration-Key-Change` description drops `docs/work/dod.yaml`.

#### 6.5 The git example

TCW adopts TCW-75's opt-in example as TCW-75 writes it:

- pulling is prompt text, in a file bound into every stage's `prompt` list;
- committing is a `post` hook on every stage an item can be moved into (request to
  discarded), which succeeds when there is nothing to commit, as is usual in Jira
  mode where a move changes no file;
- **[Decision] no push hook.** The owner pushes, as today
  (`CLAUDE.md:150`: publishing stays a human step).

### 7. TCW's own files

| File | Change |
| --- | --- |
| `tcw-config.yaml` | Design 6 |
| `scripts/require_artifact.py` | asks `tcw work path "$TCW_SLUG" <stage>` for the document's path and fails unless that file exists and is not empty. It keeps failing closed when `TCW_SLUG` is unset or `tcw` fails. `path` is the shared layout in both modes, so the check still composes no path itself, which was the script's reason for asking the CLI (`:9-13`). The `TCW_NODE_ROOT` mention goes |
| `docs/lifecycle/templates/spec.md`, `spec-bug.md` | each gains a first line saying it is the outline for `spec/spec.md`, since it is now read as prompt text rather than copied in as a skeleton |
| `docs/lifecycle/review.md` | new (Design 6.3) |
| `tests/test_repo_lifecycle.py` | rewritten against the 3.0 parser: the config parses with no problems; every bound file exists and is not empty; plan binds no template; both templates carry the spec's seven required headings; the documentation entries and triggers are as in Design 6.4. The test comparing the template with `tcw.work.templates._SPEC` goes with that module (TCW-74): in 3.0 the template adds to the built-in text instead of replacing it |
| `CLAUDE.md` and `AGENTS.md` (kept identical) | "Work Planning and Implementation" (lines 11-51) rewritten for 3.0: `advance --dry-run` instead of `stage gate`; the bindings table gains review and completed; the exception rewritten (Design 8.6); the GitHub-issue paragraph without `dod.yaml` and `refined-outcome.md`. Versioning (line 150): `upcoming/<work-item-folder>.md`. The `--worktree` section is TCW-75's |
| `docs/procedures/create-work.md` | made consistent with TCW-74's `create-work` procedure (or its replacement); step-number references fixed |
| `.gitignore` | `docs/work/discarded/*` and its exception removed; `tcw-config.local.yaml` added |
| `docs/capabilities/**/meta.yaml` | `Planning doc:` lines removed (65 files) |
| `docs/release-notes/upcoming/`, `docs/changelogs/upcoming/` | this item's entries, linking the guide; README wording (Design 6.4) |

### 8. Sequencing: how this epic's board is tracked until the migration

1. **Until TCW-70 lands,** the 2.x CLI works and may be used as usual. (TCW-69
   changes no command.)
2. **From TCW-70 onwards,** on the epic branch:
   - **[Decision] the board stays in 2.x form and is changed by hand**, as
     `CLAUDE.md:29-41` and the epic require: folders moved between status
     directories, `state.yaml` edited, documents written;
   - **[Decision] read-only commands may use a 2.8 CLI that is not the working
     tree:** the primary checkout's install on `main` or a released 2.8.x in an
     isolated environment, run against the epic branch's files. Reading prompts
     (`stage prompt`), `list`, `show` and `validate` is not driving the lifecycle,
     and that CLI is not under modification. No moves are made with it;
   - Jira statuses for TCW-68 to TCW-77 are moved by hand in Jira, or left to lag;
     either way step 6 reconciles them, disk winning.
3. **[Decision] Completed epic items are kept** in `completed/` despite
   `retain: {completed: false}` (`tcw-config.yaml:77-78`), so their documents and
   `capabilities.yaml` reach 3.0. They are the first completed items 3.0 drift can
   read.
4. **The repository's `tcw-config.yaml` stays in 2.x form until this slice.** From
   TCW-70 the 3.0 code rejects it, so no test may load it in the meantime. That is
   a requirement on TCW-70 (Notes), which must retire the 2.x assertions in
   `tests/test_repo_lifecycle.py`; this slice writes their 3.0 replacement.
5. **The migration itself:**
   1. starts when TCW-69 to TCW-75 and TCW-77 are complete (moved to `completed/`
      by hand). "Code frozen" means no further change under `tcw/`, `skills/`,
      `agents/` or `web/` until the epic merges;
   2. **[Decision] merges `main` into the epic branch first,** so items created on
      `main` during the epic are migrated too, and from then until the epic merges,
      `main`'s board is frozen. If `main`'s board must change in that window, it is
      merged again and the guide's steps are run for the new items;
   3. runs on its own branch off the epic branch, one commit per step. If a step
      exposes a defect in 3.0 code, that branch is abandoned, the code is fixed on
      the epic branch, and the migration restarts from step 0. Jira writes survive
      the restart and are safe to repeat (Design 1.8);
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
7. **The epic merges to `main` with the migration, and 3.0.0 is cut straight
   after** (`scripts/cut_version.py`), so `main` never holds a half-migrated
   board, and the window in which `main` holds a 3.0 board but PyPI holds 2.8 is as
   short as possible.

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

Criteria 1 to 10 are checked by reading the guide; criteria 11 to 26 on the epic
branch after the migration commit; 27 on the epic branch before it.

**The guide**

1. `docs/migration-guide-2.8-to-3.0.0.md` exists and opens with the prerequisites
   and rules of Design 1.2.
2. It has steps 0 to 11 in the order of Design 2, and every step has a **Check**
   line containing a command and its expected output.
3. It has exactly the stops of Design 1.5: one consolidated-plan stop (step 1), a
   stop for Jira changes the agent cannot make (step 2), and the general rule that
   a check failing after one retry stops the migration. No step asks a question
   per item.
4. Each of these names appears in a mapping table with its 3.0 form or "removed"
   and what replaces it (checked by `grep` for each name):
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
   and `TCW_STAGE` for `post` hooks, and `TCW_TRANSITION` to `TCW_STAGE`.
6. The `artifacts` row says that an earlier entry's condition is added as
   `not_tags` to later ones, and shows this repository's `spec` templates as the
   example.
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
    `tcw-config.local.yaml`.
19. `diff CLAUDE.md AGENTS.md` prints nothing, and neither file contains
    `dod.yaml`, `refined-outcome.md`, `stage gate` or `<work-item-slug>`. Neither
    `upcoming/README.md` contains `<work-item-slug>`.
20. A pytest test runs `scripts/require_artifact.py spec` as a `pre` hook in a
    temporary 3.0 project: it exits non-zero for an item with no `spec/spec.md`,
    with an empty one, and with `TCW_SLUG` unset, and exits 0 when the file has
    text. The script contains neither `--json` nor `TCW_NODE_ROOT`.
21. `tests/test_repo_lifecycle.py` passes as rewritten (Design 7), and the full
    suite passes when run as CI runs it, with bare `pytest`.
22. `tcw capabilities drift` prints nothing, or each line it prints is recorded in
    the implement round with its cause and the slice that owns the fix.
23. `git diff --stat <freeze commit>..HEAD -- tcw skills agents web` prints nothing
    for the migration's commits.
24. The implement round records the approved plan verbatim, every Jira write, and
    every amendment made to the guide during the run.
25. The implement round records the filesystem rehearsal of Design 5.2: the 2.8
    commands that built it, and a clean `tcw validate` at the end.
26. TCW-76's first move after the migration, `tcw work advance <TCW-76 slug>` to
    review, exits 0, and its `post` hook commits or reports nothing to commit.

**Sequencing**

27. Until the migration starts, `docs/work/completed/` on the epic branch holds the
    folder of every finished slice among TCW-69 to TCW-75 and TCW-77, and
    `graveyard.yaml` gains no entry for any of them.

### Coverage

| Design | Criteria |
| --- | --- |
| 1 The guide's form | 1, 3, 9 |
| 2 Steps | 2, 3 |
| 3.1–3.4 Stages, fields, documents, store root | 4, 8, 11, 12, 13, 14 |
| 3.5 Configuration | 4, 6, 16 |
| 3.6 Hook variables | 4, 5 |
| 3.7 Capability records | 17, 22 |
| 3.8–3.9 Project files, references | 7, 18, 19 |
| 4 Jira binding | 12, 14, 15, 24 |
| 5 Proving | 10, 24, 25 |
| 6 TCW's configuration | 16, 26 |
| 7 TCW's files | 18, 19, 20, 21 |
| 8 Sequencing | 23, 26, 27 |

## Risks

- **The guide depends on six unwritten specs.** TCW-70 to TCW-75 and TCW-77 have
  only tickets today, and the guide's storage details (inbox items, `item.yaml`
  keys, `work.jira` keys, renamed commands, surviving procedures) come from them.
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
  people move tickets by hand in Jira. Mitigation: it is an owner question.
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
- **A large one-off ticket creation.** TCW needs up to 18 new tickets (8 items, 10
  inbox entries) unless the prune step removes some.

## Notes

### Decisions made in this spec, for the owner to confirm

Each is marked **[Decision]** above:

- checks are read-only shell commands; the CLI is used only at the end (1.4);
- three kinds of stop only (1.5);
- Jira writes have REST forms (1.7) and are safe to repeat and logged (1.8);
- a survey step with one consolidated plan, including a prune list (2.1);
- the Jira compatibility check runs in a scratch folder after the config rewrite
  (2.3);
- Jira mode writes a full `item.yaml` first and reduces it at binding (2.4);
- ignored discarded folders are listed and, if kept, tracked (3.1);
- `initial-request.md` wins over `intake.md`, which is appended when different
  (3.3);
- acceptance history maps to `qa` rounds, `judges: 1`, rework before acceptance
  (3.3);
- hook variables are mapped by meaning, not position (3.6);
- `Planning doc` and `Tracker` are removed from capability records (3.7);
- `tcw-config.local.yaml` is added to `.gitignore` (3.8);
- empty disk values and `<KEY> — ` title prefixes are not disagreements; extra
  Jira labels are removed only on agreement (4.2);
- request text goes to an empty body, otherwise to a comment (4.4);
- a filesystem-mode rehearsal proves the rest of the guide (5.2);
- TCW enables every optional stage, with `Specifying`, `Planning` and `In QA` as
  new statuses and `In Review` as review (6.2);
- one global transition into each status (6.2);
- the Definition of Done splits into the built-in gates, `tcw validate` as the
  project gate, and `docs/lifecycle/review.md` (6.3);
- `Tracker-Change` becomes `Jira-Change`; upcoming files are named by folder
  (6.4);
- no push hook (6.5);
- the epic's board stays 2.x and is changed by hand from TCW-70; read-only commands
  may use a 2.8 CLI outside the working tree (8.2);
- completed epic items are kept, not deleted (8.3);
- `main` is merged in and its board frozen before the migration (8.5);
- after the migration commit, TCW-76 is moved with the 3.0 CLI (8.6).

### Contradictions in the ticket, and how this spec resolves them

- **`capabilities.yaml`:** the artifact table says `spec/capabilities.yaml`; the
  "Update from TCW-69's spec" section and the owner's confirmed decision say the
  item root. It is already at the item root in 2.x (a side file,
  `base.py:3113-3117`), so nothing moves.
- **Order:** step 2 runs `tcw validate --remote` before step 3 writes the
  configuration it reads. Resolved in Design 2, step 3.
- **Acceptance records:** the ticket says qa, the decision record says review.
  Resolved for qa (Design 3.3).
- **Hook variables:** the ticket's list pairs them by position. Resolved by
  meaning (Design 3.6).
- **"Missing priority becomes medium"** would overwrite Jira-owned priorities in
  Jira mode. Applied in filesystem mode only (Design 4.2).

### Cross-slice findings

Nothing has been posted to these tickets.

- **TCW-69.**
  - Its Capability changes section says there is one `work/` capability; there are
    46. Removing or rewriting the 2.x ones needs an owner among TCW-70, TCW-71 and
    TCW-73.
  - The value of `TCW_SLUG` in 3.0 hooks is not stated (full slug or folder). 2.x
    passes the bare folder name (`cli.py:1616`). The guide needs it.
  - The variables and JSON payload given to `generate` prompt bindings
    (`resolve.py:185-196`) are not specified for 3.0.
  - Its Notes list the hook variable renames by position; the guide maps them by
    meaning (Design 3.6), and TCW-75's hook documentation should too.
- **TCW-70.**
  - Once it removes the 2.x store, no test may load this repository's 2.x
    `tcw-config.yaml` (`tests/test_repo_lifecycle.py`). It must retire those
    assertions; this slice restores 3.0 ones.
  - Suggested: a folder under the work path with no `item.yaml` (such as a 2.x
    status directory) is reported with a message naming the migration guide. A
    2.x config that never set `tracker`, `lifecycle` or `retain` is valid 3.0
    configuration, so nothing else would point that project at the guide. This is
    an error message, not conversion code.
  - Where an inbox item's text is stored (step 8) is TCW-70's to fix.
- **TCW-71.**
  - The 2.x tracker keys whose 3.0 fate no ticket states: `timeout-seconds`,
    `comments`, `link`, `create.issue-type`, `create.issue-types`,
    `create.components`, `create.on-new`.
  - The workflow compatibility check must work on a project with no items
    (Design 2, step 3).
  - "Exactly one transition to the target" fails on many default Jira workflows
    that offer two routes into one status; the setup walkthrough should say how to
    fix that, as Design 6.2 does for TCW.
- **TCW-72.** `tcw init` adds `tcw-config.local.yaml` to `.gitignore` only for new
  projects; the guide does it for migrated ones.
- **TCW-73.**
  - Remove `Planning doc` and `Tracker` from `CAP_FIELDS` (`base.py:844-847`),
    following this spec's decision.
  - Its ticket still says `spec/capabilities.yaml` (already noted by TCW-69).
  - The final names of the "node" keys (`connected-projects`, and others) are
    needed for the guide's table.
- **TCW-74.**
  - Its ticket says the spec stage writes `spec/capabilities.yaml`; the confirmed
    location is `<item>/capabilities.yaml`.
  - Whether the `create-work` procedure survives decides TCW's
    `work.procedures.create-work` binding.
  - The eval harness (`evals/seed_fixture.py`, `evals/evals.json`, `evals/grade.py`)
    builds 2.x boards and asserts 2.x paths; no ticket owns updating it. TCW-74,
    which changes what the harness measures, is the natural owner.
  - Suggested: the setup skill names the guide when it meets a 2.x project.
- **TCW-75.**
  - Its ticket says "add the `spec/capabilities.yaml` chain"; the location is the
    item root.
  - Rewriting `docs/lifecycle/abstraction.md` must keep, or update together, the
    phrases `tests/test_repo_lifecycle.py:76-86` asserts.
- **TCW-77.** Its ticket edits `spec/capabilities.yaml` through a form and lists it
  in the autocomplete table; the location is the item root. Its removal of the
  `Planning doc` and `Tracker` fields from the viewer agrees with Design 3.7.

### Questions only the owner can answer

1. Are `Specifying`, `Planning` and `In QA` the right new status names, and should
   every optional stage be enabled for TCW?
2. Does anyone else use the TCW Jira project or its workflow, so that replacing
   its transitions with one global transition per status matters? Is it a
   company-managed or team-managed project, and does TCW-68's Epic issue type use a
   different workflow?
3. Do the TCW Project, TCW Item, Effort and Complexity fields exist, and can the
   agent create fields and statuses, or does the owner do step 2?
4. The prune list. Candidates on today's board whose subject 3.0 removes: TCW-33
   (`scaffold`), TCW-10 (tracker workflow vs `statuses`), TCW-40 (claim
   exclusivity), TCW-26 (mapped tracker fields), TCW-54 (aggregating child
   boards in `tcw serve`); unbound `2026-09-21-two-tracker-create-runs-…`,
   `2026-09-22-let-a-leftover-start-record-…`,
   `2026-09-22-refuse-an-unconfigured-start-…` and
   `2026-09-24-give-a-strict-tracker-claim-…`; and inbox entries about start
   records, worktrees, the merge-back, `state.yaml` and status folders. Which go?
5. Should TCW's git example push as well as commit?
6. Are "tests pass" and "docs synced" acceptable as review-stage instructions
   rather than a gate (Design 6.3)?
7. Are there untracked discarded items on the machine that will run the migration
   (ignored by `.gitignore:29`), and should they be kept?
8. During TCW-70 to TCW-77, should Jira tickets be moved by hand as work
   progresses, or left to be reconciled at migration?

### Other notes

- **The ticket's numbers are out of date** (Problem 3). The guide's survey
  recounts at migration time, since the board keeps changing until then.
- **The owner's own notes outside the repository** describe 2.x behavior (for
  example, how a Jira sync reverses a manual move). They are not part of this
  slice, but will need revisiting after the migration.
- **Driving this item.** This item's implementation changes no code under `tcw/`,
  but the code is in flux until the freeze, so its board is driven by editing
  files, per `CLAUDE.md`, until Design 8.6 applies.
