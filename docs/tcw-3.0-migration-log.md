# TCW 3.0 migration log

The record of TCW's own migration from 2.8 to 3.0.0, made by following
[the migration guide](migration-guide-2.8-to-3.0.0.md) (TCW-76, Tasks B4 to
B16). It is kept outside the work path, as the guide's rule 7 says. What
TCW-76 did before the freeze (the filesystem rehearsal, the guide's review,
the Jira checklist for the owner) is in TCW-76's own `outcome.md`, which
stays the item's implement document and is converted at step 7.

## Run 1

Started: 2026-10-16
Starting commit: 3b71ea7826cfabb7610e6fd01a0497edf78fec71

The starting commit is the freeze commit: `epic/tcw-3.0` after `main`
(`8b5a212b`) was merged into it (TCW-76 Task B3). The run is made in the
worktree `.worktrees/tcw-3-0-migration-run-1`, on the branch
`migrate/tcw-3.0-run-1`.

### Deviations from the plan

- **(a) A version was cut before Task B24.** 2.8.3 was cut and published on
  2026-10-16 at the owner's request, although TCW-76's plan said no version
  until B24. All five version files say 2.8.3 after Task B3.
- **(b) The agent applies the Jira changes.** The owner asked on 2026-10-16
  that the agent make the Jira workflow, status, screen and field changes
  itself, in the owner's personal Chrome profile, instead of the owner making
  them by hand (spec Design 2 step 2 and 6.2 said by hand). Each change is
  still listed in the step 1 plan, for approval before it is made.
- **(c) TCW gets its own screens.** The owner chose on 2026-10-16 that TCW
  gets its own copies of the screens it shares with `PRPI` (TCW-76's
  `outcome.md`, Jira checklist step 5).
- **(d) Where the log lives.** TCW-76's spec (Design 1.8) and plan (choice 5)
  made the log TCW-76's 2.x `outcome.md`, becoming `implement/round-1.md` at
  step 7. The guide's rule 7 keeps the log outside the work path, and the
  run follows the guide as written, so the log is this file,
  `docs/tcw-3.0-migration-log.md`. It also keeps one path through steps 4, 6
  and 7, which move and rename TCW-76's folder and its `outcome.md`.
- **(e) 2.8 for step 0.** The plan's rules name 2.8.1 for reading the 2.x
  board. Step 0 ran 2.8.3, the released version the board is on, from PyPI
  in a private virtual environment (`tcw76/venv-28` in the session's scratch
  folder; `tcw --version` printed `tcw 2.8.3`).

### Step 0: Prepare

**Before you start**, checked on 2026-10-16:

- On 2.8.x: `tcw --version` printed `tcw 2.8.3` (the shared install, and the
  private `venv-28` from PyPI).
- The 3.0 CLI beside it: the private virtual environment `tcw76/venv`, an
  editable install of this worktree. Run from outside the primary checkout,
  it imports `.worktrees/tcw-3-0-migration-run-1/tcw/__init__.py`, and
  `tcw work advance --help` prints `usage: tcw work advance [-h] [--to TO]
  [--force] [--reason REASON] [--dry-run]`, a 3.0 command. Its version string
  still reads 2.8.3, since 3.0.0 is cut later.
- No uncommitted changes: `git status --porcelain` printed nothing.
- No 2.x item worktree: `git worktree list | grep -E '\[work/'` printed
  nothing. The other worktrees, listed for the plan: the primary checkout
  (`main`, `8b5a212b`), `.worktrees/tcw-3-0-epic` (`epic/tcw-3.0`,
  `3b71ea78`), and this one.
- A branch or tag marking the 2.x state: `main` (frozen at `8b5a212b`) and
  `epic/tcw-3.0` (`3b71ea78`) mark it today, but both move later (B21, B24),
  and the tag `v2.8.3` is on `74b5913f`, four board commits before `main`'s
  tip. No tag was made in this step; the step 1 plan proposes one.
- Connected projects: the configuration declares none.
- Jira credentials: `TCW_JIRA_EMAIL` and `TCW_JIRA_API_KEY` are set (after
  `source ~/.bashrc`).
- `jq --version` printed `jq-1.7.1-apple`.

**2.8's `tcw validate`**, run in this worktree with `venv-28`: printed
`validate OK`, exit 0. Nothing to fix under 2.8. `git status --porcelain`
printed nothing afterwards.

**Ignored item folders.** In this worktree,
`git status --ignored --porcelain -- docs/work` printed nothing. In the
primary checkout, `git -C /Users/brian/Projects/TCW status --ignored --porcelain -- docs/work`
printed 37 lines, all under `docs/work/discarded/` (the `.gitignore` rule
`docs/work/discarded/*`, lines 29-30); 33 were counted on 2026-10-15. The
list is in the step 1 plan.

**Finished slices** (criterion 27): each one's `graveyard.yaml` `location`,
and `git cat-file -e <location>:docs/work/completed/<slug>/spec.md`:

| Slice | `location` | `git cat-file -e` |
| --- | --- | --- |
| TCW-69 | `0e4d406165a7ac84bb8d49376b06ac6a91df2f36` | exit 0 |
| TCW-70 | `3207f3103f73bcefe5fedfe7e3ed7d50b39bc8cb` | exit 0 |
| TCW-71 | `6599dd209f89ae87c403455129e783aeff49bad2` | exit 0 |
| TCW-72 | `a066ae201dc12928fbe06ad27dead370bfc85ed1` | exit 0 |
| TCW-73 | `e400dcfd046c6044d905c550902be9896899af20` | exit 0 |
| TCW-74 | `64a2eb9478ecf4d0eec7dc16a5e390161ee852bd` | exit 0 |
| TCW-75 | `560e312f1700893abbdf05d596d1817ae541916a` (deleted in `b5b7756f`) | exit 0 |
| TCW-77 | `0a23906fb743a41ebf6d1fb2227ebf122ad2d318` | exit 0 |

**Check.** Before the log was started, `git status --porcelain` printed
nothing and `git worktree list | grep -E '\[work/'` printed nothing.
Afterwards, `grep -E '^(Started|Starting commit): ' docs/tcw-3.0-migration-log.md | tail -n 2`
printed:

```text
Started: 2026-10-16
Starting commit: 3b71ea7826cfabb7610e6fd01a0497edf78fec71
```

### Amendments to the guide

None in step 0. In step 1, three places where the guide was unclear were
fixed before the plan was written, and the plan was then made from the fixed
text (spec Design 5.1):

1. **Where a pruned item's stage comes from.** Step 1 said a pruned item
   keeps its folder at stage `discarded`, but step 4 gave every item its stage
   from the Status folders rule alone, which puts a pruned `backlog/` item at
   `request`. Step 4 now says the stage is the one the approved plan closes
   the item at, `discarded` for a pruned item.
2. **What a pruned item's comment says.** Step 5 gave a discarded item's
   comment the first line `Carried over from TCW 2.x: discarded as
   <resolution>`, but a pruned item was never discarded under 2.x and has no
   resolution, and rule 6 needs a fixed first line to skip a repeat. Step 5
   now gives an item the plan closes the first line `Closed at the migration
   to TCW 3.0 as <stage>`, followed by the plan's reason. The same covers an
   item closed at `completed` because 3.0 delivers its work (TCW's "keep an
   item's folder in one place"), which the guide had no place for: step 1's
   prune list says such an item can be closed the same way, step 6's fourth
   pass posts these comments too, and "Moves and comments" names them.
3. **A blocker whose folder is not migrated.** The `blocked_by` row said each
   entry becomes `<project>/<folder>` "using the folders' final names", which
   has no answer for an item 2.x retention deleted (TCW-76's blocker TCW-75).
   The row now drops and lists such an entry, as it does an `external:` one.

`tests/test_migration_guide.py`, `tests/test_docs_describe_3_0.py` and
`tests/test_documented_cli_surface.py` pass after the change (800 passed).

### Step 1: Survey, then ask once

The board, the configuration and every ticket were read (REST `GET` and one
JQL search only; nothing written). The plan below was presented to the owner
as one question on 2026-10-16. The appendix holding the exact text of every
comment it would post is not committed, since it is built entirely from files
in this commit (each named below by its blob), and is kept beside the plan in
the session's scratch folder.

This log is a tracked Markdown file outside the archival trees, so
`tests/test_documented_cli_surface.py` read it as a live document and failed
on the 2.x keys the plan names (`work.lifecycle`, `work.retain`,
`work.tracker`). The step's commit adds the log to that test's `ARCHIVAL`
list, beside the migration guides. Without that line the test fails as
described; with it, the test files named in the plan's rules pass (1153
passed, 6 skipped), and `pytest --collect-only -q` collects 5275 tests.

**Check:** to be run once the answer is recorded:
`grep -c '^## Approved plan' docs/tcw-3.0-migration-log.md` must print `1`.

## Approved plan

Status: **presented to the owner on 2026-10-16; not yet answered.** Nothing
in the board, the configuration or Jira has been changed. The owner's answer
is recorded word for word at the end of this section once given.

Built from a read of the whole board and configuration on the migration
branch after step 0 (`2e5e843a`), and of every ticket in the Jira project
`TCW` (one JQL search, `project = TCW`, 77 tickets, plus a REST read of the
description of each of the 19 bound tickets) on 2026-10-16. Only REST `GET`
requests and that search were made.

The decisions this plan needs from the owner are collected at the end, under
"Decisions for the owner" (D1 to D12). Everything else follows the guide, the
spec's recorded decisions, or both.

### The migration log

`docs/tcw-3.0-migration-log.md` (this file), outside the work path, as the
guide's rule 7 says (deviation d above).

### Backend and stages

- **Backend:** Jira mode (`work.backend: jira`), site
  `https://proposit.atlassian.net`, project `TCW`.
- **Stages:** every optional stage on: `spec`, `plan`, `review`, `qa` and
  `postmortem` (owner, 2026-10-01; spec Design 6.2).
- **Statuses** (spec Design 6.2): inbox `Triage`, request `To Do`, spec
  `Specifying`, plan `Planning`, implement `In Progress`, review `In Review`,
  qa `In QA`, completed `Done`, discarded `Won't Do`. `postmortem` is a side
  stage and has no status. 2.x's `review` status (`In Review`) goes to 3.0's
  `review` stage; no item is in 2.x `review/` today, so no ticket is affected.

### Jira changes (step 2)

The workflow was read again today. It is unchanged from TCW-76's checklist
(`outcome.md`, "Jira checklist (for the owner)"): the scheme `TCW work scheme`
(10039) maps every issue type to the one workflow `TCW work`, whose statuses
are `Triage` (10011), `To Do` (10012), `In Progress` (3), `In Review`
(10013), `Done` (10009) and `Won't Do` (10041), and whose transitions are
`Create` (initial, to Triage) and the directed `Accept`, `Start`, `Submit`,
`Complete`, `Rework`, `Cancel`, `Stop` and `Reopen`, none with a screen. The
project still uses the issue type screen scheme `PRPI: Kanban Issue Type
Screen Scheme` (10002), shared with `PRPI`. The custom fields are `TCW
Project` (`customfield_10076`, text), `TCW Item` (`customfield_10042`, text),
`Effort` (`customfield_10077`) and `Complexity` (`customfield_10078`), single
choice with the options `low`, `medium`, `high`, `very-high`. The site's
priorities are `Highest`, `High`, `Medium`, `Low` and `Lowest`, 3.0's
defaults.

The changes, each applied by the agent in the owner's Chrome profile
(deviation b) after this plan is approved and once nothing will run 2.8
against the project again, with each line's confirmation read back by REST
and logged:

1. Add the existing statuses `Specifying` (10042), `Planning` (10043) and
   `In QA` (10044) to `TCW work`.
2. Add one global transition into each of the nine statuses, named after the
   status, with no screen, condition or validator.
3. Delete `Accept`, `Start`, `Submit`, `Complete`, `Rework`, `Cancel`, `Stop`
   and `Reopen`; keep `Create`.
4. Publish the draft; every ticket keeps its status.
5. **TCW's own screens** (deviation c): copy the three screens 10010, 10011,
   10012 as `TCW: Kanban Default Screen`, `TCW: Kanban Bug Screen` and
   `TCW: Kanban Epic Screen`; copy their screen schemes and point the copies
   at the new screens; copy the issue type screen scheme 10002 as
   `TCW: Kanban Issue Type Screen Scheme`, point it at the copied screen
   schemes and assign it to `TCW` only; then add `TCW Project`, `Effort` and
   `Complexity` to the three copied screens (`TCW Item`, `Summary`, `Labels`,
   `Assignee`, `Parent` and `Priority` are checked there as well). `PRPI`
   keeps 10002, unchanged.
6. No other workflow: confirmed by the scheme read above.

Step 3's `tcw validate --remote`, in a scratch folder, is the reading that
confirms them together. It reads only the `Task` and `Sub-task` types, so the
`Bug` and `Epic` create and edit screens and their workflow are confirmed by
the separate REST reads the guide's step 2 lists.

### Each item

33 items: 30 in `backlog/`, 1 in `active/`, 2 in `completed/`; none in
`review/`, `blocked/` or `discarded/` (tracked), and no nested child. 19 are
bound to tickets, 14 are not. Stages by the guide's Status folders rule:
`backlog/` gives `request` (TCW-50 has `spec.md` and `plan.md`, so `plan`),
`active/` gives `implement`, `completed/` gives `completed`; the plan closes
12 items instead (the prune list, and the one closed as delivered).

Priorities convert by the guide's table: 40 or more `highest`, 30 to 39
`high`, 20 to 29 `medium`, 10 to 19 `low`, below 10 `lowest`. Every ticket
today is at `Medium` with no labels, no effort or complexity, no `TCW
Project` or `TCW Item`, and no `Blocks` link.

| # | 2.x folder | Ticket | 3.0 stage | Status move | Fields and differences | Documents |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | `backlog/2026-08-18-decide-whether-tcw-work-scaffold-should-stage-its-draft-in-git` | TCW-33 | discarded (pruned) | To Do → Won't Do | priority 25 → medium (ticket's Medium: no change); labels cli, work (set); effort low; complexity low | intake.md |
| 2 | `backlog/2026-08-31-nothing-verifies-that-a-changed-capability-was-actually-changed` | TCW-5 | request | stays at To Do | priority 45 → highest (set); labels cli, capabilities, work (set); effort low; complexity medium | initial-request.md |
| 3 | `backlog/2026-09-01-fan-the-backlog-audit-out-across-every-connected-work-root` | TCW-22 | request | stays at To Do | priority 35 → high (set); labels skills, work (set) | intake.md |
| 4 | `backlog/2026-09-01-make-tcw-validate-usable-as-a-gate-suppressible-references-and-graded-exit-codes` | TCW-14 | request | stays at To Do | priority 40 → highest (set); labels cli, work (set) | intake.md |
| 5 | `backlog/2026-09-04-tcw-provision-cannot-be-scoped-and-a-third-hop-config-can-name-a-checkout-directory` | TCW-23 | request | stays at To Do | priority 35 → high (set); labels cli, remote (set); effort low; complexity medium | intake.md |
| 6 | `backlog/2026-09-11-run-the-eval-harness-and-act-on-what-it-finds` | TCW-48 | request | stays at To Do | priority 1 → lowest (set); labels skills, work, docs (set) | initial-request.md |
| 7 | `backlog/2026-09-15-check-the-tracker-s-workflow-against-the-statuses-mapping-in-tcw-validate` | TCW-10 | discarded (pruned) | To Do → Won't Do | priority 45 → highest (set); labels remote, work, cli (set); effort high; blocked by TCW-14: link "TCW-14 blocks TCW-10" created | initial-request.md, intake.md |
| 8 | `backlog/2026-09-15-check-the-whole-tracked-tree-ledgers-included-for-removed-skill-names` | TCW-39 | request | stays at To Do | priority 20 → medium (no change); labels tech-debt, skills (set); effort medium | initial-request.md, intake.md |
| 9 | `backlog/2026-09-15-decide-claim-exclusivity-from-a-jira-project-s-workflow-definition` | TCW-40 | discarded (pruned) | To Do → Won't Do | priority 20 → medium (no change); labels remote, work (set) | intake.md |
| 10 | `backlog/2026-09-15-let-tcw-work-list-sort-by-created-priority-effort-or-title` | TCW-50 | plan | To Do → Planning | no priority on disk (ticket's Medium stands); labels work, cli (set) | initial-request.md, plan.md, spec.md |
| 11 | `backlog/2026-09-15-make-pnpm-prettify-check-pass-on-a-clean-checkout` | TCW-42 | request | stays at To Do | priority 15 → low (set); labels tech-debt (set); effort medium | initial-request.md, intake.md |
| 12 | `backlog/2026-09-15-repair-sentences-references-and-headings-in-the-guides` | TCW-41 | request | stays at To Do | priority 20 → medium (no change); labels docs (set); effort medium | initial-request.md, intake.md |
| 13 | `backlog/2026-09-15-test-as-ci-does-and-warn-on-red-ci-and-unpublished-tags` | TCW-21 | request | stays at To Do | priority 40 → highest (set); labels tech-debt (set); effort medium | initial-request.md, intake.md |
| 14 | `backlog/2026-09-15-write-work-item-properties-to-mapped-tracker-fields` | TCW-26 | discarded (pruned) | To Do → Won't Do | priority 35 → high (set); labels remote, work, cli (set); effort high | initial-request.md, intake.md |
| 15 | `backlog/2026-09-16-add-a-rename-verb-to-tcw-capabilities-and-tcw-taxonomy` | TCW-27 | request | stays at To Do | priority 35 → high (set); labels capabilities, taxonomy, cli (set); effort medium; complexity medium | intake.md |
| 16 | `backlog/2026-09-19-aggregate-descendant-nodes-taxonomy-and-capabilities-in-tcw-serve` | TCW-54 | discarded (pruned) | To Do → Won't Do | no priority on disk (Medium stands); labels web, taxonomy, capabilities (set) | intake.md |
| 17 | `backlog/2026-09-21-tidy-the-loose-ends-the-combined-v2-5-1-review-found-in-children-and-config-messages` | new | request, or discarded if pruned (D4) | created → To Do (or Won't Do) | no priority; labels tech-debt, cli | intake.md |
| 18 | `backlog/2026-09-21-two-tracker-create-runs-at-once-can-make-two-tickets-for-one-item` | new | discarded (pruned) | created → Won't Do | priority 50 → highest; labels work, cli; `phase: ""` dropped | intake.md |
| 19 | `backlog/2026-09-22-let-a-leftover-start-record-stop-refusing-a-legitimate-rework` | new | discarded (pruned) | created → Won't Do | priority 3 → lowest; labels work, cli, bug; effort low | intake.md |
| 20 | `backlog/2026-09-22-refuse-an-unconfigured-start-before-the-ticket-leaves-triage` | new | discarded (pruned) | created → Won't Do | priority 3 → lowest; labels work, cli; effort low | intake.md |
| 21 | `backlog/2026-09-24-give-a-strict-tracker-claim-past-the-active-status-a-way-forward-instead-of-a-transition-list` | new | discarded (pruned) | created → Won't Do | no priority; labels work, cli | intake.md |
| 22 | `backlog/2026-09-24-make-the-test-suite-run-in-minutes-not-half-an-hour` | new | request | created → To Do | no priority; labels tech-debt | intake.md |
| 23 | `backlog/2026-09-26-decide-whether-a-capability-path-may-name-a-connected-project-by-an-unambiguous-shorthand` | new | request | created → To Do | no priority; labels capabilities | intake.md |
| 24 | `backlog/2026-09-30-compare-git-s-store-root-with-a-project-s-node-path-without-depending-on-letter-case` | new | discarded (pruned) | created → Won't Do | no priority; labels bug, store | initial-request.md, intake.md |
| 25 | `backlog/2026-09-30-follow-renamed-slugs-in-the-web-app-tracker-verbs-and-capability-drift-check` | new | request | created → To Do | no priority; labels web, work, capabilities | initial-request.md, intake.md |
| 26 | `backlog/2026-09-30-keep-an-item-s-folder-in-one-place-and-its-status-only-in-state-yaml` | new | completed (closed as delivered) | created → Done | no priority; labels store, work, tech-debt | initial-request.md, intake.md |
| 27 | `backlog/2026-09-30-let-the-worktree-merge-back-wait-out-a-store-commit-s-index-lock` | new | discarded (pruned) | created → Won't Do | no priority; labels bug, work, tech-debt | initial-request.md, intake.md |
| 28 | `backlog/2026-09-30-run-ci-on-python-3-12-as-well` | new | request | created → To Do | no priority; labels tech-debt; its `slug:` field still says `…-or-3-13-as-well` (renamed in 2.x), dropped with the field | initial-request.md, intake.md |
| 29 | `backlog/2026-10-01-tcw-68-tcw-3-0-a-simpler-work-lifecycle-with-jira-as-a-first-class-backend` | TCW-68 (Epic) | request | stays at To Do | no priority (Medium stands); `type: epic` dropped; the title's `TCW-68 — ` prefix is not a difference | intake.md |
| 30 | `backlog/2026-10-16-make-the-migration-guide-s-test-check-its-2-x-and-3-0-names-against-the-code` | new | request | created → To Do | no priority; no tags; effort medium; complexity medium; blocked by TCW-76: link "TCW-76 blocks <new key>" created | initial-request.md |
| 31 | `active/2026-10-01-tcw-76-migration-guide-from-2-x-to-3-0-0-and-migrate-the-tcw-repository-first` | TCW-76 | implement | stays at In Progress | no priority (Medium stands); parent TCW-68 (already on the ticket); blocked by TCW-75, whose folder 2.x retention deleted: dropped and listed (D5); `owner` dropped, the ticket's assignee (Brian) stands; the `TCW-76 — ` prefix is not a difference | capabilities.yaml, initial-request.md, intake.md, notes-from-tcw-74.md, outcome.md, plan.md, spec.md |
| 32 | `completed/2026-09-15-add-tcw-work-tracker-create-to-make-and-bind-a-ticket-for-an-existing-item` | TCW-9 | completed | In Progress → Done | priority 45 → highest (set); labels remote, work, cli (set); effort high; `owner` dropped, assignee Brian stands; **Jira lagged** (below) | initial-request.md, intake.md, outcome.md, plan.md, refined-outcome.md, spec.md |
| 33 | `completed/2026-09-17-stop-offering-a-version-cut-after-every-completed-work-item` | new | completed | created → Done | priority 45 → highest; labels work, cli, skills, docs; effort medium; complexity medium; `owner` dropped; its `capabilities.yaml` names a removed record (D9) | capabilities.yaml, initial-request.md, outcome.md, plan.md, refined-outcome.md, spec.md |

Dropped from every `state.yaml`: `slug`, `created`, `resolution`, `started`,
`completed` and `phase`. No item has `initiative`, an `external:` blocker or
`type` other than TCW-68's `epic`. `owner` is dropped on items 31, 32 and 33
(Jira mode: it is a git identity, not a Jira account).

After the plan's moves: 17 items at `request` (16 if D4 prunes item 17), 1
at `plan`, 1 at `implement`, 3 at `completed`, 11 at `discarded` (12 with
D4).
Nothing is at `qa`, so no item meets the completion gate's "qa while review
is on" refusal.

### Differences between the folders and the tickets

The folder wins, by the guide's reconciling rules:

- **Summaries:** none differs. TCW-68's and TCW-76's titles carry a leading
  `<KEY> — `, which is not a difference; the summaries stay.
- **Priority:** 11 bound tickets change from `Medium`: TCW-5, TCW-14, TCW-10,
  TCW-21 and TCW-9 to `Highest`; TCW-22, TCW-23, TCW-26 and TCW-27 to `High`;
  TCW-42 to `Low`; TCW-48 to `Lowest`. TCW-33, TCW-39, TCW-40 and TCW-41
  convert to `medium`, already the ticket's; TCW-50, TCW-54, TCW-68 and TCW-76
  have none on disk, so `Medium` stands. Of the new tickets, items 18 and 33
  are set to `Highest` and 19 and 20 to `Lowest`; the rest keep the default.
- **Labels:** every bound ticket but TCW-68 and TCW-76 gains its item's tags
  as labels. No ticket has a label the folder lacks, so nothing is removed.
- **Effort and complexity:** set where the table gives them.
- **Assignee:** never set from disk in Jira mode. The assignees on the tickets
  stand (TCW-9 and TCW-76: Brian; 30 of the 77 tickets have one). The new
  tickets get none unless the project's default assignee sets one.
- **Parent:** TCW-76's parent TCW-68 is already on the ticket. No other item
  has one.
- **Blocks links:** two to create (TCW-14 blocks TCW-10; TCW-76 blocks the new
  ticket of item 30). TCW-76's 2.x blocker TCW-75 is dropped (D5).
- **Jira lagged (TCW-9):** its `tracker.yaml` holds a `sync` record still
  `pending`: `move: start`, at 2026-09-20T21:32:43Z, reason "tracker
  credentials are not set". The ticket is at `In Progress`, so the start was
  made in Jira later, but the 2.x completion never reached it. Step 6 moves it
  to `Done`.

### Tickets to create

16, all of type `Task`, created at `Triage` by the `Create` transition and,
for items, moved by one global transition to the status in the table. None
has a parent, so no child type is needed. The summary is each item's title
exactly, or the inbox entry's first `# ` heading:

| For | Summary | Then |
| --- | --- | --- |
| item 17 | Tidy the loose ends the combined v2.5.1 review found in children and config messages | To Do, or Won't Do (D4) |
| item 18 | Two tracker create runs at once can make two tickets for one item | Won't Do |
| item 19 | Let a leftover start record stop refusing a legitimate rework | Won't Do |
| item 20 | Refuse an unconfigured start before the ticket leaves triage | Won't Do |
| item 21 | Give a strict tracker claim past the active status a way forward instead of a transition list | Won't Do |
| item 22 | Make the test suite run in minutes, not half an hour | To Do |
| item 23 | Decide whether a capability path may name a connected project by an unambiguous shorthand | To Do |
| item 24 | Compare git's store root with a project's node path without depending on letter case | Won't Do |
| item 25 | Follow renamed slugs in the web app, tracker verbs and capability drift check | To Do |
| item 26 | Keep an item's folder in one place and its status only in state.yaml | Done |
| item 27 | Let the worktree merge-back wait out a store commit's index.lock | Won't Do |
| item 28 | Run CI on Python 3.12 as well | To Do |
| item 30 | Make the migration guide's test check its 2.x and 3.0 names against the code | To Do |
| item 33 | Stop offering a version cut after every completed work item | Done |
| inbox `2026-10-13-settle-the-jira-live-check-questions-that-need-a-second-account.md` | Settle the Jira live-check questions that need a second account | stays at Triage |
| inbox `2026-10-15-tidy-what-tcw-74-s-reviews-left-for-the-eval-harness.md` | Tidy what TCW-74's reviews left for the eval harness | stays at Triage |

Each new ticket's description is its request (below); an inbox ticket's is
the entry's whole text. No item is deleted for want of a ticket.

`TCW Project` is set to `tcw` and `TCW Item` to `tcw/<KEY>-<title words>` on
all 33 items' tickets (title words by the guide's Folder names rule, from the
summary as it stands). The folders become, for the bound items:
`TCW-33-decide-whether-tcw-work-scaffold-should-stage-its-draft-in-git`,
`TCW-5-nothing-verifies-that-a-changed-capability-was-actually-changed`,
`TCW-22-fan-the-backlog-audit-out-across-every-connected-work-root`,
`TCW-14-make-tcw-validate-usable-as-a-gate-suppressible-references-and-graded-exit-codes`,
`TCW-23-tcw-provision-cannot-be-scoped-and-a-third-hop-config-can-name-a-checkout-directory`,
`TCW-48-run-the-eval-harness-and-report-what-it-finds`,
`TCW-10-check-the-tracker-s-workflow-against-the-statuses-mapping-in-tcw-validate`,
`TCW-39-check-the-whole-tracked-tree-ledgers-included-for-removed-skill-names`,
`TCW-40-decide-claim-exclusivity-from-a-jira-project-s-workflow-definition`,
`TCW-50-order-and-limit-the-output-of-the-commands-that-list-entities`,
`TCW-42-make-pnpm-prettify-check-pass-on-a-clean-checkout`,
`TCW-41-repair-misplaced-sentences-broken-references-and-overloaded-headings-in-the-guides`,
`TCW-21-test-the-suite-the-way-ci-runs-it-and-notice-red-ci-runs-unpublished-tags-and-a-shadowing-install`,
`TCW-26-write-work-item-properties-to-mapped-tracker-fields`,
`TCW-27-add-a-rename-verb-to-tcw-capabilities-and-tcw-taxonomy`,
`TCW-54-aggregate-descendant-nodes-taxonomy-and-capabilities-in-tcw-serve`,
`TCW-68-tcw-3-0-a-simpler-work-lifecycle-with-jira-as-a-first-class-backend`,
`TCW-76-migration-guide-from-2-x-to-3-0-0-and-migrate-the-tcw-repository-first`,
`TCW-9-add-tcw-work-tracker-create-to-make-and-bind-a-ticket-for-an-existing-item`;
and for the new ones, `<new key>-` followed by the words of the summary
above. TCW-48, TCW-50, TCW-41 and TCW-21 take their (newer) titles' words,
not their 2.x folders'.

### Where each request goes

Read with the guide's last command in "Talking to Jira", for every request
file of every bound ticket:

- **Contained, deleted without posting:** TCW-68's `intake.md` and TCW-76's
  `intake.md`, both 2.x imports byte for byte as their import commits added
  them (`e89d5e6b`, `deecec08`).
- **TCW-76's `initial-request.md`** is not contained, and the description is
  the ticket's own long text: by the guide's default it is posted as a
  comment headed `Request as written in the repository before 3.0`, and the
  description stays (D3).
- **The other 17 bound tickets** (TCW-5, 9, 10, 14, 21, 22, 23, 26, 27, 33,
  39, 40, 41, 42, 48, 50, 54) have a description that is only a binding note
  written when they were bound on 2026-09-20 ("Tracked in the TCW work system
  as `<slug>`. Status: backlog. Artifacts live in the repository under
  docs/work/backlog/<slug>/. …"), which no longer holds after the migration.
  None of their request files is contained. The guide's default posts the
  request as a comment and leaves the note; **the plan recommends "replace"**
  for all 17: the request text becomes the description, and no comment is
  posted (D2). Where an item has both files, the request is
  `initial-request.md` followed by `## Original intake` and `intake.md`
  (none of these intakes is contained in its `initial-request.md`).
- **The 14 new tickets** get the request as their description at creation
  (both files combined the same way where both exist), so step 7 finds them
  contained and posts nothing.

### Comments the migration would post

The exact text of each is in the appendix file given to the owner with this
plan (`tcw76/step1-comments.md` in the session's scratch folder, built from
the files at `2e5e843a`). Each is a fixed first line, a blank line, and the
rest:

- **Closing comments** (step 5, as amended), 12 (13 with D4): on TCW-33,
  TCW-10, TCW-40, TCW-26, TCW-54 and the new tickets of items 18-21, 24 and 27
  (and 17 with D4), the text
  `Closed at the migration to TCW 3.0 as discarded` / blank line /
  `subject removed by TCW 3.0 (TCW-68)`; on the new ticket of item 26,
  `Closed at the migration to TCW 3.0 as completed` / blank line /
  `Delivered by the TCW 3.0 redesign (TCW-68)`.
- **Carried-over verdicts** (step 7), 2: on TCW-9 and on the new ticket of
  item 33, `Carried over from TCW 2.x: qa round 1, verdict accepted` / blank
  line / the item's `refined-outcome.md` exactly (blobs `0ed94053e8` and
  `7406300871`).
- **Request comments** (step 7): 1 on TCW-76,
  `Request as written in the repository before 3.0` / blank line /
  `initial-request.md` exactly (blob `c42f550973`); plus 17 more only for
  tickets where D2 keeps the default.

No status move carries a comment. Nothing else is posted.

### Prune list

Discarded with the reason `subject removed by TCW 3.0 (TCW-68)` (owner,
2026-10-01; spec Design 2 step 1, amendment 3):

- bound: TCW-33 (`scaffold`), TCW-10 (tracker workflow against `statuses`),
  TCW-40 (claim exclusivity), TCW-26 (mapped tracker fields), TCW-54
  (aggregating child boards in `tcw serve`);
- unbound, each given a ticket moved straight to `Won't Do`: items 18
  (two tracker create runs), 19 (a leftover start record), 20 (an
  unconfigured start), 21 (a strict tracker claim), 24 (the 2.x store's git
  root, `FsWorkStore.store_git_root`), 27 (the worktree merge-back's
  `index.lock`).

Closed as delivered, at `completed`: item 26, "Keep an item's folder in one
place and its status only in state.yaml" (owner, 2026-10-01).

Proposed addition (D4): item 17, "Tidy the loose ends the combined v2.5.1
review found in children and config messages". Its three findings are about
2.x code 3.0 deleted: `_complete`'s open-children refusal, the
leftover-store-config report, and `_start`'s call to `_tracked_source` while
recovering an interrupted claim.

Looked at and not proposed: TCW-41 (repair the guides; TCW-75 rewrote most
guides, so it may be partly done, but its subject is still live), and the
items and entries added since 2026-10-01 (item 30 and both inbox entries,
which are about 3.0).

### Ignored discarded folders

37 folders exist only in the primary checkout, hidden by the `.gitignore`
rule `docs/work/discarded/*`; the migration worktree has none. By the owner's
decision of 2026-10-01, **none is kept** unless named now. At step 4 each is
moved out of the primary checkout's work path with a plain `mv`, to
`/Users/brian/Projects/TCW-2.x-ignored-discarded-items/`, a new folder
outside every repository (D6):

1. `2026-06-19-additional-capability-sidecars`
2. `2026-06-19-remote-adapter-jiraworkstore`
3. `2026-06-19-remote-extends-for-taxonomy`
4. `2026-06-19-tracker-sync-for-capabilities`
5. `2026-06-19-typed-taxonomy-relations`
6. `2026-07-02-add-a-vendored-rich-markdown-editor-to-the-local-web-app`
7. `2026-07-03-live-browser-test-pass-for-the-interactive-web-editor`
8. `2026-07-03-per-object-capability-revision-token-fix-file-scoped-409s`
9. `2026-07-22-planning-agnostic-tcw-lifecycle-orchestration`
10. `2026-07-23-capability-first-lifecycle-author-expected-behavior-before-the-spec-attest-tests-at-completion`
11. `2026-07-27-add-tcw-work-methodology-to-resolve-a-stage-s-skill-binding`
12. `2026-08-12-resolve-self-qualified-tcw-links-in-tcw-serve`
13. `2026-08-12-separate-the-agent-plugin-from-the-python-cli-source`
14. `2026-08-18-report-the-missing-skill-caveat-from-tcw-work-lifecycle-rather-than-the-skill`
15. `2026-08-18-serve-version-cut-instructions-from-tcw-config-yaml-instead-of-the-agent-guide`
16. `2026-08-21-nothing-enforces-a-spec-s-declared-capability-deltas-without-a-capabilities-yaml`
17. `2026-08-25-avoid-rescanning-work-items-for-every-tcw-work-reference`
18. `2026-08-31-upstream-the-acceptance-criteria-coverage-table-to-tcw-s-own-spec-stage`
19. `2026-09-01-a-broken-work-path-is-hidden-when-a-repository-is-also-declared`
20. `2026-09-04-let-a-work-store-outside-git-be-read-and-refuse-only-its-writes`
21. `2026-09-04-nothing-lets-a-script-ask-about-a-tombstone`
22. `2026-09-09-distinguish-a-blank-artifact-from-an-absent-one-in-the-web-ui`
23. `2026-09-10-let-a-node-declare-its-own-work-item-state-fields`
24. `2026-09-10-record-a-work-item-s-branch-and-let-a-node-declare-its-own-state-fields`
25. `2026-09-11-refine-the-plugin-skills-and-lifecycle-prompts-against-the-eval-findings`
26. `2026-09-11-validate-a-skill-prompt-binding-names-something-that-exists`
27. `2026-09-14-curate-taxonomy-and-capabilities-documents-in-obsidian`
28. `2026-09-15-eval-runs-under-this-checkout-grade-and-behave-wrongly`
29. `2026-09-15-record-a-time-of-day-and-timezone-offset-in-every-timestamp-tcw-writes`
30. `2026-09-15-record-lasting-evidence-of-a-tracker-hold-on-a-shared-ticket`
31. `2026-09-16-close-three-gaps-the-pr-45-review-left-in-tracker-delivery`
32. `2026-09-16-record-a-blocker-naming-a-resolved-item-as-a-slug-not-as-free-text`
33. `2026-09-21-a-create-response-that-never-arrives-leaves-a-ticket-nothing-can-find`
34. `2026-09-21-decide-whether-capabilities-drift-should-judge-a-shared-master-ledger-s-missing-defaults`
35. `2026-09-21-one-definition-of-a-valid-created-record`
36. `2026-09-21-report-a-missing-taxonomy-path-as-a-validate-problem-instead-of-crashing-inside-the-capabilities-check`
37. `2026-09-21-say-that-a-tcw-config-yaml-edit-was-staged-so-git-diff-showing-nothing-isn-t-a-surprise`

### Inbox entries

2 (the plan's count of seven on 2026-10-15 went down when the pre-freeze
clean-up item took five). Each becomes a ticket at `Triage` at step 6 (table
above), and its file is deleted at step 8:

- `2026-10-13-settle-the-jira-live-check-questions-that-need-a-second-account.md`
- `2026-10-15-tidy-what-tcw-74-s-reviews-left-for-the-eval-harness.md`

### Tickets without items

None. Every ticket at `To Do` or `In Progress` is bound to an item; the other
58 are at `Done` or `Won't Do`. TCW-69 to TCW-75 and TCW-77 (TCW-68's
children, `Done`, their folders deleted by 2.x retention) become untracked
references under TCW-68. Whether to give them, and TCW-67, `TCW Project`
alone is D8.

### Rewrites

**Configuration** (step 3), key by key from `tcw-config.yaml`; there is no
`tcw-config.local.yaml`:

| 2.x | 3.0 |
| --- | --- |
| `work.tracker.provider: jira-cloud` | `work.backend: jira` |
| `work.tracker.base-url` | `work.jira.site` |
| `work.tracker.credentials` | `work.jira.credentials`, the same two variables |
| `work.tracker.statuses` (`backlog`, `active`, `review`, `completed`, `discarded`) | `status` on `request`, `implement`, `review`, `completed`, `discarded` |
| `work.tracker.pre-backlog: {Triage: Accept}` | `work.stages.inbox.status: Triage`; `Accept` dropped |
| `work.tracker.inbox-query` (`project = TCW AND status = Triage`) | dropped: it only selects the inbox status |
| `work.tracker.candidate-query`, `work.tracker.transitions.start` | removed |
| (none) | `work.jira.project: TCW`; `work.jira.fields` (the four fields); `issue-type`, `timeout` and `priorities` left at their defaults; `status` for `spec`, `plan`, `qa` |
| `work.retain` | removed (3.0 never deletes) |
| `work.lifecycle.stages.spec/plan/implement` | `work.stages.*`, with `pre` and `prompt` kept and `builtin: true` written `inherit: true` |
| `work.lifecycle.artifacts.spec` | prompt entries of `spec`: `spec-bug.md` when `tags: [bug]`, `spec.md` when `not_tags: [bug]` (the guide's example); both templates already open with their outline line (Task A3) |
| `work.lifecycle.transitions.complete.pre: tcw validate` | `work.stages.completed.pre` |
| `work.procedures.create-work` | kept, `builtin` written `inherit` |
| `work.tags` | kept |
| `work.documentation` | kept; `Tracker-Change` becomes `Jira-Change` with a new description, `Guide-Topic-Change` names it, the two `upcoming/<slug>.md` paths become `upcoming/<folder>.md`, and `Configuration-Key-Change` no longer names `docs/work/dod.yaml` (spec Design 6.4) |
| the git example | adopted (owner, 2026-10-01; spec Design 6.5): the pull text heads every stage's prompt, and `post: command: sh docs/guide/examples/commit-item-after-move.sh` is on every stage from `request` to `discarded`; no push hook |
| `docs/work/dod.yaml` | its entries go to the completion and records gates and to `docs/lifecycle/review.md` (spec Design 6.3); "originating GitHub issue" stays in `AGENTS.md` |

The proposed file in full:

```yaml
id: tcw
work:
  backend: jira
  jira:
    site: https://proposit.atlassian.net
    project: TCW
    credentials:
      email-env: TCW_JIRA_EMAIL
      token-env: TCW_JIRA_API_KEY
    fields:
      project: TCW Project
      item: TCW Item
      effort: Effort
      complexity: Complexity
  tags:
  - bug
  - capabilities
  - cli
  - docs
  - remote
  - skills
  - store
  - taxonomy
  - tech-debt
  - web
  - work
  documentation:
  - path: README.md
    trigger: Public-API
    description: 'Public-facing overview: what TCW is, installation, each axis and its
      skills and CLI, the work lifecycle and Jira, the local web app, and contributor
      setup; plain, high-readability. Update when the public CLI surface or user-facing
      behavior changes.'
  - path: docs/guide/jira.md
    trigger: Jira-Change
    description: User-facing guide to the Jira backend; plain language. Update whenever
      what a `tcw work` command does to a ticket, a `work.jira` key, a stage's `status`,
      or `tcw work tickets list` or `tcw work tickets adopt` changes.
  - path: docs/guide/<topic>.md
    trigger: Guide-Topic-Change
    description: The long-form user guides, one per topic — taxonomy and capabilities,
      multi-repo, linking and validation, and the rest of docs/guide/. Update the
      guide whose topic a change touches, in plain language. Fires on more than a
      CLI surface change — it also covers where a setting is declared, what a command
      writes to disk, and which files TCW treats as its own records, because a guide
      that names a file or a key goes stale silently when that moves. docs/guide/jira.md
      has its own entry and is covered by Jira-Change instead.
  - path: docs/release-notes/upcoming/<folder>.md
    trigger: Public-API
    description: User-facing release notes for the next version; plain language, no
      jargon or internal module names. One file per work item, named by the item's
      folder name, never its full slug; never edit another item's file. The folder's
      README.md says how to write one.
  - path: docs/changelogs/upcoming/<folder>.md
    trigger: Any-Code-Change
    description: Developer changelog for the next version; technical, grouped under
      `##` Added/Changed/Fixed/Removed/Internal headings. One file per work item,
      named by the item's folder name, never its full slug; never edit another
      item's file.
  - path: skills/<component>/SKILL.md
    trigger: Skill-Driven-Component
    description: The driving skills (`work`, `capabilities`, …) that teach
      agents to operate each component through its CLI. Always update the matching
      skill whenever the component it drives changes — its CLI surface, model/fields,
      lifecycle, or guardrails — so the skill never drifts from the tool. How to configure
      a component goes to `configure`, not to the component's skill.
  - path: skills/configure/references/<document>.md
    trigger: Configuration-Key-Change
    description: How to declare or change each configuration setting. Update the matching
      document whenever a key in `tcw-config.yaml`, a component config file, or a
      `TCW_PROJECT_<ID>`-style variable is added, removed, or changes meaning.
  procedures:
    create-work:
    - inherit: true
    - file: docs/procedures/create-work.md
  stages:
    inbox:
      status: Triage
    request:
      status: To Do
      prompt: &pull-first
      - blob: &pull-text >-
          Before you start, bring this checkout up to date with
          `git pull --ff-only`. If the folder that
          `tcw work path <item>` prints is inside a different
          git repository, also run
          `git -C <that folder> pull --ff-only`. If either
          pull fails, tell the user and carry on with what
          you have.
      - inherit: true
      post: &commit-after-move
      - command: sh docs/guide/examples/commit-item-after-move.sh
    spec:
      status: Specifying
      prompt:
      - blob: *pull-text
      - inherit: true
      - file: docs/lifecycle/abstraction.md
      - file: docs/lifecycle/harness.md
      - file: docs/lifecycle/templates/spec-bug.md
        when:
          tags:
          - bug
      - file: docs/lifecycle/templates/spec.md
        when:
          not_tags:
          - bug
      post: *commit-after-move
    plan:
      status: Planning
      pre:
      - command: python scripts/require_artifact.py spec
      prompt:
      - blob: *pull-text
      - inherit: true
      - file: docs/lifecycle/abstraction.md
      post: *commit-after-move
    implement:
      status: In Progress
      pre:
      - command: python scripts/require_artifact.py spec
      - command: python scripts/require_artifact.py plan
      prompt:
      - blob: *pull-text
      - inherit: true
      - file: docs/lifecycle/implementation.md
      - file: docs/lifecycle/harness.md
      post: *commit-after-move
    review:
      status: In Review
      prompt:
      - blob: *pull-text
      - inherit: true
      - file: docs/lifecycle/review.md
      post: *commit-after-move
    qa:
      status: In QA
      prompt: *pull-first
      post: *commit-after-move
    completed:
      status: Done
      pre:
      - command: tcw validate
      post: *commit-after-move
    discarded:
      status: Won't Do
      post: *commit-after-move
    postmortem:
      prompt: *pull-first
```

**Hooks:** the configuration binds `python scripts/require_artifact.py spec`
and `… plan` (already 3.0's, Task A2), `tcw validate`, and, new,
`sh docs/guide/examples/commit-item-after-move.sh`. No hook reads
`TCW_STATUS`, `TCW_TRANSITION`, `TCW_NODE_ROOT` or `TCW_RESOLUTION`. Each use
of `TCW_SLUG` takes it as the full slug, which is right in 3.0:
`require_artifact.py` passes it to `tcw work path` (lines 9, 15, 33, 35), and
the commit script uses it in the commit message (line 10). No status values
are compared, no `skill` is in a `pre`, and there is no `when: {type: …}`.

**Capability records** (step 10): the `Planning doc:` line is removed from
13 records (`capabilities/detect-capability-drift`, `web/choose-a-theme`,
`cli/install-from-pypi`, `work/read-the-documentation-gate-for-a-change`,
`work/retitle-a-work-item`, `work/discard-a-work-item`,
`work/decompose-a-work-item-into-children`,
`work/declare-the-work-stores-home-repository`,
`work/configure-the-work-store-location`, `work/manage-the-work-inbox`,
`skills/extras-report`, `skills/configure`, `skills/taxonomy`). No record has
`Tracker:`, and none links `connected-project-registry`. In the two items'
`capabilities.yaml`, nothing to convert (no `added:`, no list form); item
33's names a removed record (D9).

**The project's own files** (step 10):

- `AGENTS.md` (`CLAUDE.md` is a link to it): "Work Planning and
  Implementation" rewritten for 3.0 as spec Design 7 says (`advance
  --dry-run` instead of `stage gate` at line 16, the bindings table gaining
  `review` and `completed`, the exception rewritten as Design 8.6 says, the
  GitHub-issue paragraph without `dod.yaml` and `refined-outcome.md`, and when
  TCW's own process advances an item to `implement`); Versioning's
  `upcoming/<work-item-slug>.md` becomes `upcoming/<work-item-folder>.md`. The
  worktree and eval sections are left as they are.
- `.gitignore`: lines 28-30 (the comment "Discarded work: …", the rule
  `docs/work/discarded/*` and its `!…/.gitkeep`) removed;
  `/tcw-config.local.yaml` added.
- `tests/doc_allowance.py`: `tcw work stage gate` removed from
  `REMOVED_COMMANDS` in the same commit (spec amendment 23).
- Already done in Part A, so step 10 finds them clean:
  `scripts/require_artifact.py`, both templates, `docs/lifecycle/review.md`,
  `docs/procedures/create-work.md`.

### `<hook files>`

`tcw-config.yaml`, `scripts/require_artifact.py`,
`docs/guide/examples/commit-item-after-move.sh`,
`docs/lifecycle/abstraction.md`, `docs/lifecycle/harness.md`,
`docs/lifecycle/implementation.md`, `docs/lifecycle/review.md`,
`docs/lifecycle/templates/spec.md`, `docs/lifecycle/templates/spec-bug.md`,
`docs/procedures/create-work.md`, `AGENTS.md`, `CLAUDE.md`. (`tcw validate`
runs no file of the project's.)

### Step 9

- **Skipped:** this log, and TCW-76's whole folder
  (`TCW-76-migration-guide-from-2-x-to-3-0-0-and-migrate-the-tcw-repository-first`
  after step 6), since both name the old folders on purpose.
- **Open item folders searched:** every item folder at `request`, `plan` or
  `implement` after the migration except TCW-76's: the 17 (16 with D4) at
  `request` and TCW-50's at `plan`.
- **Live documents searched:** `tcw-config.yaml` and every file git tracks
  outside the work path, except `docs/changelogs/`, `docs/release-notes/`,
  `docs/plan/`, `docs/superpowers/`, the `docs/migration-guide-*` files, this
  log and `tests/fixtures/`. Read today, none of them names a current item
  folder or a `renames.yaml` slug.
- **Old names:** the 33 folder names above and the two old slugs of
  `renames.yaml`
  (`2026-09-30-report-a-slug-held-by-two-folders-in-tcw-validate-instead-of-crashing`,
  whose item was completed and deleted, and
  `2026-09-30-run-ci-on-python-3-12-or-3-13-as-well`, now item 28).
- In the open items, 6 request files (TCW-5's, TCW-14's, both of TCW-41's,
  and those of items 22 and 28) and TCW-50's `plan.md` name items by their
  2.x folders. In Jira mode the request files go to Jira at steps 6 and 7,
  before step 9 runs (D10).

### Decisions for the owner

- **D1.** Approve this plan as a whole, with the answers below.
- **D2.** Request placement for the 17 tickets whose description is the
  2026-09-20 binding note (TCW-5, 9, 10, 14, 21, 22, 23, 26, 27, 33, 39, 40,
  41, 42, 48, 50, 54). Recommended: **replace** the note with the request
  text. Otherwise: the guide's default (post the request as a comment, keep
  the note), or append.
- **D3.** TCW-76's `initial-request.md`. Recommended: the guide's default,
  a comment, keeping the ticket's own description. Or replace, or append.
- **D4.** Add item 17 (tidy the v2.5.1 review's loose ends) to the prune
  list. Recommended: yes.
- **D5.** TCW-76's 2.x blocker TCW-75 (folder deleted by retention).
  Recommended: drop it, as the amended guide says (TCW-75 is `Done`).
  Otherwise: also link "TCW-75 blocks TCW-76" in Jira, where it shows as
  untracked.
- **D6.** The folder outside the repository that the 37 ignored discarded
  folders move to at step 4:
  `/Users/brian/Projects/TCW-2.x-ignored-discarded-items/`, or another path.
  Confirm that none is kept.
- **D7.** A tag marking the 2.x state (the guide's "Before you start"; none
  was made, since step 0 changes nothing outside the migration worktree).
  Recommended: `git tag tcw-2.x-final 8b5a212b`, `main`'s frozen tip, the
  last commit whose code and board are both 2.x; or on the freeze commit
  `3b71ea78`; or none.
- **D8.** `TCW Project` alone (`tcw`) on the tickets of the redesign that
  have no item: TCW-69 to TCW-75 and TCW-77, and TCW-67 (spec Design 4.5).
  Recommended: yes. The guide's steps make no such write on their own.
- **D9.** Item 33's `capabilities.yaml` declares
  `changed: work/customize-the-definition-of-done`, a record TCW-70 deleted
  (`cb6b7578`). In 3.0 `tcw capabilities drift` reports a finished item's
  declaration of a record that is not in the ledger. Recommended: remove that
  one line at step 7 (the guide's "corrected where needed"), and say so in
  the log; or keep it and accept the drift finding.
- **D10.** Old folder names inside request text that steps 6 and 7 put into
  Jira (the 6 request files of open items named under Step 9). Step 9 rewrites only files, so in Jira
  mode it cannot reach them. Recommended: leave them as written (git history
  resolves them), and amend the guide's step 9 to say so for Jira mode.
  Otherwise: rewrite them in the text before it is posted at steps 6 and 7,
  which the guide would then have to describe.
- **D11.** The Jira changes listed under "Jira changes", applied by the agent
  in the owner's Chrome profile, including TCW's own copies of the screens.
- **D12.** For information, not a choice: in Jira mode an item's creation
  date is its ticket's, so the 14 new tickets give their items the date
  2026-10-16, which `tcw work list` and drift's "newest declaration wins"
  ordering then read (item 33 is the only one of them with a
  `capabilities.yaml`).

### The owner's answer

(Not yet given.)
