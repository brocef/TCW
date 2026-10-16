# Migrating from 2.8 to 3.0.0

TCW 3.0.0 changes how work items are stored and moved, and **nothing in 3.0
converts a 2.x project for you**: 3.0 refuses a 2.x configuration and does not
read a 2.x work store. This guide is how a project on 2.8 gets to 3.0: its
configuration, its board, its own scripts and documents, and the instructions
its agents have been given.

What changes, in short:

- **Items no longer move between folders.** In 2.x an item's status was the
  folder it sat in (`backlog/`, `active/`, `review/`, …). In 3.0 an item's
  folder stays where it was created, and its **stage** (`inbox`, `request`,
  `spec`, `plan`, `implement`, `review`, `qa`, `completed`, `discarded`, and
  the side stage `postmortem`) is recorded about it.
- **`item.yaml` replaces `state.yaml`.** In Jira mode the item's properties
  live on its Jira ticket, and `item.yaml` holds only the ticket's address.
- **Documents live in stage folders**: `spec/spec.md`, `plan/plan.md`, and
  numbered **rounds** such as `implement/round-1.md` and `qa/round-1.md`, with
  a verdict at the top of each `review` and `qa` round.
- **One command moves an item**: `tcw work advance`, with
  `tcw work discard` as a shorthand for discarding.
- **TCW never changes git state.** It does not commit, push, branch, make
  worktrees or delete finished items. A project that wants commits adds a
  hook (an example is in
  [Configuration](guide/configuration.md#example-keeping-git-in-step-with-each-stage-change-something-your-project-adds)).
- **The configuration is reshaped**: `work.lifecycle` and `work.tracker` give
  way to `work.stages`, `work.hooks`, `work.backend` and `work.jira`, and
  several keys are removed.
- **Some commands that keep their names are stricter**: see
  [Behavior that changed](#behavior-that-changed).

**Who this guide is for.** It is written for an agent, under Claude Code,
Codex or any other harness, working with a user: the person who owns the
project and decides for it. The agent does the steps; the user answers the
few questions the guide asks. The agent may have any level of Jira access: a
Jira change it cannot make is handed to the user as a checklist. Every step
uses only a shell, `curl` and `tcw`.

**Projects older than 2.8** upgrade to 2.8 first, with the earlier migration
guides (for example [2.4 to 2.5](migration-guide-2.4.X-to-2.5.0.md); the
README lists them all) and 2.8's own `tcw validate`.

Words this guide uses:

- **The work path** is the project's configured `work.path`, `docs/work` unless
  the project set another. Paths in commands are written with `docs/work`;
  substitute the project's own.
- **The board** is everything under the work path: item folders, the inbox,
  and the files 2.x kept beside them.
- **A slug** names an item. In 2.x it was the item's folder name. In 3.0 the
  full slug is the project's ID and the folder name, `<project>/<folder>`, and
  the folder name alone is enough inside the project.
- **Filesystem mode** and **Jira mode** are the two 3.0 backends, chosen by
  `work.backend`. In filesystem mode everything about an item is a file in its
  folder. In Jira mode the item's properties, stage, request and comments live
  on its Jira ticket, and the folder holds its other documents.
- **The migration log** is one file that records this migration: the plan the
  user approved, every change made in Jira, and every correction made to this
  guide along the way.

The mapping tables in [What each 2.x name becomes](#what-each-2x-name-becomes)
say what every 2.x folder, field, document, key, variable, command, skill and
agent becomes. The steps point into them.

## Before you start

Check each of these before step 0; step 0's check confirms the ones a command
can show.

- **The project is on 2.8.x.** `tcw --version` prints `2.8.` and a patch
  number. A project on an earlier version upgrades to 2.8 first.
- **The 3.0 CLI is installed, beside 2.8.** Both are needed: 2.8 for step 0's
  last check of the 2.x board, and 3.0 from step 3 on. One way is a virtual
  environment, a private Python installation in a folder of its own:

  ```sh
  python3 -m venv ~/.tcw-3
  ~/.tcw-3/bin/pip install 'tcw-cli>=3,<4'
  ~/.tcw-3/bin/tcw --version     # prints 3. and the rest of the version
  ```

  Where a step runs `tcw` from step 3 on, it means this 3.0 CLI: run it as
  `~/.tcw-3/bin/tcw`, or with `~/.tcw-3/bin` first on `PATH`. Step 11 makes
  3.0 the `tcw` everyone runs.
- **The working tree has no uncommitted changes**: `git status --porcelain`
  prints nothing.
- **No 2.x item worktree is open.** 2.x could give an item its own git
  worktree on a branch named `work/<slug>`; 3.0 knows nothing about them. Merge
  or remove each one first, so that `git worktree list | grep -E '\[work/'`
  prints nothing. The migration itself may run in a worktree of its own; the
  plan lists any other worktrees.
- **A branch or tag marks the 2.x state**, so the project can return to it,
  for example `git tag tcw-2.x-final`.
- **Every connected project is on this machine, and is migrated with this
  one.** 3.0 reads the configuration of every project the configuration
  declares (under `connected-projects`): one that is missing is reported as
  unresolved and cannot be checked, and one still on 2.x makes
  `tcw validate`, and every `tcw work` command that reads the board, fail on
  its `connected-projects` key. 2.8's `tcw validate`
  reports a missing one, and `tcw provision` fetches it. Plan to run this
  guide in each connected project; at the least, each must have finished its
  own step 3 before this project's step 11.
- **In Jira mode, the Jira credentials are set**: the two environment
  variables the configuration names under `credentials` hold an email address
  and an API token for an account that can read and edit the project's tickets.
- **In Jira mode, `jq` 1.6 or later is installed**: `jq --version` prints
  `jq-1.6` or a later version. The Jira commands use `--rawfile` and `IN`,
  which earlier versions lack.

## Rules

1. **Do the steps in order**, from step 0 to step 12. Steps 2 and 6 are for
   Jira mode; in filesystem mode, run only their checks.
2. **After each step, run its check, and do not go on until it passes.** A
   check is a read-only shell command and the output it must print. It holds
   however the step was done, by hand or with a throwaway script of your own;
   commit no such script.
3. Stop and ask the user at these four points only, and ask nothing item by
   item:
   - the consolidated plan, at step 1: one question that covers every
     decision the migration needs, answered once;
   - a Jira change you cannot make yourself, at step 2;
   - the review of agent instructions and memories, at step 12: one question
     listing every finding;
   - **a check that fails after one retry**: report what you expected, what
     you saw, and stop.
4. **A step interrupted partway is rerun from its beginning**, not stopped:
   a lost session, or a Jira error such as a 5xx response or a timeout, is not
   a failure. Every action is written so that doing it again after it took
   effect changes nothing: a folder already moved or renamed is skipped, a
   ticket that already exists is reused, a comment already posted is not
   posted again. Only when the rerun's check fails as well does the last stop
   above apply.
5. **Commits are the project's choice.** TCW never commits, stages or
   branches. Committing once after each step's check passes is recommended,
   so that a bad step can be reverted.
6. **Jira writes are REST requests** ([Talking to Jira](#talking-to-jira)),
   with the Jira web page, or any Jira tool you have, as an equivalent. A
   REST request works the same under every harness. **Before each write, read
   the ticket and skip the write when its effect is already there**, so that
   Jira, not the log, says what was done:
   - **creating a ticket**: search with
     `project = <KEY> AND reporter = currentUser() AND created >= "<the day before the start date>"`
     and compare summaries exactly. A match is the ticket an earlier run made,
     and it is reused. The start date is the one step 0 writes into the log,
     unchanged across restarts, and with the reporter it tells the
     migration's own ticket apart from someone else's with the same summary.
     The search starts a day early because Jira compares `created` in the
     account's time zone, which may be a day behind the machine that wrote
     the start date (`date -j -v-1d -f %F <start date> +%F` on macOS,
     `date -d '<start date> -1 day' +%F` on Linux, prints the day before);
   - **posting a comment**: every comment the migration posts begins with a
     fixed first line naming its kind. Read the ticket's comments, and skip
     the post when one by the same account already begins with that line.
     Read every page of comments, not only the first
     ([Talking to Jira](#talking-to-jira));
   - **moving a ticket, or setting a field, label or link**: skip it when the
     ticket already has that status, value or link.
7. **Keep the migration log.** It is one file, named in the approved plan and
   kept outside the work path (for example `docs/tcw-3.0-migration-log.md`),
   because 3.0 treats any file at the top of the work path as a mistake. It
   records the start date and starting commit (step 0), the approved plan
   (step 1), every Jira write as it is made (the ticket's key and what
   changed), each step's check output (for step 12's check when it fails,
   only what step 12 says), and every place where this guide was
   wrong or unclear and what was done instead. Commit it with each step. If a
   run is abandoned and the migration starts again, keep the old branch, and
   copy the log forward under a new heading `## Run <N>`, so every run's record
   survives. A log lost anyway costs only the record: the reads of rule 6,
   not the log, decide whether a Jira write is repeated. **The log is
   committed, so it never holds text from a file outside the repository**, or
   from a file git does not track: for those, step 12 records only the file's
   path and line number in the log, and keeps any text it needs in a private
   file that is never committed.
8. **Run `tcw` only where a step says to**: 2.8 at step 0, 3.0 in a scratch
   folder at step 3, and 3.0 on the project from step 11 on. Every check
   before that is a plain shell command, because neither CLI can read a board
   that is half converted.

## 2.x behavior that had no key

Some of 2.x's behavior happened without the project setting anything, so no
key in the configuration points at it, and nothing in the mapping tables would
make you look for it. 3.0 drops all of it:

- **Automatic commits.** 2.x committed every move by default:
  `work.auto-commit-transitions` was on unless a project turned it off. A
  project that never set the key still got a commit per move. 3.0 never
  commits, so such a project silently stops committing unless it adopts the
  [git example](guide/configuration.md#example-keeping-git-in-step-with-each-stage-change-something-your-project-adds).
  The plan asks.
- **Publishing.** `work.publish-transitions` was on by default too: 2.x pushed
  the board after a move. 3.0 never pushes; the git example has an optional
  push entry.
- **Retention.** 2.x could delete finished items, recording each in
  `graveyard.yaml`, under `work.retain` (by default it kept everything). 3.0
  never deletes an item. A project that wants old items gone removes their
  folders itself. Items 2.x already deleted stay deleted.
- **Ignored completed and discarded folders.** 2.x's `tcw init` wrote
  `.gitignore` rules for `docs/work/completed/*` and `docs/work/discarded/*`
  (each with a `!…/.gitkeep` exception and a comment line above them), so in
  a project that kept those rules, finished items exist only on the machine
  that finished them. 3.0 never moves a folder, so the rules stop matching
  anything, and those folders would be invisible to the migration unless
  step 0 looks for them.
- **Folders that moved.** A 2.x move moved the item's folder between status
  folders, so a path into an item changed with every move. A 3.0 folder stays
  where it was made; only `tcw work rename` changes its name.
- **Claims and item worktrees.** 2.x could claim a Jira ticket when work
  started, and could give an item its own git worktree. 3.0 does neither.

## The steps

### Step 0: Prepare

1. Check every point of [Before you start](#before-you-start).
2. Run 2.8's `tcw validate`. Fix anything it reports under 2.8 now, while the
   tools for it still exist.
3. Find the item folders that `.gitignore` hides:
   `git status --ignored --porcelain -- docs/work` lists them, each on a line
   beginning with two exclamation marks. A run made in a worktree also runs it in the primary
   checkout (`git -C <primary checkout> status --ignored --porcelain -- docs/work`),
   since an ignored folder exists only in the checkout that made it. Keep the
   list for the plan.
4. Only then start the migration log, with the start date and the commit the
   run starts from:

   ```markdown
   # TCW 3.0 migration log

   ## Run 1

   Started: <the date `date +%F` prints>
   Starting commit: <the hash `git rev-parse HEAD` prints>
   ```

   A later run copies the log forward under `## Run 2` and so on, with its own
   starting commit and the first run's start date.

**Check:** before the log is started, `git status --porcelain` prints nothing
and `git worktree list | grep -E '\[work/'` prints nothing. Afterwards,
`grep -E '^(Started|Starting commit): ' <log> | tail -n 2` prints the two lines
of this run.

### Step 1: Survey, then ask once

Read the whole board and the whole configuration, and in Jira mode every
ticket of the Jira project (a search, [Talking to Jira](#talking-to-jira)).
Then write one plan and present it to the user as one message. It covers:

- **The backend**: filesystem or Jira mode. A 2.x project with `work.tracker`
  usually becomes a Jira-mode project, but need not.
- **The stages**: which optional stages to turn on (`spec`, `plan`, `review`,
  `qa`, `postmortem`), and in Jira mode the status for each stage turned on,
  and the statuses, transitions and fields that must be added (step 2).
- **Each item**: its stage ([Status folders](#status-folders)), its converted
  fields ([Item fields](#item-fields)), and everything dropped or listed (a
  free-text blocker, an `initiative` beside a `parent`, an `owner` in Jira
  mode). In filesystem mode, each folder to rename because its name is not a
  date followed by lower-case words. In Jira mode, every difference between
  the item and its ticket ([Reconciling](#reconciling-the-folder-with-the-ticket)),
  and every `sync` record still `pending`.
- **In Jira mode, the tickets to create** for items and inbox entries, any
  item without a ticket to delete instead, where each request goes
  ([The request](#the-request)), the exact text of every comment the
  migration will post, and the tickets without items
  ([Tickets without items](#tickets-without-items)).
- **A prune list**: items and inbox entries whose subject 3.0 removes, such as
  tracker sync, claims, start records, worktrees, retention, the graveyard,
  the Definition of Done, `scaffold` or status folders, proposed for
  discarding rather than migrating, each with the reason to record. Migrating
  them would carry forward work that no longer applies. A pruned item keeps
  its folder at stage `discarded`; in Jira mode its ticket, created if it has
  none, is moved to the discarded status with the reason as its comment.
- **The ignored completed and discarded folders** step 0 found: which to
  keep as tracked items. The rest are moved out of the work path at step 4, to
  a folder outside the repository that the plan names.
- **The inbox entries**, and what each becomes (step 8).
- **The rewrites**: the configuration, key by key
  ([Configuration](#configuration)); each hook, with its variables and status
  values ([Hook variables](#hook-variables)); the templates
  ([Templates become prompt entries](#templates-become-prompt-entries));
  whether to adopt the git example
  ([2.x behavior that had no key](#2x-behavior-that-had-no-key)); the
  capability records ([Capability records](#capability-records)); and the
  project's own files ([The project's own files](#the-projects-own-files)).
- **Items that will be at `qa` while `review` is on**, which the completion
  gate will refuse until a review round is written
  ([Acceptance history goes to qa](#acceptance-history-goes-to-qa)).
- **`<hook files>`**, the fixed list of files step 10's check searches: the
  configuration files (`tcw-config.yaml`, and `tcw-config.local.yaml` where it
  exists), every file a `command:` or `generate:` binding in them runs, every
  file a `file:` binding in them names, and the agent guides (`AGENTS.md`,
  `CLAUDE.md`). Never the whole repository: changelogs, release notes,
  finished items' documents, tests and this guide name the 2.x variables on
  purpose.
- **What step 9's check skips**: the migration log, and, when the migration
  is itself tracked as a work item, that item's folder, since both name the
  old folders on purpose.
- **The migration log's file name**, and the open items and live documents
  step 9 searches.

**Stop and ask**: one question, for the whole plan. Change nothing before the
answer. Record the plan and the user's answer, word for word, in the log under
a heading `## Approved plan`.

**Check:** `grep -c '^## Approved plan' <log>` prints `1` (a second run, under
its own `## Run <N>` heading, records its plan under `### Approved plan` and
the check counts that instead).

### Step 2: Jira mode: prepare Jira

In filesystem mode there is nothing to do.

In Jira mode, read the project's workflow first (the Jira web page, or the
reads in [Talking to Jira](#talking-to-jira)), then make, or list, what the
new configuration needs:

- **a status for each stage turned on** that has none yet;
- **a route for every move** `tcw work advance` makes. For each move, TCW
  takes the one transition into the target stage's status; when several lead
  there, the one whose screen asks for nothing but a comment; and it refuses
  with exit code 3 when that still leaves none or more than one. The simplest
  workflow that satisfies this is one **global transition** (a transition
  every status can take) into each mapped status, with no screen fields, and
  no other transition into those statuses: an older transition with no screen
  into the same status would be an equal candidate, and `advance` would
  refuse. Keep the transition that creates a ticket;
- **the custom fields**: `TCW Project` and `TCW Item`, text fields of one line,
  and, if the project tracks effort and complexity, two single-choice fields
  whose options are `Low`, `Medium`, `High` and `Very High` (3.0 matches them
  ignoring capitals, so `low` … `very high` serve as well);
- **the fields on the screens**: every one of those custom fields, and also
  `Summary`, `Labels`, `Assignee`, `Parent` and, when the project has a
  priority field, `Priority`, must be on the create screen and the edit
  screen of every issue type the project uses. `Parent` is not needed on the
  type at the top of the project's hierarchy.
- **what step 3 cannot check**: at step 3 there are no item folders yet, so
  `tcw validate --remote` reads at most two issue types: the configured one
  (`work.jira.issue-type`, `Task` by default) and the project's sub-task
  type. It checks the create screen of both; the edit screen of each only
  when the Jira project already has a ticket of that type to read it on,
  reporting `unchecked:` for that edit screen otherwise; and the statuses and
  moves of the configured type's workflow alone. It never reads an epic's
  screens or workflow, or those of any other type the project uses. Confirm
  those by reading them (the create and edit screen reads in
  [Talking to Jira](#talking-to-jira)), and put each one you cannot read on
  the checklist below: one line per type for its create screen, its edit
  screen and its workflow's statuses and moves.

**Stop and ask** for every change you cannot make yourself: give the user a
checklist, one line per change with how to confirm it was made, and wait until
they say each line is done. Record the checklist and each confirmation in the
log. A workflow change also changes how 2.8 moves these tickets, so make it
only once nothing will run 2.8 against the project again.

**Check:** this step's check is the Jira-workflow reading at the end of step 3,
because it reads the new configuration.

### Step 3: Rewrite the configuration

Rewrite `tcw-config.yaml`, and `tcw-config.local.yaml` where it exists, key by
key as the plan says ([Configuration](#configuration)): stages and their
bindings under `work.stages`, hook limits under `work.hooks`, templates as
prompt entries, `connected-projects` as `projects`, and the git example if the
plan adopts it. In Jira mode, add `work.backend: jira`, the `work.jira` block
(`site`, `project`, `credentials`, `fields`, and `priorities`, `issue-type`
or `timeout` where they differ from the defaults), and each stage's `status`.
Give each template its first line saying what it outlines. The `configure`
skill's reference documents, linked from [Configuration](#configuration),
describe every key.

Then check the new configuration with the 3.0 CLI, away from the board, which
3.0 cannot read yet. Build a scratch folder outside the repository holding the
new `tcw-config.yaml`, every file it binds at the same relative path, and empty
folders at the configured work, taxonomy and capabilities paths, and make it a
git repository:

```sh
SCRATCH=$(mktemp -d)
cp tcw-config.yaml "$SCRATCH/"
for f in docs/lifecycle/*.md; do mkdir -p "$SCRATCH/$(dirname "$f")"; cp "$f" "$SCRATCH/$f"; done   # each bound file
mkdir -p "$SCRATCH/docs/work" "$SCRATCH/docs/taxonomy" "$SCRATCH/docs/capabilities"
git -C "$SCRATCH" init -q
```

A connected project's path is relative to the project, so from the scratch
folder it points nowhere, and 3.0 reports it as unresolved. For each one, set
`TCW_PROJECT_<ID>` (its ID in capitals, with `-` written `_`) to the
project's real folder, for example `export TCW_PROJECT_SHOP_API=/work/shop-api`.
Set this project's own variable to the scratch folder as well
(`export TCW_PROJECT_SHOP=$SCRATCH` for a project whose ID is `shop`), so that
each connected project's path back to this one leads to the scratch copy.

Then, in the scratch folder, run `tcw validate` (filesystem mode) or
`tcw validate --remote` (Jira mode), which prints one finding per line. Read
every line:

- **a finding about the configuration** (one naming `tcw-config.yaml` or a
  bound file) is fixed now, and the run repeated;
- **in Jira mode, a Jira-workflow finding**: a move with two candidate
  transitions, a missing status, or a screen that asks for more than a comment
  is fixed in Jira before going on (back to step 2's checklist); a move it
  could not check, a `warning` starting `unchecked:`, is listed for step 11;
- **a finding naming another project's file** belongs to that project's own
  migration (for example `the key 'connected-projects' was renamed`, while it
  is still on 2.x);
- **any other finding** is noted in the log and left to step 11, which
  validates the real project.

**Check:**
`grep -nE '^[[:space:]]*(tracker|lifecycle|retain|auto-commit-transitions|publish-transitions|trunk-branch):|builtin: true|^connected-projects:' tcw-config.yaml`
prints nothing, and the scratch folder's run prints no finding about the
configuration and, in Jira mode, no Jira-workflow finding other than
`unchecked:` ones. In Jira mode this is step 2's check too.

### Step 4: Flatten the store and give every item a stage

For every item folder under a status folder, and every child nested inside
another item's folder:

1. **Move it to the top of the work path**, `docs/work/<folder>`. A nested
   child gets its parent from the folder it was nested in, recorded at step 5.
   In filesystem mode, a folder whose name is not a date and lower-case words
   joined by `-` (`2026-10-20-refund-a-payment`, at most 128 characters) is
   renamed to its `created` date and its title's words
   ([Folder names](#folder-names) gives the rule for the words), and the old
   and new names go in the log for step 9. In Jira mode every folder is
   renamed at step 6 instead.
2. **Write its `item.yaml`** with its `title` and its `stage`, from the
   [Status folders](#status-folders) rule. Step 5 adds the rest.

Then:

3. **Copy every pair in `renames.yaml`** into the log, as `<old slug> -> <new
   slug>`, one per line, for step 9.
4. **Move the ignored folders the plan does not keep** out of the work path,
   to the folder the plan names outside the repository. The kept ones are
   moved like any other item. Use a plain `mv` for them: `git mv` refuses a
   folder git does not track, and `git mv -k` skips it without a word. **In a
   run made in a worktree**, the ignored folders exist only in the primary
   checkout: copy each kept one from there into the worktree's work path, and
   move each one not kept out of the primary checkout's work path, or 3.0 will
   find it there once the primary checkout is on the migrated branch.
5. **Delete** the status folders (`backlog/`, `active/`, `review/`,
   `blocked/`, `completed/`, `discarded/`) with their `.gitkeep` files,
   `graveyard.yaml`, `dod.yaml` and `renames.yaml`. Leave `inbox/` for step 8.
   Delete a status folder only once it holds nothing but its `.gitkeep`:
   `find docs/work/backlog docs/work/active docs/work/review docs/work/blocked docs/work/completed docs/work/discarded -mindepth 1 ! -name .gitkeep 2>/dev/null`
   must print nothing first. This step's check cannot see an item that was
   deleted with its folder.

A step rerun skips a folder already at the top of the work path.

**Check:**
`find docs/work -mindepth 1 -maxdepth 1 -type d \( -name backlog -o -name active -o -name review -o -name blocked -o -name completed -o -name discarded \)`
prints nothing, and
`for d in docs/work/*/; do [ "$d" = docs/work/inbox/ ] || [ -f "$d/item.yaml" ] || echo "$d"; done`
prints nothing.

### Step 5: Convert item fields

For every item, convert the rest of `state.yaml` into `item.yaml`, one key per
line as the example in [Item fields](#item-fields) shows (this step's check
reads it that way), row by row of that table: `priority` as a name, `effort`,
`complexity` and `tags` as they are, `parent` and `blocked-by` as full slugs
using each folder's name after step 4, `initiative` as `parent` where the plan
says, and in filesystem mode `owner` as `assignee`. Then delete `state.yaml`.

For a `discarded` item, record its 2.x resolution as a comment whose first line
is `Carried over from TCW 2.x: discarded as <resolution>`, followed by any
reason the item's documents give, or the reason the plan gives for a pruned
item. In filesystem mode a comment is a file in the item's `comments/` folder
named with the time in UTC, such as `comments/20261020T143000Z.md`; in Jira
mode it is posted at step 6.

In filesystem mode, delete `tracker.yaml` too. In Jira mode it stays until
step 6, which reads the ticket's key from it.

**Check:** `find docs/work -name state.yaml` prints nothing (in filesystem
mode, `find docs/work \( -name state.yaml -o -name tracker.yaml \)` prints
nothing), and `grep -nE '^priority: [0-9]' docs/work/*/item.yaml` prints
nothing.

### Step 6: Jira mode: bind items to tickets

In filesystem mode there is nothing to do.

In Jira mode, following [Jira mode: binding items to tickets](#jira-mode-binding-items-to-tickets),
and reading before every write (rule 6):

1. **Find or create every ticket.** An item's ticket is the first of these
   that exists:
   - `ticket.key` in its `tracker.yaml` (in 2.x, `ticket` is a mapping of
     `id`, `key` and `url`);
   - the `ticket:` line of its `item.yaml`, which this pass writes when it
     creates a ticket, and which pass 7 leaves once `tracker.yaml` is gone;
   - the key at the front of its folder's name, once pass 6 has renamed it.

   On a rerun, an item whose `tracker.yaml` an earlier run deleted is found
   this way and never gets a second ticket. For an item with none of the
   three, create the ticket, or delete the folder, as the plan says; on
   creating one, add the line `ticket: <site>/browse/<KEY>` to its `item.yaml`
   at once. Create a parent's ticket before its children's, and give a child
   its parent in the create request, with the issue type
   [Talking to Jira](#talking-to-jira) gives for a child. For every inbox
   entry the plan keeps, create a ticket at the inbox stage's status with the
   entry's text as its description and, as its summary, the title step 8 would
   give it (the entry's first `# ` heading, else its file name's words), and
   record its key in the log for step 8. Do this for every item first, since
   the next pass links tickets to one another.
2. **Reconcile each ticket with its item**: summary, priority, labels,
   effort and complexity, parent and `Blocks` links, as the plan says.
3. **Move each ticket to its stage's status**, with no comment, when it is not
   there already.
4. **Post the discard comments** from step 5.
5. **Set `TCW Project`** to the project's ID and **`TCW Item`** to the item's
   full slug, `<project>/<KEY>-<title words>`, computed from the ticket's
   summary as it now stands ([Folder names](#folder-names)).
6. **Rename the folder** to `<KEY>-<title words>`, and record the old and new
   names in the log for step 9.
7. **Reduce `item.yaml`** to the one line `ticket: <site>/browse/<KEY>`, and
   delete `tracker.yaml`.

**Check:** `find docs/work -name tracker.yaml` prints nothing. In Jira mode
also: `ls docs/work | grep -vxE 'inbox|<KEY>-[1-9][0-9]*-[a-z0-9]+(-[a-z0-9]+)*'`,
with the project's key in place of `<KEY>`, prints nothing (the pattern 3.0
reads a folder name with: no leading zero in the number, and title words
joined by single hyphens); and

```sh
for d in docs/work/*/; do
  n=$(basename "$d"); [ "$n" = inbox ] && continue
  k=$(printf '%s' "$n" | sed -E 's/^([A-Z][A-Z0-9_]*-[0-9]+)-.*/\1/')
  [ "$(grep -cv '^[[:space:]]*$' "$d/item.yaml")" = 1 ] &&
    grep -qxE "ticket: https://[^ ]+/browse/$k" "$d/item.yaml" || echo "$n"
done
```

prints nothing: every `item.yaml` is the one `ticket:` line, and the key in
it is the folder's own.

### Step 7: Move documents

For every item, move each document as [Documents](#documents) says:

- the request: in filesystem mode into `request/request.md` (both request
  files combined as described there); in Jira mode into the ticket, as
  [The request](#the-request) says, and the files deleted;
- `spec.md`, `plan.md`, `outcome.md` and `post-mortem.md` into their stage
  folders;
- `rework.md` and `refined-outcome.md`: in filesystem mode into `qa/` rounds
  with front matter; in Jira mode into ticket comments, oldest first, each
  beginning with its fixed first line, and the files deleted;
- `capabilities.yaml` corrected where needed, and `rollup.md` deleted.

**Check:**
`find docs/work -maxdepth 2 \( -name intake.md -o -name initial-request.md -o -name spec.md -o -name plan.md -o -name outcome.md -o -name refined-outcome.md -o -name rework.md -o -name post-mortem.md -o -name rollup.md \)`
prints nothing, and every verdict round has its front matter:

```sh
for f in docs/work/*/review/round-*.md docs/work/*/qa/round-*.md; do
  [ -e "$f" ] || continue
  head -n 1 "$f" | grep -qx -- '---' &&
    sed -n '2,/^---$/p' "$f" | grep -qxE 'verdict: (accepted|rejected)' &&
    sed -n '2,/^---$/p' "$f" | grep -qxE 'judges: [0-9]+' || echo "$f"
done
```

prints nothing.

### Step 8: Convert the inbox

- **Filesystem mode:** each `inbox/<name>.md` becomes an item at stage
  `inbox`: a folder `docs/work/<name>/` (renamed as in step 4 when `<name>` is
  not a date and lower-case words, using the date the entry was added,
  `git log --diff-filter=A -1 --format=%cs -- <entry>`, or today's date,
  `date +%F`, for an entry that was never committed and so prints nothing)
  holding `item.yaml` with `title` (the entry's first `# ` heading, or its
  name's words), `stage: inbox` and `priority: medium`, and
  `request/request.md` holding the entry's text.
- **Jira mode:** each entry's ticket was created at step 6, or the plan
  pruned it; delete the file.

Then delete `inbox/` and its `.gitkeep`.

**Check:** `ls docs/work | grep -x inbox` prints nothing.

### Step 9: Rewrite live references

Collect every old name in one file, one per line: the folders renamed at steps
4 and 6, and the old slugs copied from `renames.yaml` at step 4. Then, in the
documents of open items (those not at `completed` or `discarded`), the
configuration, and the project's live documents, rewrite each old name to its
new one, and each `tcw://work/<old slug>` to the new slug
([Live references](#live-references)). In open items, also rewrite each
relative link between one item's documents, which step 7 moved into stage
folders: a link to `spec.md` in the plan becomes a link to
`../spec/spec.md`. Leave alone what step 9's plan entry skips,
and the documents of finished items, changelogs and release notes.

**Check:** `grep -rnF -f <the file of old names> <open item folders> <live documents>`,
with the folders and documents the approved plan lists and without what it
skips, prints nothing; and
`grep -rnE '\]\((\./)?(intake|initial-request|spec|plan|outcome|refined-outcome|rework|post-mortem)\.md' <open item folders>`
prints nothing.

### Step 10: Review the project's own files

Fix what the approved plan covers ([The project's own files](#the-projects-own-files),
[Capability records](#capability-records)): the hook scripts' variables and
status values, the `.gitignore` rules, the `Planning doc:` and `Tracker:` lines
in capability records, links to the renamed Feature, and the agent guides'
text. Point out to the user any other text that relies on removed behavior.

**Check:** `grep -nE 'TCW_(STATUS|TRANSITION|NODE_ROOT|RESOLUTION)\b' <hook files>`
over the plan's `<hook files>` prints nothing;
`grep -rlnE '^(Planning doc|Tracker):' docs/capabilities`, with the project's
capabilities path, prints nothing; `grep -nE 'docs/work/(completed|discarded)' .gitignore`
prints nothing; and `grep -cx '/tcw-config.local.yaml' .gitignore` prints `1`.

### Step 11: Validate

Make 3.0 the `tcw` on `PATH`, for example `pipx install --force 'tcw-cli>=3,<4'`
or `pip install --upgrade 'tcw-cli>=3,<4'`, the way 2.8 was installed: hooks
run whatever `tcw` they find. Update the TCW plugin in each harness the
project uses to the 3.0 release, the way it was installed, so that its skills
match the CLI.

Then run `tcw validate`, and in Jira mode `tcw validate --remote`. Fix each
error. Fix each warning, or list it in the log with its reason for the user,
including every `unchecked:` move from step 3. `tcw work list --all --json`
lists every item; compare each one's stage with the stage the approved plan
gave it.

**Check:** `tcw validate; echo "exit $?"` prints its findings and ends with
`exit 0`, and in Jira mode `tcw validate --remote; echo "exit $?"` ends with
`exit 0` too.

### Step 12: Revisit agent instructions and memories

Agents are told how to use TCW in many places besides the project's own
documents: instruction files, skills, commands, harness settings, and the
memories a harness saves between sessions. Each can still tell an agent to run
a 2.x command or look in a status folder, and nothing in steps 0 to 11 reads
them. This step finds every such passage, asks the user once what to do with
all of them, and does only what the user approves.

The commands here are for `bash`. Run them from the project's root.

**Where to look.** Three groups, whichever of them exist:

- **The project:**
  - `CLAUDE.md` and `AGENTS.md`, and every file they link to or import (a line
    of `CLAUDE.md` that is `@` followed by a path imports that file);
  - `.claude/skills/`, `.claude/commands/`, `.claude/agents/`, `.codex/` and
    `.agents/skills/`;
  - the `hooks` and `permissions.allow` entries of `.claude/settings.json` and
    `.claude/settings.local.json`;
  - the prompt and procedure files the 2.x configuration bound (step 1's
    `<hook files>` list names them).
- **The user's own files:** `~/.claude/CLAUDE.md`, `~/.codex/AGENTS.md`,
  `~/.claude/skills/`, `~/.claude/commands/`, `~/.claude/agents/`,
  `~/.codex/skills/`, `~/.agents/skills/`, `~/.codex/prompts/`,
  `~/.claude/settings.json` and `~/.codex/rules/`.
- **Saved memories:** `~/.codex/memories/`, and the `memory/` folder (with its
  index, `MEMORY.md`) of every Claude Code project folder under
  `~/.claude/projects/` that belongs to this project. Those folders are found
  by what their session records say, not by how they are named: a record that
  starts in one of the project's checkouts says so in a `"cwd"` field, and
  every checkout is a path `git worktree list --porcelain` prints.

**A run made in a worktree** also searches the primary checkout's untracked
per-user files, such as `.claude/settings.local.json`, by the primary
checkout's absolute path: a worktree holds only the files git tracks, so the
ones each person keeps for themselves exist only in the primary checkout.
`git -C <primary checkout> status --ignored --porcelain -- .claude .codex`
lists them.

**Files outside the repository** are the person running the migration's own.
Every other contributor repeats this step for their own files after the
migration lands.

Build the list of places:

```sh
PRIMARY=$(git worktree list --porcelain | sed -n '1s/^worktree //p')
PLACES=()
for p in CLAUDE.md AGENTS.md .claude/skills .claude/commands .claude/agents .codex .agents/skills \
         .claude/settings.json .claude/settings.local.json \
         ~/.claude/CLAUDE.md ~/.codex/AGENTS.md ~/.claude/skills ~/.claude/commands ~/.claude/agents \
         ~/.codex/skills ~/.agents/skills ~/.codex/prompts ~/.claude/settings.json ~/.codex/rules \
         ~/.codex/memories; do
  [ -e "$p" ] && PLACES+=("$p")
done
# Each file CLAUDE.md and AGENTS.md link to or import, and each bound prompt
# and procedure file, added by hand:
#   PLACES+=(docs/lifecycle/implementation.md)
# The primary checkout's own files, when this is a worktree:
if [ "$PRIMARY" != "$(pwd -P)" ]; then
  while read -r _ f; do PLACES+=("$PRIMARY/$f"); done \
    < <(git -C "$PRIMARY" status --ignored --porcelain -- .claude .codex)
fi
# The Claude Code memory folders of every checkout:
while read -r d; do PLACES+=("$d"); done < <(
  git worktree list --porcelain | sed -n 's/^worktree //p' | while read -r path; do
    find ~/.claude/projects -mindepth 2 -maxdepth 2 -name '*.jsonl' \
      -exec grep -lF -e "\"cwd\":\"$path\"" -e "\"cwd\":\"$path/" {} +
  done | while read -r t; do d=$(dirname "$t")/memory; [ -d "$d" ] && echo "$d"; done | sort -u)
printf '%s\n' "${PLACES[@]}"
```

**What to look for**: every name in the first column of the tables in
[What each 2.x name becomes](#what-each-2x-name-becomes), including the status
folders with `inbox/`, `state.yaml`, `dod.yaml` and `--worktree`; the bare 2.x
verbs (start, submit, rework, complete, drop, claim) and stage names (verify);
and text that relies on automatic commits, publishing or retention, which a
memory often describes without naming a command ("TCW commits each move, so
there is no need to commit").

The searches use two lists of `grep -E` alternatives. `NAMES` holds names that
mean 2.x wherever they appear, each matched where it starts a word (or, for
`--worktree`, where no letter, digit or `_` comes before it); `WORDS` holds
ordinary words that may mean 2.x, matched as whole words:

```sh
NAMES='state\.yaml|tracker\.yaml|blocked_by|graveyard\.yaml|dod\.yaml|renames\.yaml|intake\.md|initial-request\.md|spec\.md|plan\.md|outcome\.md|refined-outcome\.md|rework\.md|post-mortem|rollup\.md|inbox/|backlog/|active/|review/|blocked/|completed/|discarded/|work\.tracker|work\.lifecycle|work\.retain|auto-commit-transitions|publish-transitions|trunk-branch|builtin: true|auto-delete|status-synced|catch-up|unlinked|TCW_SLUG|TCW_STATUS|TCW_TRANSITION|TCW_NODE_ROOT|TCW_RESOLUTION|TCW_WORK_OWNER|connected-projects|connected-project-registry|Planning doc:|Tracker:|tcw:body|commands-verify-work|work-stage|consolidate-plans|work (inbox|tracker|nodes|reconcile|delegate|escalate|tombstone|delete|scaffold|start|submit|rework|complete|drop)|(taxonomy|capabilities|work) (init|check)|stage (gate|validate)|provision --refresh|no-recurse|local-only|work list --status|procedure prompt|--worktree|Definition of Done|tracker sync|transitions\.(claim|start)'
WORDS='start|submit|rework|complete|drop|verify|sync|claim|release|reconcile|scaffold|tombstone|escalate|delegate|nodes|backlog|wontfix|superseded|duplicate|graveyard|verifier|decompose|delegation|initiative|worktree|retain|retention|resolution|epic|auto-commit|publish|trunk'
```

**First, find the files to read**, every file in the places that names `tcw`
or any of either list (case matters):

```sh
grep -rlsE "\btcw\b|(^|[^[:alnum:]_])($NAMES)|\b($WORDS)\b" "${PLACES[@]}"
```

**Read each printed file in full**, and judge every passage that tells an
agent how TCW behaves, not only the lines that matched: a sentence such as
"move the item to review when done" names nothing the search can find
reliably. For each passage that is wrong for 3.0, propose one action:

- **delete** it;
- **rewrite** it, with the proposed text;
- **keep** it, with the reason (it describes history, or is correct for 3.0).

**Stop and ask**: one question listing every finding (the file, the passage,
the proposed action). Change nothing before the answer, and apply only what
the user approves. A finding the user rejects is left as it is.

Then record the step in the log, under a heading `## Agent instructions`: one
line per finding (the file and line as found, the decision, what was done),
ending with a fenced block marked `expected-names` that holds every line the
check's search should still print afterwards, as `<file>:<text>`: kept lines as
they stand, and rewritten lines whose approved text still matches `NAMES`.
Write it from the search's own output once the changes are applied, after
reading each line in it, so that no line is in the block without having been
judged.

**Nothing private goes into the log.** The log is committed, and most places
outside the repository hold the user's own text, often about other projects:
`~/.claude/CLAUDE.md`, `~/.codex/rules/`, `~/.codex/memories/` and the Claude
Code memory folders among them. So for a file outside the repository, or one
git does not track (the primary checkout's own per-user files), the log's
finding line gives only the file's path, the line number, the decision and
what was done, never the passage. That file's expected lines go into a
private file instead, outside the repository and never committed, in the
same `<file>:<text>` form, one per line:

```sh
PRIVATE=~/.tcw-3.0-migration-expected-names.txt   # outside the repository; never committed
```

The `expected-names` block in the log holds only lines of files git tracks in
the repository. Delete the private file, and the saved check output
`~/.tcw-3.0-migration-check.txt` if there is one, once the migration is
accepted.

**Check:** `grep -c '^## Agent instructions' <log>` prints `1`, and, with
`LOG` set to the log's path and `PLACES`, `NAMES`, `WORDS` and `PRIVATE` as
above,

```sh
diff <(grep -rIsHE "(^|[^[:alnum:]_])($NAMES)" "${PLACES[@]}" | LC_ALL=C sort) \
     <({ awk '/^```expected-names$/{f=1;next} f&&/^```$/{f=0} f' "$LOG"; cat "$PRIVATE" 2>/dev/null; } | LC_ALL=C sort)
```

prints nothing. No line numbers are compared, so an edit above a kept line
does not fail the check; and a rewritten line that still says `tcw` is not a
failure, since `NAMES` does not contain it. **When the check fails, its output
quotes the lines that differ, private ones included**, so it never goes into
the log as it stands: save it beside `$PRIVATE`, outside the repository
(`diff … > ~/.tcw-3.0-migration-check.txt`), and record in the log only the
files it names, which
`sed -nE 's/^[<>] ([^:]*):.*/\1/p' ~/.tcw-3.0-migration-check.txt | sort -u`
prints. If a configuration-bound file
changed, `tcw validate; echo "exit $?"` ends with `exit 0`.

## Talking to Jira

Every Jira read and write the steps make, as a `curl` request to Jira Cloud's
REST interface. Set these first, from the configuration. `credentials` names
two environment variables rather than holding the values, so read the names
from the project's own `work.jira.credentials` (TCW's own project uses
`TCW_JIRA_EMAIL` and `TCW_JIRA_API_KEY`); `printenv` then reads each one's
value without printing it:

```sh
SITE=https://example.atlassian.net            # work.jira.site
KEY=SHOP                                      # work.jira.project
TYPE=Task                                     # work.jira.issue-type (default Task)
EMAIL_ENV=TCW_JIRA_EMAIL                      # work.jira.credentials.email-env
TOKEN_ENV=TCW_JIRA_API_KEY                    # work.jira.credentials.token-env
AUTH="$(printenv "$EMAIL_ENV"):$(printenv "$TOKEN_ENV")"
J=$(mktemp -d)                                # answers and request bodies, outside the repository
```

**Text goes through version 3 of the interface, as Atlassian Document
Format.** Version 2 reads a description or comment as Jira's wiki markup, so
Markdown's `#`, `|`, `*x*`, `-`, `--` and `{{…}}` would be shown as headings,
tables, bold text, lists, dashes and code. Version 3 takes Atlassian Document
Format (ADF), a JSON document in which text is never read as markup, and 3.0
writes every description and comment that way. These `jq` functions build a
document from text in the same shape 3.0 does (`text_document` in
`tcw/work/jira/mapping.py`: a paragraph for each run of lines between blank
lines, a line break inside a paragraph as a `hardBreak`), and read a
document's text back the way 3.0 does (`document_text`, beside it: paragraphs
joined by a blank line). Set them once, beside the variables above:

```sh
ADF='
def adf(t): t | gsub("\r\n?"; "\n") | split("\n")
  | reduce .[] as $l ([[]];
      if ($l | test("\\S")) then .[-1] += [$l]
      elif (.[-1] | length) > 0 then . + [[]] else . end)
  | map(select(length > 0) | {type: "paragraph",
      content: ([.[] | {type: "hardBreak"}, {type: "text", text: .}] | .[1:])})
  | {type: "doc", version: 1, content: .};
def adf_inline: (.type | IN("text", "hardBreak", "mention", "emoji", "inlineCard", "date", "status"));
def adf_line: if .type == "text" then .text // ""
  elif .type == "hardBreak" then "\n"
  else (.attrs // {} | .text // .shortName // .url // "") end;
def adf_block: if all(.content[]?; adf_inline)
  then [.content[]? | adf_line] | join("")
  else [.content[]? | if adf_inline then adf_line else adf_block end] | join("\n") end;
def adf_text(d): d | [.content[]? | adf_block] | join("\n\n");
'
```

Build every request's JSON with `jq`, never by pasting text between quotes,
so that quotes and line breaks in the text are escaped. The requests that
send text read it from a file in `$J`: before each one, write the text there
yourself, the description to `$J/request.md` and a comment, fixed first line
included, to `$J/comment.txt`, replacing what the previous request left.
Every request has an equivalent on the ticket's Jira web page, given after it. `<project field>`,
`<item field>`, `<effort field>` and `<complexity field>` stand for the
`customfield_<number>` IDs of the four custom fields, found with the request
in the fourth row.

| What | Request | On the web page |
| --- | --- | --- |
| Who you are (your account ID) | `curl -s -u "$AUTH" "$SITE/rest/api/3/myself"` | your profile |
| Search | `curl -s -u "$AUTH" -X POST -H 'Content-Type: application/json' "$SITE/rest/api/3/search/jql" -d "$BODY"`, where `BODY` is `{"jql": "<query>", "fields": ["summary", "status"], "maxResults": 100}`; while the answer says `"isLast": false`, repeat with its `nextPageToken` added | the issue search, in JQL mode |
| Read one ticket | `curl -s -u "$AUTH" "$SITE/rest/api/3/issue/$KEY-42?fields=summary,status,priority,labels,assignee,parent,issuelinks,issuetype,description,<project field>,<item field>,<effort field>,<complexity field>"`; leave out the effort and complexity fields when the project has none. The custom fields must be named, or the answer leaves them out and a field already set looks empty | the ticket |
| Find a custom field's ID | `curl -s -u "$AUTH" "$SITE/rest/api/3/field"`, then the entry whose `name` is the field's name; its `id` is `customfield_<number>` | the field's settings |
| Read the project's issue types | `curl -s -u "$AUTH" "$SITE/rest/api/3/project/$KEY"`: each entry of `issueTypes` has a `name`, a `hierarchyLevel` and `subtask` | the issue types, in project settings |
| Create a ticket | `curl -s -u "$AUTH" -X POST -H 'Content-Type: application/json' "$SITE/rest/api/3/issue" -d "$BODY"`, where `BODY` is `jq -n --arg k "$KEY" --arg t "$TYPE" --arg s "$SUMMARY" --rawfile d "$J/request.md" "$ADF"'{fields: {project: {key: $k}, issuetype: {name: $t}, summary: $s, description: adf($d)}}'`; for a child, add `parent: {key: $p}` (with `--arg p <the parent's key>`) beside `summary`. The answer holds the new key | Create |
| List a ticket's transitions | `curl -s -u "$AUTH" "$SITE/rest/api/3/issue/$KEY-42/transitions"`: each has an `id`, a `name`, and `to.name`, the status it leads to | the status button |
| Move a ticket | `curl -s -u "$AUTH" -X POST -H 'Content-Type: application/json' "$SITE/rest/api/3/issue/$KEY-42/transitions" -d '{"transition": {"id": "<id>"}}'` | the status button |
| Set fields | `curl -s -u "$AUTH" -X PUT -H 'Content-Type: application/json' "$SITE/rest/api/3/issue/$KEY-42" -d "$BODY"`, where `BODY` holds `{"fields": {…}}` with any of: `"summary": "<text>"`, `"priority": {"name": "High"}`, `"labels": ["billing"]`, `"parent": {"key": "<KEY>-7"}`, `"assignee": {"accountId": "<id>"}`, a text field `"customfield_<n>": "<text>"`, a single-choice field `"customfield_<n>": {"value": "<option>"}`, with the option's value exactly as the field offers it (`Medium`, or `medium` in a project such as TCW's own whose options are in lower case), and a description `"description": <document>`, built as `jq -n --rawfile d "$J/request.md" "$ADF"'{fields: {description: adf($d)}}'` | the ticket's fields |
| Find a person's account ID | `curl -s -u "$AUTH" "$SITE/rest/api/3/user/assignable/search?project=$KEY&query=<name>"` | the assignee picker |
| List a ticket's comments | `curl -s -u "$AUTH" "$SITE/rest/api/3/issue/$KEY-42/comment?startAt=0&maxResults=100"`: the answer has `comments`, `startAt` and `total`. While `startAt` plus the number of comments is less than `total`, repeat with `startAt` raised by that number. Each comment has `body`, a document, and `author.accountId` | the comments |
| Post a comment | `curl -s -u "$AUTH" -X POST -H 'Content-Type: application/json' "$SITE/rest/api/3/issue/$KEY-42/comment" -d "$BODY"`, where `BODY` is `jq -n --rawfile b "$J/comment.txt" "$ADF"'{body: adf($b)}'` | Add a comment |
| Link a blocker | `curl -s -u "$AUTH" -X POST -H 'Content-Type: application/json' "$SITE/rest/api/3/issueLink" -d '{"type": {"name": "Blocks"}, "inwardIssue": {"key": "<the blocker>"}, "outwardIssue": {"key": "<the blocked ticket>"}}'` | Link, "blocks" |
| Read a create screen | `curl -s -u "$AUTH" "$SITE/rest/api/3/issue/createmeta/$KEY/issuetypes/<type id>?startAt=0&maxResults=200"`, with the type's `id` from the project's issue types: each entry of `fields` (or `values`) is a field the create screen shows, with its `fieldId` and `name`; while `startAt` plus the entries read is less than `total`, repeat with `startAt` moved on | Create, with that type chosen |
| Read an edit screen | `curl -s -u "$AUTH" "$SITE/rest/api/3/issue/$KEY-42/editmeta"`, on a ticket of that type: each key of `fields` is a field the edit screen shows | the ticket, in edit |
| Read the project's statuses | `curl -s -u "$AUTH" "$SITE/rest/api/3/project/$KEY/statuses"`: the statuses of each issue type | the workflow, in project settings |

**The issue type of a new ticket** is `work.jira.issue-type` (`TYPE` above),
as 3.0 uses it. A child's ticket takes the type one level below its parent's
in Jira's hierarchy, as 3.0 chooses it: read the parent's
`issuetype.hierarchyLevel`, then pick from the project's issue types. A
parent at level 1 (an epic) gives a child of type `TYPE`; a parent at level 0
gives the project's one sub-task type (`subtask` true); a parent at level 2
or above gives the one type at the level below it. When there is no single
such type, or the parent is a sub-task, the child cannot be placed under that
parent: list it in the plan.

**Reading a comment's first line** (rule 6), for one page of the comments
answer saved as `$J/comments.json`, prints each comment's author and first
line:

```sh
jq -r "$ADF"'.comments[] | [.author.accountId, (adf_text(.body) | split("\n")[0])] | @tsv' "$J/comments.json"
```

**Whether a description already contains a request file**
([The request](#the-request)), for the ticket whose key is in `T` (such as
`T=$KEY-42`), read with `?fields=description` and saved as `$J/ticket.json`,
prints `true` or `false`. An `intake.md` that has a line
`Imported on <date> from [<the ticket's key>](https://…/browse/<the ticket's key>)`
was written by 2.x's import from that very ticket, so it prints `true`
without comparing anything: 2.x read the description through version 2 of the interface, as
wiki markup, so its copy never matches the text read back here. That holds
only while the file is exactly as the import wrote it, so the command compares
the file as it stands now, uncommitted changes included, with the file 2.x's
import commit added (its subject is `tcw work: import <KEY> → <slug>`). Any
difference, or no such commit (2.x commits the import only when
`work.auto-commit-transitions` is on), means someone may have written in it,
and it is compared like any other file. Moving the item's folder changes
nothing here. Any other
request file is compared by text: the description's, read back from its
document, with the file's, both with every white space character removed:

```sh
F=<request file>
C=$(git log -1 --format=%H --grep="^tcw work: import $T " 2>/dev/null)
P=$([ -n "$C" ] && git show --format= --name-only --diff-filter=A "$C" | grep '/intake\.md$')
if [ "$(basename "$F")" = intake.md ] &&
   grep -qE "^Imported on [^ ]+ from \[$T\]\(" "$F" &&
   [ -n "$P" ] && git show "$C:$P" | cmp -s - "$F"; then
  echo true
else
  jq -r --rawfile r "$F" "$ADF"'
    def squash: gsub("\\s+"; "");
    (adf_text(.fields.description) | squash) as $d | ($r | squash) as $q
    | $q == "" or ($d | contains($q))' "$J/ticket.json"
fi
```

A request that fails says so in its answer: check for `errorMessages` and
`errors` before going on. An answer of 401 means the credentials are wrong; 403
that the account may not do this, which makes it a change to give the user
(step 2); 404 that the ticket or field does not exist; a 5xx answer or a
timeout is an interruption (rule 4).

## What each 2.x name becomes

Each table's first column is the 2.x name; the second says what it becomes in
3.0, or that it is removed and what replaces it. Step 12 searches agent
instructions for every name in a first column.

### Status folders

| 2.x folder | 3.0 stage |
| --- | --- |
| `inbox/` (loose `.md` files) | filesystem mode: an item at `inbox`, converted at step 8; Jira mode: a ticket at the inbox stage's status, with no item folder |
| `backlog/` | the furthest of `request`, `spec` and `plan` whose document exists: `plan` when the item has `plan.md`, else `spec` when it has `spec.md`, else `request` |
| `active/` | `implement` |
| `review/` | `qa`: 2.x review was the requester accepting the finished work, which is what 3.0's qa stage is for (see [Acceptance history goes to qa](#acceptance-history-goes-to-qa)) |
| `blocked/` | not a 2.8 status, but a leftover from earlier versions. Deleted with the other status folders. An item found in one is listed in the plan and staged by the `backlog/` rule, or at `implement` when it has `outcome.md` |
| `completed/` (tracked, or ignored by `.gitignore`) | `completed` |
| `discarded/` (tracked, or ignored by `.gitignore`) | `discarded`; the 2.x resolution (`wontfix`, `duplicate` or `superseded`) and any reason become a comment |

- **For `backlog/`, the rule picks a stage whose documents are already
  written**, so the item is not ahead of its documents. Items from `active/`
  and `review/` usually are: 2.x never required a spec or plan, and
  `tcw validate` warns once for each earlier stage with nothing written
  (`stage is at implement but has nothing from spec`). Those warnings are true
  and expected; step 11 lists them. When the stage the rule picks is turned
  off in the new configuration, the item takes the next flow stage that is on.
- **Completed and discarded folders ignored by `.gitignore`** exist only on
  the machine that finished them. Step 0 finds them and the plan lists them.
  The user chooses which to keep; a kept one becomes a tracked item, since 3.0
  has no folder left to ignore, and the `.gitignore` rules are removed at step
  10. The rest are moved out of the work path and are not migrated.
- **A child nested inside its parent's folder**, with no `parent` field, was
  made by a version before 2.x recorded `parent`. Step 4 moves it out to the
  top of the work path, and its `parent` becomes the folder it was nested in.

### Item fields

`state.yaml` and `tracker.yaml` become one `item.yaml`. In filesystem mode it
holds the item's properties, with a key left out when it has no value:

```yaml
title: Refund a payment
stage: spec
priority: high
effort: medium
complexity: low
tags: [billing]
assignee: Sam Lee
parent: shop/2026-09-01-payments
blocked-by: [shop/2026-09-20-fix-the-ledger]
```

In Jira mode, after step 6, it holds one line, `ticket: <site>/browse/<KEY>`;
step 4 writes the filesystem form first, and step 6 reconciles it with the
ticket and then reduces it to that line.

| 2.x field | 3.0 |
| --- | --- |
| `slug` | dropped: the folder name is the item's name, and its full slug is `<project>/<folder>` |
| `title` | `title` (Jira: the ticket's summary) |
| `created` | dropped: the date at the front of the folder's name (filesystem), or the ticket's creation date (Jira) |
| `priority` (a number; higher is more urgent) | a name: 40 or more is `highest`, 30 to 39 `high`, 20 to 29 `medium`, 10 to 19 `low`, below 10 `lowest`. With no value: `medium` in filesystem mode; in Jira mode the ticket's own priority stands, and a Jira project with no priority field has none |
| `effort`, `complexity` | unchanged: `low`, `medium`, `high` or `very-high` (Jira: the custom fields `work.jira.fields` names) |
| `tags` | `tags` (Jira: the ticket's labels) |
| `owner` | filesystem: `assignee`. Jira: dropped, because it is a git identity rather than a Jira account; listed in the plan |
| `blocked_by` | `blocked-by`, a list of full slugs using the folders' final names: each 2.x entry `slug: <folder>` becomes `<project>/<folder>`. An entry `external: <text>` is dropped and listed, since a 3.0 blocker is an item. Jira: a `Blocks` link; a link to a ticket that has no item shows as `untracked` in `tcw work show` |
| `parent` | `parent`, as a full slug. A child nested inside its parent's folder takes that folder. Jira: the ticket's parent |
| `initiative` | `parent`, as a full slug in the project it names, when the item has no `parent`; when it has both, `parent` stays and the `initiative` is listed in the plan |
| `type` | dropped: in 3.0 an item with children is an epic |
| `resolution` | dropped: the stage says it (`completed` or `discarded`), and a discarded item's resolution becomes a comment |
| `started`, `completed`, `phase`, `worktree`, `branch` | dropped |
| `tracker.yaml`: `ticket` | Jira mode: `ticket: <site>/browse/<KEY>` in `item.yaml` |
| `tracker.yaml`: `schema`, `provider`, `project`, `part`, `bound`, `unlinked`, `sync`, `comment`, `status-synced`, `catch-up`, `owed`, `created` | dropped when the file is deleted: at step 6, after binding, in Jira mode; at step 5 in filesystem mode. A `sync` record whose `state` is `pending` is a move that never reached Jira, and the plan shows it as "Jira lagged" |

### Documents

| 2.x document | Filesystem mode | Jira mode |
| --- | --- | --- |
| `intake.md`, `initial-request.md` | `request/request.md` | the ticket's description (see [The request](#the-request)) |
| `spec.md` | `spec/spec.md` | the same |
| `plan.md` | `plan/plan.md` | the same |
| `outcome.md` | `implement/round-1.md`, with no front matter | the same |
| `rework.md` | `qa/round-N.md` with `verdict: rejected` | a ticket comment |
| `refined-outcome.md` | `qa/round-N.md` with `verdict: accepted` | a ticket comment |
| `post-mortem.md` | `postmortem/postmortem.md` | the same |
| `capabilities.yaml` | stays at the item's root; an `added:` key becomes `new:`. A file that is a list rather than a mapping (the shape 2.x's reconcile command wrote, which 2.x read as declaring nothing) is deleted, because 3.0 accepts only a mapping of `new`, `changed`, `removed` and `taxonomy` | the same |
| `rollup.md` | deleted: 2.x's reconcile command generated it, and that command is gone | the same |
| any other file at the item's root | stays where it is: 3.0 reads only `item.yaml` and its own stage folders | the same |

- **When both request files exist**, `initial-request.md` becomes the request,
  as 2.x read it first, and `intake.md` is appended under a heading
  `## Original intake` unless its text is already contained in the request.
  Nothing is lost.
- **Round numbers.** `outcome.md` is the only implement round, so it becomes
  `implement/round-1.md`. When an item has both `rework.md` and
  `refined-outcome.md`, `rework.md` is `qa/round-1.md` and `refined-outcome.md`
  is `qa/round-2.md`, since a rejection comes before the acceptance that ends
  the item.
- **Relative links** inside a moved document keep working when they point
  outside the work path: the status-folder level that is removed is replaced
  by the new stage-folder level. Links between one item's documents (from
  `plan.md` to `spec.md`, now `../spec/spec.md`) and links into other items
  are rewritten in open items only, at step 9.

#### Acceptance history goes to qa

`refined-outcome.md` and `rework.md` recorded the user accepting or rejecting
the finished work. That is 3.0's **qa** stage, where the product's requester
checks the behavior. 3.0's **review** stage is engineers checking the code
against the spec and plan, which 2.x had no stage for. Mapping the history to
review would invent a code review that never happened, and would let the
completion gate pass items whose code was never reviewed.

Each converted round is a **verdict round**: front matter, a short block of
YAML between two `---` lines, then the 2.x document's text unchanged:

```markdown
---
verdict: accepted
judges: 1
---
<the text of refined-outcome.md>
```

- `verdict` is `accepted` for `refined-outcome.md` and `rejected` for
  `rework.md`.
- `judges` is the number of the implement round the verdict is about. It is
  `judges: 1` when the item has `outcome.md`, and `judges: 0` when it has
  none. A verdict counts only when `judges` equals the item's latest implement
  round, or 0 when it has none; any other number makes the verdict `stale`,
  which blocks the item.
- **Jira mode keeps no qa files**: qa is kept in Jira. Each verdict becomes a
  ticket comment instead, posted oldest first, whose first line is
  `Carried over from TCW 2.x: qa round <N>, verdict <accepted or rejected>`,
  followed by the document's text.
- **An item moved to qa while review is turned on** has no review round, so
  the completion gate refuses to complete it until a review round is written,
  or the move is forced with a reason. The plan says so for each such item.

### Store-root files

| 2.x file | 3.0 |
| --- | --- |
| the status folders and their `.gitkeep` files | deleted at step 4 |
| `graveyard.yaml` | deleted at step 4; git history keeps it. 2.x recorded every item it resolved there, with its resolution, so that a link to an item whose folder was ignored or deleted still resolved. An item it records whose folder is not migrated (ignored and not kept, or deleted by retention) stops resolving |
| `dod.yaml` | deleted at step 4; each entry goes where 3.0 can enforce or state it (the table below) |
| `renames.yaml` | deleted at step 4, after its pairs of old and new slugs are copied into the migration log, so step 9 can rewrite live mentions of an old slug |
| `inbox/` | deleted after step 8 |

2.x's **Definition of Done** (`dod.yaml`, or the four built-in entries when a
project had none) was a list of things to confirm before completing. 3.0 has
no such list; each entry becomes a check or an instruction:

| 2.x Definition of Done entry | 3.0 |
| --- | --- |
| reviewed | the built-in completion gate: an accepted, current `review` verdict |
| capabilities reconciled | the built-in records gate, run on the move after `implement` |
| tests pass | an instruction in the project's `review` stage prompt (run the suite before an accepted verdict); or a `pre` hook on `completed` when the suite finishes well inside the hook time limit (`work.hooks.timeout`, 300 seconds by default) |
| docs synced | an instruction in the `review` stage prompt to invoke the `documentation-sync` skill; a skill cannot be a `pre` hook |
| any other entry | a `pre` hook on `completed` when a command can check it quickly; otherwise an instruction in the `review` or `qa` stage prompt |

### Configuration

Every key 2.x accepted. The 3.0 keys are described in full in the `configure`
skill's [`work.md`](../skills/configure/references/work.md) and
[`jira.md`](../skills/configure/references/jira.md).

| 2.x key | 3.0 |
| --- | --- |
| `work.lifecycle.stages.inbox`, `work.lifecycle.stages.request`, `work.lifecycle.stages.spec`, `work.lifecycle.stages.plan`, `work.lifecycle.stages.implement` | the same stage under `work.stages`. A stage's `pre` and `prompt` keep their names, and a stage now also takes `post`. A bare list given as the stage (the oldest shape) becomes its `prompt`, and a `command` entry in that list becomes `generate`. An empty `prompt` list, an error in 2.x, now means "print nothing" |
| `work.lifecycle.stages.verify` | `work.stages.qa`. Ask the user whether its bindings also belong to `review`, the engineers' check |
| `work.lifecycle.stages.postmortem` | `work.stages.postmortem`, with `prompt` only: a side stage takes no `pre` or `post`, so a `pre` there is removed and listed in the plan |
| `builtin: true` | `inherit: true`, which keeps the layer below (in `tcw-config.yaml`, TCW's own text) at that position in the list. At most one per list; `builtin` written in a file is an error |
| `work.lifecycle.transitions.start` | `work.stages.implement`, its `pre` and `post` |
| `work.lifecycle.transitions.submit` | the first stage after `implement` that is turned on (`review`, else `qa`), its `pre` and `post`: a submit hook guarded "the implementation is finished", which is what entering that stage means |
| `work.lifecycle.transitions.rework` | `work.stages.implement`, merged with start's lists. A hook that must run for only one of the two tests `TCW_FROM_STAGE` itself, since `when:` has no condition on the stage an item comes from |
| `work.lifecycle.transitions.complete` | `work.stages.completed` |
| `work.lifecycle.transitions.discard` | `work.stages.discarded` |
| `work.lifecycle.transitions.auto-delete` | removed: 3.0 never deletes an item. Its hooks are listed in the plan |
| `work.lifecycle.timeout`, `work.lifecycle.output-cap` | `work.hooks.timeout`, `work.hooks.output-cap` |
| `work.lifecycle.artifacts.<document>` | `file` entries, each with its `when:`, in that stage's `prompt` list: see [Templates become prompt entries](#templates-become-prompt-entries) |
| a `skill` binding in a `pre` list | an error in 3.0, since a check that is only reported always passes. Moved to `post` (reported for the agent, not run) or into prompt text, as the user chooses |
| a `type` condition in `when:` | an error in 3.0: removed. A condition on epics becomes a tag the user adds to the epics |
| `work.tracker.provider` | `work.backend: jira` |
| `work.tracker.base-url` | `work.jira.site` |
| `work.tracker.credentials` (`email-env`, `token-env`) | `work.jira.credentials`, with the same variable names |
| `work.tracker.statuses.<status>` | `work.stages.<stage>.status`: `backlog` gives `request`'s, `active` gives `implement`'s, `completed` and `discarded` give their own. `review` gives its status to whichever 3.0 stage the user chooses: `qa`, where 2.x review items go, or `review`. `spec`, `plan`, `qa` and any other stage turned on need statuses of their own |
| `work.tracker.pre-backlog` | `work.stages.inbox.status`, the status it names; its transition name is dropped |
| `work.tracker.inbox-query` | dropped when it only selects the project's inbox status, which 3.0 offers by default; otherwise `work.jira.inbox-query` |
| `work.tracker.candidate-query` | removed: "what can I pick up" is `tcw work list --stage request --mine` |
| `work.tracker.transitions` (`start`, `submit`, `rework`, `complete`, `discard`, and `claim` in older files), `work.tracker.strict`, `work.tracker.exclusive-claim-transition` | removed. `tcw work advance` finds the transition by its destination status; when several lead there it takes the one whose screen asks for nothing but a comment, and refuses with exit code 3, listing them, when that still leaves more than one. Claims are gone. A `transitions` entry that existed to choose between two routes into one status means the Jira workflow needs one of them removed; the plan lists it |
| `work.tracker.create.project` | `work.jira.project` |
| `work.tracker.create.issue-type` | `work.jira.issue-type`, the type of a new ticket (default `Task`) |
| `work.tracker.timeout-seconds` | `work.jira.timeout`, in seconds (default 15, as before) |
| `work.tracker.create.issue-types`, `work.tracker.create.components`, `work.tracker.create.on-new`, `work.tracker.comments`, `work.tracker.link` | removed. A child's type follows its parent's level in Jira's hierarchy, and a bug is a tag. TCW sets no components, so a project that relied on them sets them in Jira (the plan lists them). Creating an item always creates its ticket. A move's reason always travels with its transition as a comment. The `TCW Item` field names the item on every ticket, in place of a link |
| `work.retain` | removed: 3.0 never deletes an item. A project that prunes finished items does it itself |
| `work.auto-commit-transitions`, `work.publish-transitions` | removed, whether set or left at their default (see [2.x behavior that had no key](#2x-behavior-that-had-no-key)); a project that wants commits adopts the [git example](guide/configuration.md#example-keeping-git-in-step-with-each-stage-change-something-your-project-adds) |
| `work.trunk-branch` | removed: TCW writes files only in the checkout it runs in |
| `work.tags`, `work.documentation`, `work.path`, `work.repository` | kept. Read each `documentation` entry for 2.x wording |
| `work.procedures.<id>` | kept for the procedures 3.0 keeps: `documentation-sync`, `create-work`, `audit-backlog`, `search`, `triage-issues` and `unattended-work` (all but the first rewritten), plus the new `pause-work`. A binding for a deleted procedure is removed and its text reviewed: see [Removed procedures](#removed-procedures) |
| `connected-projects` | `projects`, with the same `parent`, `children` and `upstream` entries. The Feature `connected-project-registry` is now `project-registry`, so a project whose own records or taxonomy link to it renames the link |

#### Templates become prompt entries

A 2.x `work.lifecycle.artifacts` list is **first match wins**: the first entry
whose `when:` matches the item is used, and nothing after it. A 3.0 `prompt`
list is **cumulative**: every entry whose `when:` matches is included. Moved
over unchanged, a list with a conditional template before an unconditional one
would give a matching item both.

So each later entry must stay silent wherever an earlier one matched. 2.x
`tags` means "has any of these" and `not_tags` "has none of these", and 3.0
keeps both meanings. **When every earlier entry's condition is `tags` alone**,
add those tags to each later entry's `not_tags`; the same single template then
applies as before. One more shape converts: when exactly one earlier entry has
`not_tags` alone, and the later entry has no `tags` of its own, that earlier
entry is silenced by giving the later one `tags` with the same list ("has
none of these" is negated by "has one of these"). **Any other shape** (an
earlier entry with both keys, or two that each need `tags`) needs an "or" to
negate, which one `when:` cannot say: list it in the plan with a proposed
rewrite (for example, adding a tag to the affected items), and the user
chooses. A `builtin` fallback entry is dropped, since
`inherit: true` already supplies TCW's text.

TCW's own `spec` templates are the example. In 2.x:

```yaml
work:
    lifecycle:
        artifacts:
            spec:
                - file: docs/lifecycle/templates/spec-bug.md
                  when: { tags: [bug] }
                - file: docs/lifecycle/templates/spec.md
```

In 3.0:

```yaml
work:
    stages:
        spec:
            prompt:
                - inherit: true
                - file: docs/lifecycle/templates/spec-bug.md
                  when: { tags: [bug] }
                - file: docs/lifecycle/templates/spec.md
                  when: { not_tags: [bug] }
```

A 2.x template was copied into a new document as its starting text. A 3.0
prompt entry is read by the agent as part of the stage's instructions, so give
each template a first line saying it is the outline for the stage's document,
for example: _The outline for this item's spec: the file
`tcw work path <slug> spec` names (`spec/spec.md`)._

### Hook variables

Hooks and `generate` scripts still run with the project's root folder as
their working folder, so a relative path in a hook's command keeps working.
The variables are **mapped by what they mean, not by their position** in a
list: a 2.x variable that meant "where the item was" becomes the 3.0 variable
that means the same, even where its name looks like another's.

| 2.x variable | 3.0 |
| --- | --- |
| `TCW_SLUG`, a bare folder name | `TCW_SLUG`, keeping its name but now the full slug `<project>/<folder>`. Because the name is unchanged, the variable search of step 10 cannot find it: list each use in a hook script that treats it as a folder name, and change it to `TCW_ITEM_PATH`, or pass the slug to `tcw` as it is |
| `TCW_STATUS` in a transition's `pre` hook (the status the item is leaving) | `TCW_FROM_STAGE` |
| `TCW_STATUS` in a transition's `post` hook (the status the item arrived in) | `TCW_STAGE` |
| `TCW_STATUS` in a stage's `pre` hook, run by 2.x's stage gate (the item's current status) | `TCW_FROM_STAGE`: a 3.0 stage's `pre` hook runs when an item is moved into that stage, from wherever it is |
| `TCW_TRANSITION` (`start`, `submit`, `complete`, `rework`, `discard`, `auto-delete`, or a stage name) | `TCW_STAGE`, compared with the name of the stage being entered instead of the name of the move |
| `TCW_NODE_ROOT` | `TCW_PROJECT_ROOT` |
| `TCW_RESOLUTION` | removed: `TCW_STAGE` is `completed` or `discarded`, and a discard's reason is in `TCW_REASON` |
| `TCW_ITEM_PATH` | `TCW_ITEM_PATH`; since the folder no longer moves, it is the same before and after a move |
| (none) | new: `TCW_FORCED`, set to `1`, and `TCW_REASON`, on a move forced with `--force` |
| (none) | new: `TCW_CONFIG_DIR`, the folder of the configuration file that declared the binding, which a relative `file:` path is read from |
| `TCW_HOOK_ROLE`, `TCW_HOOK_KIND`, `TCW_HOOK_ID`, `TCW_HOOK_PHASE` (`generate` bindings) | unchanged. A `generate` script also gets the hook variables above, with `TCW_STAGE` set to the stage whose prompt is being composed and no `TCW_FROM_STAGE` |
| the JSON a `generate` script reads on standard input | one object, `{"schema": 1, "item": <the item>, "request": <its text, or null>, "hook": {"role", "kind", "id", "phase", "body_truncated"}}`. A script that read 2.x fields such as the status or the map of documents reads `item` and `request` instead |
| `{{tcw:body}}…{{/tcw:body}}` in prompt text | `{{tcw:request}}…{{/tcw:request}}`, **with a change of meaning**: 2.x replaced the span with the request document's name (`` `initial-request.md` ``), 3.0 replaces it with the request's text. The text between the markers is still what is shown when there is no request. Reread each sentence around a converted span: "Read {{tcw:body}}the request{{/tcw:body}} first" would now paste the whole request into the middle of a sentence, so put the span where the text belongs, such as on a line of its own after "The request:". 3.0 leaves `{{tcw:body}}` as written, so an unconverted pair is printed as it stands rather than refused |

#### Status values inside comparisons

A hook that compares a variable with a status name needs the value
translated too, and **by the 3.0 stage the hook ends up bound to** (the
[Configuration](#configuration) table), not by one table for every hook,
because a hook bound to a new stage sees new values:

- **A value compared with `TCW_STAGE`**, where the 2.x test was "this move's
  destination", becomes the stage the hook is now bound to. A former `submit`
  `post` hook testing `$TCW_STATUS = review`, moved to `work.stages.review`,
  tests `$TCW_STAGE = review`, not `qa`; moved to `work.stages.qa` because
  review is turned off, it tests `qa`.
- **A value compared with `TCW_FROM_STAGE`** becomes the set of stages an item
  can come from in the new configuration. A `start` `pre` hook testing
  `= backlog` tests whether the stage is one of those turned on before
  `implement` (for example `request`, `spec` or `plan`), since a forced skip
  can enter `implement` from any of them.
- **Other 2.x statuses** translate by [Status folders](#status-folders):
  `active` is `implement`; `completed` and `discarded` are unchanged.
- **A test that becomes always true or always false** once the hook moves (for
  example a `rework` hook testing `TCW_TRANSITION = rework`, after rework is
  merged into implement) is rewritten to test `TCW_FROM_STAGE`, or removed,
  and listed in the plan.

### Capability records

| 2.x field | 3.0 |
| --- | --- |
| `Planning doc:` | removed from every record. It pointed from a capability to the 2.x item that planned it; 3.0 reads completed items' declarations instead, and a record that still carries the field is an error in `tcw validate` |
| `Tracker:` | removed, for the same reason: work items point at capabilities, not the other way |

Records whose status is `Missing` are left alone: each is a true statement of
a known gap. An open item whose 2.x plan added one still has to make it
`Supported`, or remove it, before the move after `implement`, which the
records gate checks.

### The project's own files

| 2.x | 3.0 |
| --- | --- |
| hook scripts and commands bound in the configuration | the variables of [Hook variables](#hook-variables), including every use of `TCW_SLUG`; 2.x status names in comparisons; calls to removed or renamed commands ([Commands](#commands)) |
| text in `AGENTS.md`, `CLAUDE.md` and the prompt and procedure files the configuration binds that relies on removed behavior: status folders, `state.yaml`, the Definition of Done, `refined-outcome.md`, claims, retention, automatic commits | rewritten as the approved plan says, at step 10; step 12 looks wider |
| a `.gitignore` rule naming a status folder, such as `docs/work/completed/*` or `docs/work/discarded/*`, with its `.gitkeep` exception line and the comment 2.x's `tcw init` wrote above them | removed. Add the line `/tcw-config.local.yaml`, as `tcw init` writes for a new project, so personal configuration is never committed |
| `TCW_WORK_OWNER`, and the git identity used when it is unset | removed. In filesystem mode, set `user.name` in personal configuration (`~/.config/tcw/config.yaml`, or `tcw-config.local.yaml` beside `tcw-config.yaml`) |
| item worktrees made by `tcw work start --worktree` | removed: TCW makes no worktrees. A contributor who wants one runs `git worktree add` |

### Live references

| 2.x reference | 3.0 |
| --- | --- |
| a `parent` or `blocked_by` value naming a renamed folder | the new full slug: in `item.yaml` in filesystem mode, as the ticket's parent or `Blocks` link in Jira mode |
| a renamed folder's old name in an open item's documents, the configuration, or a live document | the new name |
| an old slug that 2.x recorded when it renamed an item (copied into the migration log at step 4) | the slug it was renamed to |
| `tcw://work/<old slug>` in live text | `tcw://work/<new slug>` |
| the documents of completed and discarded items, changelogs and release notes | left as they are: they record what was true then |

### Skills and agents

TCW's plugin had these skills and agents at 2.8.1 and no longer has them.
Under Claude Code a plugin's skills and agents are named with its prefix, such
as `tcw:verifier`; an instruction written by hand may say `tcw-verifier`.

| 2.x skill or agent | 3.0 |
| --- | --- |
| the skill `commands-verify-work` | deleted: review and qa are stages. `tcw work stage prompt review <slug>` and `tcw work stage prompt qa <slug>` print their instructions, and the `commands-drive-work-to-completion` skill reaches them |
| the skill `post-mortem` | deleted: the `postmortem` stage's prompt, `tcw work stage prompt postmortem <slug>`, is the one source |
| the skill `work-stage` | deleted: `tcw work stage prompt <stage> <slug>` prints the same text |
| the agent `verifier` | renamed `reviewer`: a read-only assessment for the `review` stage that recommends a verdict, which the session that sent it writes |
| the agent `post-mortem` | deleted: the `postmortem` stage's prompt |

### Commands

Every 2.8 command and what it is in 3.0. A command not listed as changed is
unchanged.

| 2.8 command | 3.0 |
| --- | --- |
| `tcw --version`, `tcw serve` | unchanged |
| `tcw init` | `tcw init [<axis>…] --id <id>`, which also works outside a git repository and prints nothing; `--work-path`, `--taxonomy-path` and `--capabilities-path` are unchanged |
| `tcw provision --refresh` | removed: `tcw provision [--component <axis>] [--dry-run]` never updates a copy that already exists; update it with git |
| `tcw validate <path>`, `tcw validate --no-recurse` | `tcw validate [--remote]`, which checks the current project only; run it in each project |
| `tcw work nodes` | `tcw projects list [--json]` |
| `tcw taxonomy <path>`, `tcw capabilities <path>` | removed: `tcw taxonomy show <path>`, `tcw capabilities show <path>` |
| `tcw taxonomy init`, `tcw capabilities init`, `tcw work init` | removed: `tcw init <axis>`, such as `tcw init work` |
| `tcw taxonomy check`, `tcw capabilities check` | removed: `tcw validate` |
| `tcw taxonomy add <name> <description>`, with `-s` and `-p` | `tcw taxonomy add <name> [--slug] [--parent] [--kind] [--vocab]`, with the description on standard input |
| `tcw taxonomy list`, `tcw taxonomy show`, `tcw taxonomy search` | unchanged, and each takes `--json` |
| `tcw taxonomy path`, `tcw taxonomy rm`, `tcw taxonomy extends add`, `tcw taxonomy extends rm` | unchanged |
| `tcw capabilities list --local-only` | `tcw capabilities list --local`; the command also takes `--json` |
| `tcw capabilities show`, `tcw capabilities search` | unchanged, and each takes `--json` |
| `tcw capabilities add <path> <name> -s <status>` | `tcw capabilities add <path> [<name>] [--status]`, with the body on standard input |
| `tcw capabilities path`, `tcw capabilities set`, `tcw capabilities reset`, `tcw capabilities rm` | unchanged |
| `tcw capabilities extends <id>`, `tcw capabilities extends <id> --rm` | `tcw capabilities extends add <id>`, `tcw capabilities extends rm <id>` |
| `tcw capabilities drift` | unchanged in shape; it reads completed items' declarations |
| `tcw work inbox list\|path\|show\|accept` | removed. Filesystem mode: inbox items, `tcw work list --stage inbox`. Jira mode: `tcw work tickets list`, `tcw work tickets adopt <KEY>` |
| `tcw work tracker list\|show\|import\|create\|link\|claim\|release\|unlink\|sync` | removed: `tcw work tickets list`, `tcw work tickets adopt <KEY>` |
| `tcw work reconcile` | removed: Jira's hierarchy, or `tcw work list --parent <slug>` |
| `tcw work delegate`, `tcw work escalate` | removed: `tcw work new <title> --project <id>` |
| `tcw work tombstone add`, `tcw work delete`, `tcw work scaffold` | removed |
| `tcw work start`, `tcw work submit`, `tcw work rework`, `tcw work complete`, `tcw work drop` | `tcw work advance <slug> [--to <stage>] [--force --reason <text>] [--dry-run]`; `tcw work discard <slug> --reason <text>` |
| `tcw work start --worktree` | removed: TCW makes no worktrees |
| `tcw work stage gate` | removed: `tcw work advance <slug> --dry-run` |
| `tcw work stage validate` | removed |
| `tcw work stage <stage> <slug>` (the 1.x form) | removed |
| `tcw work new <title> --priority <number> --epic --initiative <slug>` | `tcw work new <title> [--project <id>] [--stage inbox] [--priority <name>] [--effort] [--complexity] [--tag] [--assignee] [--assign-me] [--parent] [--blocked-by]`, with the request on standard input |
| `tcw work list --status <status>`, `tcw work list -i` | `tcw work list [--stage <stage>] [--parent <slug>] [--assignee <name>] [--mine] [--tag <tag>] [--all] [--json]` |
| `tcw work show <slug> [--json]` | unchanged |
| `tcw work path [<slug>]` | `tcw work path [<slug> [<stage> [--next] [--handoff]]]` |
| `tcw work edit <slug> --initiative`, `tcw work edit <slug> --type`, an integer `--priority` | `tcw work edit <slug> [--title] [--priority <name>] [--effort] [--complexity] [--tag] [--untag] [--assignee] [--assign-me] [--parent] [--blocked-by] [--unblocked-by] [--blocks]` |
| `tcw work rename <slug> <new-slug>` | `tcw work rename <slug> <new-name>`, the new name being the part after the date or key |
| `tcw work lifecycle <slug> --directive --phase --transition` | `tcw work lifecycle [--stage <stage>] [--json]` |
| `tcw work docs`, `tcw work stage prompt <stage> [<slug>] [--no-exec]`, `tcw work tags list\|add\|rm` | unchanged |
| `tcw work procedure prompt <id>` | `tcw work procedure <id> [<slug>] [--no-exec]` |
| (none) | new: `tcw config show [--origin]`, `tcw work comment <slug>` |

#### Behavior that changed

Commands that now refuse, or report, what 2.x let through. Most kept their
names and arguments; `tcw work new --project` and `tcw config show` are new in
3.0 and are listed for what they refuse:

- **A slug given to `tcw taxonomy add --slug` must be a slug**: lower-case
  letters and digits in words joined by single hyphens, such as
  `refund-a-payment`. Anything else, a space, a capital letter or a `/`
  among them, is a usage error (exit code 2) and nothing is created. A
  nested term is made with `--parent`, not with a `/` in the slug. The
  viewer's request that creates a term answers 400 for the same slugs.
  Existing terms are not changed.
- **The viewer's record edits need a revision.** `tcw serve`'s
  `PATCH /api/taxonomy/<ref>` and `PATCH /api/capabilities/<ref>` require
  `revision`, the `coreRevision` the client last read: without it the answer
  is 400 `revision is required`, and with one that is out of date, 409. The
  viewer's own page always sends it; a script of the project's own that
  calls these routes must send it too.
- **`tcw provision` turns git's prompts off.** It runs git with every prompt
  it can reach turned off: `GIT_TERMINAL_PROMPT=0` stops git's own prompt for
  HTTPS credentials; `GIT_ASKPASS` is set to the empty string, which also
  stops a configured `core.askPass`, and `SSH_ASKPASS` is removed, so no
  password program is opened; and `GCM_INTERACTIVE=never` stops Git
  Credential Manager from opening an interactive sign-in. A credential helper
  that answers without asking still answers. For ssh, TCW sets
  `GIT_SSH_COMMAND` to `ssh -o BatchMode=yes`, so a private remote over ssh
  needs a key that an ssh agent holds and a host already in
  `~/.ssh/known_hosts`: a first contact with an unknown host, or a key whose
  passphrase nothing supplies, fails with `git clone failed:` and git's
  reason, instead of asking. **An ssh command the user has set** is left
  alone, so with one set, ssh may still ask. TCW counts as the user's own
  `GIT_SSH_COMMAND` or `GIT_SSH` in the environment, and a `core.sshCommand`
  that `git config --show-scope --includes --get-all core.sshCommand` prints
  from any scope but `local` and `worktree`: the global or system
  configuration, or the command line (`git -c`, `GIT_CONFIG_PARAMETERS`,
  `GIT_CONFIG_COUNT`). A `core.sshCommand` in the repository the command runs
  in does not count, since a clone into a new folder does not use it.
- **`tcw provision` refuses a configuration it cannot read.** When
  `tcw-config.yaml` cannot be parsed, it exits with code 1 and names the
  file. 2.x printed `Nothing to provision` and exited 0.
- **A `tcw-config.yaml` that is not valid UTF-8 is named.** `tcw provision`
  and `tcw init` exit with code 1 and say which file holds which byte, such
  as `tcw init: <path>/tcw-config.yaml: is not valid UTF-8 text (byte 0xe9 at
  position 17)`, and leave the file as it was. 2.x printed Python's own
  decoding error, which names no file.
- **The Jira client does not pass credentials on through a redirect.** When
  Jira answers a request with a redirect, TCW no longer sends the account's
  email address and API token on to the address it was redirected to,
  whatever host that is; they go only to `work.jira.site`. **A 401 after a
  redirect names the redirect**: when the address that answered 401 is not
  the one TCW asked, the error says Jira redirected the request to that
  address, that credentials are not sent on a redirect, and that
  `work.jira.site` should be set to the address Jira answers at. A 401 from
  `work.jira.site` itself is still reported as rejected credentials.
- **`tcw work` commands check the connected projects.** A `tcw work` command
  that reads the board refuses (exit code 1, naming the file) when the
  configuration of this project, or of a project connected to it, holds a
  retired key such as `connected-projects`, or is otherwise invalid as a set
  of connected projects, as the taxonomy and capabilities commands already
  did. A connected project that is not on this machine does not stop it, and
  `tcw work new --project`, which hands an item to another project, is not
  checked this way. This is why every connected project must finish its own
  step 3 before this project's step 11 ([Before you start](#before-you-start)).
- **`tcw work new --project <id> --stage <stage>` is a usage error** (exit
  code 2), naming `--stage`. An item created in another project starts where
  that project's intake puts it, so `--stage` cannot choose; like every other
  flag but `--priority`, it is refused with `--project` rather than ignored.
- **`tcw config show` refuses a value it would print wrongly.** It reads its
  own output back before printing it, and when a value would not read back
  as the same value, it prints nothing and exits with code 1, naming the
  value's key.
- **Offline `tcw validate` in Jira mode reads each item's
  `capabilities.yaml`.** Without `--remote`, it reports a declaration that
  cannot be read or is malformed as an error naming the file, in every item
  folder whatever the item's stage. The records it declares are still checked
  only under `--remote`, which does not report a malformed file a second
  time. In Jira mode the viewer's check of one item, after a save in
  `tcw serve` changes it, also reports a malformed `capabilities.yaml` in
  the same words, whatever the item's stage. Step 7's corrections to
  `capabilities.yaml` are what keep this quiet at step 11.

### Removed procedures

| 2.x procedure (`work.procedures.<id>`) | 3.0 |
| --- | --- |
| `post-mortem` | the `postmortem` stage's prompt; bind replacement text under `work.stages.postmortem.prompt` |
| `decompose` | part of the `plan` stage's prompt; bind replacement text under `work.stages.plan.prompt` |
| `delegation` | fixed text in the `work` skill; delegating to another project is `tcw work new <title> --project <id>` |
| `consolidate-plans` | deleted; move an outside plan into an item with `tcw work new` |

## Jira mode: binding items to tickets

These rules apply when the 3.0 configuration sets `work.backend: jira`. Step 6
carries them out; the survey of step 1 finds every case they cover, and the
plan shows each one before anything changes.

### Every item needs a ticket

A Jira-mode item without a ticket is not legal. For each item without one, the
plan offers two answers:

- **Create it.** The agent creates the ticket in the Jira project, of the
  issue type [Talking to Jira](#talking-to-jira) gives, with the item's
  `title` as its summary, its request as the description
  ([The request](#the-request)), and the status of the item's stage. These are
  REST requests ([Talking to Jira](#talking-to-jira)), not `tcw work new`:
  in Jira mode `tcw work new` creates only at `request`, and it makes a new
  folder where one already exists. A ticket is created at the project's
  starting status and then moved into the target status; with one transition
  into every mapped status (step 2), that is a single move. A completed item's
  ticket is created and moved straight to the completed status.
- **Delete the folder.** Git history keeps it.

### Reconciling the folder with the ticket

Where the folder (the full `item.yaml` step 4 wrote) and the ticket disagree,
**the folder wins**, since 2.x treated the files as the source. Three
refinements:

- **An absent or empty value on disk is not a disagreement**: the ticket's
  priority, labels or assignee stand. Otherwise every item with no priority on
  disk would reset its ticket's priority to `medium`.
- **A title that differs only by a leading `<KEY> — ` prefix** (`TCW-12 — Do
  the thing` against `Do the thing`) is not a disagreement; the prefix is
  dropped.
- **Labels on the ticket that the folder does not have** are listed, and
  removed only when the user agrees in the plan.

Every difference, and every 2.x `sync` record still `pending` (Jira lagged
behind a move), is shown in the plan.

### Moves and comments

**A status move the migration makes carries no comment**: it is bookkeeping,
not a step in the work. A discard's reason does become a comment, and so does
each carried-over verdict ([Acceptance history goes to qa](#acceptance-history-goes-to-qa)).

### The request

- **A request file the ticket's description already contains**,
  `intake.md` or `initial-request.md` alike, is deleted without asking and
  without posting anything. Two kinds count as contained:
  - **a 2.x import of this ticket**: an `intake.md` that has the line
    `Imported on <date> from [<KEY>](https://…/browse/<KEY>) (jira-cloud).`
    with this ticket's own key. 2.x wrote it from the ticket, under a heading of the
    key and summary, holding the description as 2.x read it (Jira's wiki
    markup) or `The ticket has no description.`, so its text never matches
    the description read back as a document, and it is not compared. This
    holds only for a file whose contents, uncommitted changes included, are
    exactly what 2.x's import commit added; an edited import, or one with no
    import commit, is compared like any other file, so text added to it is
    never deleted unseen;
  - **any other request file whose text the description holds**, ignoring
    all white space. The description is a document, so the comparison reads
    its text back first. This covers every ticket step 6 created, whose
    description is the request already, so step 7 never posts that text a
    second time.

  The last command in [Talking to Jira](#talking-to-jira) decides both.
- Other request text (the file left once a contained one is deleted, or both
  combined as [Documents](#documents) describes when neither is contained)
  goes into the description when the
  description is empty. When it has text, the request is posted as a comment
  whose first line is `Request as written in the repository before 3.0`, and
  the description is left as it is: Jira owns it, and someone outside
  engineering may have written it. The plan offers "replace" or "append"
  instead, per ticket.
- The exact text of every comment is shown in the plan before anything is
  posted.

### TCW Project and TCW Item

Two custom fields tie a ticket to an item: `TCW Project` holds the project's
ID, and `TCW Item` holds the item's full slug, `<project>/<folder>`, using the
renamed folder. Both are set on every ticket that has an item. Tickets a
project tracks without an item (an epic it only links to, for example) may
carry `TCW Project` alone.

### Folder names

A Jira-mode folder is named `<KEY>-<title words>`. The title words come from
the ticket's summary: lower case, every run of characters other than `a`-`z`
and `0`-`9` turned into one `-`, `-` trimmed from both ends, and cut back to
the last `-` within 108 characters. A summary that leaves nothing gives
`untitled`.

### Tickets without items

Tickets in the Jira project that no item is bound to, and that are not at the
inbox, completed or discarded statuses, are listed. 3.0 shows them in no
list: `tcw work tickets list` offers only tickets at the inbox status (or a
project's own `work.jira.inbox-query`), and one linked as an item's parent or
blocker appears only as an `untracked` reference in that item's
`tcw work show`. The user chooses, per ticket: move it to the inbox status,
or leave it.
