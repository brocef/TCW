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
- **(f) 3.0 is not made everyone's `tcw` at step 11.** The guide's step 11
  installs the released 3.0 and updates the plugin. 3.0.0 is cut and
  published only at Task B24, so step 11 ran the private environment
  `tcw76/venv` (this worktree's 3.0 code) first on `PATH`, as the plan's rules
  say, and the shared install and the plugins are left for B24.

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

In step 3, one more (recorded in full under Step 3 below):

4. **The scratch folder left bound files out, and the check could not see
   it.** Step 3's snippet copied `docs/lifecycle/*.md`, 5 of the 9 files
   TCW's configuration binds (not the two templates, `create-work.md`, or the
   two hook scripts), and the step treated "a finding naming a bound file" as
   something `tcw validate` reports. It does not: 3.0 reads a `file:` binding
   only when it composes a prompt. Step 3 now copies every bound file, and
   composes every stage's prompt and every bound procedure in the scratch
   folder as part of its check.

In step 9, one more (D10, recorded under Step 9 below):

5. **Text already in Jira.** Step 9 said to rewrite old names "in the
   documents of open items", but in Jira mode steps 6 and 7 had already put
   the requests and acceptance history into tickets, and step 9 rewrites only
   files. Step 9 now says that in Jira mode an old folder name inside text
   already posted to Jira is left as written, and that git history resolves
   it.

In step 12, one more (recorded under Step 12 below):

6. **Files someone else installed.** Step 12 said to read every file the
   search prints in full, but its `WORDS` list (start, release, claim,
   verify, …) also prints every skill a harness or another plugin installed:
   on this machine 99 such files, Office XML schemas and library scripts
   among them, none naming `tcw` or `TCW`. Step 12 now says such a file is
   read where it matches `NAMES`, and enough of the rest to confirm it is not
   about TCW, and is listed with that reason.

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

**Check:** `grep -c '^## Approved plan' docs/tcw-3.0-migration-log.md`
printed `1`.

## Approved plan

Status: **approved by the owner on 2026-10-16**, every decision as
recommended (D2 replace, D3 comment, D4 prune, D5 drop, D6 move none kept, D7
tag `tcw-2.x-final` on `8b5a212b`, D8 yes, D9 remove the line, D10 leave and
amend the guide, D11 the agent applies the Jira changes). The answer is
recorded word for word at the end of this section.

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

Given in chat on 2026-10-16:

> Approve as recommended

## Run 1, after the approved plan

### Step 2: Jira mode: prepare Jira

The workflow was read again before any change (`POST /rest/api/3/workflows`
for `TCW work`, id `e42df41b-b7d8-4dd2-9cf1-ff67bd7a6679`, version 1): as in
the checklist. `TCW work scheme` (10039) is used by `TCW` alone, and `TCW
work` by that scheme alone, so the change reaches no other project. Nothing
runs 2.8 against the project any more: `main`'s board is frozen (Task B3).

The changes were applied by the agent through Jira's REST interface on
2026-10-16, with the owner's account (site administrator), instead of in the
owner's browser (deviation b): each one can be read back exactly. The
permission check of the agent's session held the first write until the owner
said, in chat, "Try to make the change again".

Checklist (TCW-76 `outcome.md`, "Jira checklist") and each confirmation:

1. **Statuses `Specifying`, `Planning`, `In QA` added to `TCW work`.**
   Applied with `POST /rest/api/3/workflows/update` (checked first with
   `/workflows/update/validation`: no errors); the workflow is at version 2.
   Confirmed: `GET /rest/api/3/project/TCW/statuses` lists the nine statuses
   for each of `Task`, `Sub-task`, `Bug` and `Epic`.
2. **One global transition into each of the nine statuses**, named after it,
   no screen, condition or validator (ids 101 to 181). Confirmed: `GET
   /rest/api/3/issue/TCW-76/transitions?expand=transitions.fields` and the
   same for `TCW-9` list exactly one transition to each of the nine statuses,
   none with a field. Jira also lists the transition into the ticket's own
   status, which a global transition always offers; 3.0 never moves a ticket
   to the stage it is at.
   **Addition to the checklist:** each new transition keeps 2.x's resolution
   post-function, an action run after the move and not a screen, condition or
   validator: the one into `Done` sets the resolution `Done` (10000), the one
   into `Won't Do` sets `Won't Do` (10001), and the other seven clear it, as
   `Accept`, `Start`, `Submit`, `Rework`, `Reopen`, `Complete` and `Cancel`
   did. 3.0 does not read the resolution; Jira's "unresolved" filters and
   resolved dates do.
3. **`Accept`, `Start`, `Submit`, `Complete`, `Rework`, `Cancel`, `Stop` and
   `Reopen` deleted; `Create` kept**, in the same update. Confirmed: the
   workflow's transitions are `Create` (initial, to `Triage`) and the nine
   global ones, and no status other than `Triage` (by `Create` and its global
   transition, as intended) is reached by two.
4. **Published.** The update applies to the active workflow directly; there is
   no separate draft. Confirmed: the scheme still has `defaultWorkflow: TCW
   work` and no issue type mappings, and the 77 tickets keep their statuses
   (26 `Done`, 2 `In Progress`, 17 `To Do`, 32 `Won't Do`; the same counts as
   before).
5. **TCW's own screens** (deviation c). The source screens are named `PRPI:
   Kanban Default Issue Screen` (10010), `PRPI: Kanban Bug Screen` (10011) and
   `PRPI: Kanban Epic Screen` (10012), one tab each; the copies take TCW's
   prefix: `TCW: Kanban Default Issue Screen` (10051), `TCW: Kanban Bug
   Screen` (10052), `TCW: Kanban Epic Screen` (10053), each with its source's
   fields in the same order followed by `TCW Project`, `Effort` and
   `Complexity`. Screen schemes `TCW: Kanban Default Screen Scheme` (10049),
   `… Bug Screen Scheme` (10050), `… Epic Screen Scheme` (10051), each using
   its screen for create, edit and view as the PRPI ones do. Issue type screen
   scheme `TCW: Kanban Issue Type Screen Scheme` (10037): default → 10049,
   `Bug` → 10050, `Epic` → 10051, as 10002 maps PRPI's; assigned to `TCW`.
   Confirmed: `GET /rest/api/3/issuetypescreenscheme/project` shows 10037 for
   `TCW` and 10002 for `PRPI` alone; the create metadata of all four types
   lists `TCW Project`, `TCW Item`, `Effort`, `Complexity`, `Summary`,
   `Labels`, `Assignee`, `Priority` and, except on `Epic` (the top of the
   hierarchy, where the guide does not need it), `Parent`; the edit metadata
   of `TCW-76` (`Task`), `TCW-9` (`Task`) and `TCW-68` (`Epic`) lists the
   same. No `Bug` or `Sub-task` ticket exists to read an edit screen on; each
   type uses one screen for create and edit, so the create read covers it.
   PRPI's three screens list the same fields as before the change.
6. **No other workflow.** Confirmed by the scheme read under 4.

**Check:** the Jira-workflow reading at the end of step 3.

### Step 3: Rewrite the configuration

`tcw-config.yaml` was replaced by the proposed file of the approved plan
("Rewrites"), byte for byte as the plan holds it. There is no
`tcw-config.local.yaml`. Both spec templates already open with their outline
line (Task A3). The configuration declares no connected projects, so no
`TCW_PROJECT_<ID>` variable was set.

**Amendment 4, made during the step.** The first scratch run followed the
guide's snippet literally: it copied only `docs/lifecycle/*.md`, and
`tcw validate --remote` reported no configuration finding although
`docs/lifecycle/templates/spec.md`, `spec-bug.md` and
`docs/procedures/create-work.md` were missing. Removing
`docs/lifecycle/review.md` too still gave `0 errors, 0 warnings` from
`tcw validate`. 3.0's own reference (`skills/configure/references/work.md`,
"Binding kinds") does not say `validate` opens bound files, so this is not a
3.0 defect; in the same folder `tcw work stage prompt spec` exited 1 with
`file 'docs/lifecycle/templates/spec.md' no longer exists`, and
`tcw work procedure create-work` with the same for `create-work.md`. The
guide was fixed (amendment 4 above), the composing loops were confirmed to
print `stage spec` and `procedure create-work` in that incomplete folder, and
the step was redone in a fresh scratch folder from the fixed text.

The scratch folder (`tcw76/step3.nZx7` in the session's scratch folder) holds
`tcw-config.yaml`, the seven `file:` targets (`docs/lifecycle/abstraction.md`,
`harness.md`, `implementation.md`, `review.md`,
`docs/lifecycle/templates/spec.md`, `spec-bug.md`,
`docs/procedures/create-work.md`), the two hook scripts
(`scripts/require_artifact.py`, `docs/guide/examples/commit-item-after-move.sh`),
empty `docs/work`, `docs/taxonomy` and `docs/capabilities`, and a fresh git
repository. `tcw validate --remote` (the 3.0 CLI, `tcw76/venv`, imported from
this worktree) printed:

```text
tcw: the credentials and Jira project TCW are readable
tcw: moves read from the workflow definition had their screen fields left unchecked; only a sample ticket shows them
tcw: 0 item folders checked against their tickets
tcw: the model checks ran over 0 items
0 errors, 1 warning, 0 unresolved
warning: work.jira: unchecked: the Sub-task edit screen: no Sub-task ticket in TCW to sample
exit 0
```

Each line read:

- **Configuration findings:** none.
- **Jira-workflow findings:** none: no move with two candidate transitions,
  no missing status, no screen asking for more than a comment. Nothing goes
  back to step 2.
- **`unchecked:` warnings, listed for step 11:** the `Sub-task` edit screen.
  Step 2 read the `Sub-task` create screen, which every type here uses for
  create and edit alike (step 2, line 5), so the fields are there; no
  `Sub-task` ticket exists to read the edit screen on.
- **The note on moves' screen fields** is not a finding. 3.0 read the moves
  from the workflow definition and says it left their screen fields
  unchecked. Step 2 read them on sample tickets (`TCW-76` and `TCW-9`, with
  `expand=transitions.fields`): one transition into each of the nine
  statuses, none with a field. Listed for step 11, which reads them again on
  the real items.
- **Other findings:** none.

The two composing loops of the amended step, in the same folder, printed
nothing, and `ls docs/lifecycle/templates/spec-bug.md` (the one binding whose
`when:` lists `tags`) found the file.

Tests: the files that read the guide or this log
(`tests/config/test_personal_merge.py`, `tests/test_capabilities_cli_contract.py`,
`tests/test_docs_describe_3_0.py`, `tests/test_documented_cli_surface.py`,
`tests/test_migration_guide.py`, `tests/test_projects_list.py`,
`tests/test_upcoming_entries.py`, `tests/test_validate_command.py`,
`tests/work/test_cli_config.py`), `tests/test_documentation_sync_wiring.py`,
and the standing guard files passed: 1285 passed, 6 skipped. No test reads
the repository's own `tcw-config.yaml` until Task B17 writes
`tests/test_repo_lifecycle.py`. `pytest --collect-only -q` collected 5275
tests.

**Check:**
`grep -nE '^[[:space:]]*(tracker|lifecycle|retain|auto-commit-transitions|publish-transitions|trunk-branch):|builtin: true|^connected-projects:' tcw-config.yaml`
printed nothing (exit 1); the scratch run printed no configuration finding
and no Jira-workflow finding other than the one `unchecked:` warning; the two
composing loops printed nothing. This is step 2's check too: it passes.

### Step 4: Flatten the store and give every item a stage

**Items.** Each of the 33 item folders was moved with `git mv` from its
status folder to the top of the work path (30 from `backlog/`, 1 from
`active/`, 2 from `completed/`). There was no nested child: no `state.yaml`
lies deeper than `docs/work/<status>/<folder>/`. In Jira mode no folder is
renamed here; each takes its `<KEY>-<title words>` name at step 6. Each
folder got an `item.yaml` holding its `title`, copied from its `state.yaml`
unchanged (the `TCW-68 — ` and `TCW-76 — ` prefixes included, which step 6's
reconciling drops), and its `stage`, from the approved plan's item table with
D4 applied: 16 at `request`, 1 at `plan` (TCW-50), 1 at `implement` (TCW-76),
3 at `completed` (TCW-9, item 26, item 33), 12 at `discarded` (the prune list
and item 17). Read against the guide's Status folders rule, the only stages
that differ from it are those 13 the plan closes, as the amended step 4 says.

**`renames.yaml`**, its two pairs, for step 9:

```text
2026-09-30-report-a-slug-held-by-two-folders-in-tcw-validate-instead-of-crashing -> 2026-09-30-refuse-instead-of-crashing-when-a-slug-is-held-by-two-folders
2026-09-30-run-ci-on-python-3-12-or-3-13-as-well -> 2026-09-30-run-ci-on-python-3-12-as-well
```

**Ignored folders** (D6, none kept). The worktree has none. In the primary
checkout, `git -C /Users/brian/Projects/TCW status --ignored --porcelain -- docs/work`
listed the same 37 folders as the plan, all under `docs/work/discarded/`.
Each was moved with a plain `mv` to
`/Users/brian/Projects/TCW-2.x-ignored-discarded-items/`, made for them and
outside every repository, which now holds 37 folders. Afterwards the same
`git status --ignored` command printed nothing, the primary checkout's
`docs/work/discarded/` holds only its tracked `.gitkeep`, and
`git -C /Users/brian/Projects/TCW status --porcelain` printed nothing, with
`main` still at `8b5a212b`. Nothing else in the primary checkout was touched.

**Deleted.** `find docs/work/backlog docs/work/active docs/work/review docs/work/blocked docs/work/completed docs/work/discarded -mindepth 1 ! -name .gitkeep 2>/dev/null`
printed nothing first. Then the six status folders with their `.gitkeep`
files, `graveyard.yaml`, `dod.yaml` and `renames.yaml` were removed with
`git rm`. `inbox/` stays for step 8.

**Check:**
`find docs/work -mindepth 1 -maxdepth 1 -type d \( -name backlog -o -name active -o -name review -o -name blocked -o -name completed -o -name discarded \)`
printed nothing, and
`for d in docs/work/*/; do [ "$d" = docs/work/inbox/ ] || [ -f "$d/item.yaml" ] || echo "$d"; done`
printed nothing. `docs/work` holds 33 item folders and `inbox/`.

Tests: the files that read the guide or this log (as at step 3), the tests
naming the deleted store-root files (`tests/test_validate.py`,
`tests/work/test_cli_items.py`, `tests/work/test_fs_backend.py`,
`tests/work/test_no_2x_names.py`, all on fixtures, none on this board), and
the standing guard files: 1437 passed, 17 skipped. `docs/work/` is archival in
`tests/test_documented_cli_surface.py`, so the moved documents are not read as
live ones. `pytest --collect-only -q` collected 5275 tests.

### Step 5: Convert item fields

Every `state.yaml` (33) was converted into its item's `item.yaml`, one key
per line in the order of the guide's example, and then removed with `git rm`:

- **`priority`** as a name: 19 items had one, now 7 `highest`, 4 `high`, 4
  `medium`, 1 `low`, 3 `lowest`. The 14 with none have no `priority` key: in
  Jira mode the ticket's own priority stands.
- **`effort`** (15 items), **`complexity`** (6) and **`tags`** (30) as they
  were. TCW-48's and TCW-41's empty `blocked_by: []` give no key.
- **`parent`**: TCW-76's, as `tcw/2026-10-01-tcw-68-tcw-3-0-a-simpler-work-lifecycle-with-jira-as-a-first-class-backend`
  (the folder's name after step 4).
- **`blocked-by`**: TCW-10's, as
  `[tcw/2026-09-01-make-tcw-validate-usable-as-a-gate-suppressible-references-and-graded-exit-codes]`,
  and item 30's, as
  `[tcw/2026-10-01-tcw-76-migration-guide-from-2-x-to-3-0-0-and-migrate-the-tcw-repository-first]`.
  TCW-76's blocker `2026-10-01-tcw-75-documentation-for-tcw-3-0-readme-guides-and-the-opt-in-git-example`
  was dropped and is listed here: 2.x retention deleted its folder (D5). No
  item had an `external:` blocker or an `initiative`.
- **Dropped:** `slug`, `created`, `resolution`, `started`, `completed`,
  `phase` (item 18's empty one) and `type` (TCW-68's `epic`); `owner` on
  TCW-9, TCW-76 and item 33, since in Jira mode it is a git identity, not an
  account.

Each item's converted `priority`, `effort`, `complexity` and `tags` were
compared with the approved plan's item table, row by row: all 33 agree.

**Comments.** No item was discarded under 2.x (the tracked `discarded/` was
empty, and none of the ignored ones is kept), so no `Carried over from TCW
2.x: discarded as …` comment arises. The 13 items the plan closes (12 at
`discarded`, item 26 at `completed`) each get the comment whose first line is
`Closed at the migration to TCW 3.0 as <stage>`, with the plan's reason. In
Jira mode those are posted at step 6, so no `comments/` file was written.

`tracker.yaml` stays, as Jira mode says: 19 files, one per bound item, for
step 6 to read the ticket keys from.

Tests: as at step 4: 1437 passed, 17 skipped; `pytest --collect-only -q`
collected 5275 tests.

**Check:** `find docs/work -name state.yaml` printed nothing, and
`grep -nE '^priority: [0-9]' docs/work/*/item.yaml` printed nothing (exit 1).

### Step 6: Jira mode: bind items to tickets

Made on 2026-10-20 through Jira's REST interface, every request through one
script that logs each call, with the owner's account
(`557058:f365e97a-cd5d-4f27-a5c2-b5dc8dbad702`). Every write was preceded by
the read of rule 6. Request bodies were built with `jq` and the guide's `ADF`
functions, which were compared with the guide's block first (identical).

**Read first.** The 19 bound tickets and the 9 of D8 were read with every
field the guide names, and their comments: each was as the approved plan
describes it (`Medium`, no labels, no effort, complexity, `TCW Project` or
`TCW Item`, no `Blocks` link, no comments; TCW-76's parent TCW-68). The search
`project = TCW AND reporter = currentUser() AND created >= "2026-10-15"`
(the day before the start date) found nothing, so no ticket of this run
existed yet.

**The approved text.** Every comment and request text of the appendix
(`tcw76/step1-comments.md`, built from `2e5e843a`) was derived again from the
files at `38e6b82b` and compared: all 32 are identical. Between the two
commits every document was only moved (`git diff -M --name-status` shows
`R100` for each), so the files are the same. The longest text is 14012
characters, under Jira's limit of 32767.

**Pass 1, tickets.** 16 created, each of type `Task`, at `Triage` by
`Create`, with the request as its description (both files combined as the
plan says where an item has both; an inbox entry's whole text). Each item's
`ticket:` line was written into its `item.yaml` straight after its create
answer, and the search was repeated before each create.

| Key | For | Summary |
| --- | --- | --- |
| TCW-78 | item 33 | Stop offering a version cut after every completed work item |
| TCW-79 | item 17 | Tidy the loose ends the combined v2.5.1 review found in children and config messages |
| TCW-80 | item 18 | Two tracker create runs at once can make two tickets for one item |
| TCW-81 | item 19 | Let a leftover start record stop refusing a legitimate rework |
| TCW-82 | item 20 | Refuse an unconfigured start before the ticket leaves triage |
| TCW-83 | item 21 | Give a strict tracker claim past the active status a way forward instead of a transition list |
| TCW-84 | item 22 | Make the test suite run in minutes, not half an hour |
| TCW-85 | item 23 | Decide whether a capability path may name a connected project by an unambiguous shorthand |
| TCW-86 | item 24 | Compare git's store root with a project's node path without depending on letter case |
| TCW-87 | item 25 | Follow renamed slugs in the web app, tracker verbs and capability drift check |
| TCW-88 | item 26 | Keep an item's folder in one place and its status only in state.yaml |
| TCW-89 | item 27 | Let the worktree merge-back wait out a store commit's index.lock |
| TCW-90 | item 28 | Run CI on Python 3.12 as well |
| TCW-91 | item 30 | Make the migration guide's test check its 2.x and 3.0 names against the code |
| TCW-92 | inbox `2026-10-13-settle-the-jira-live-check-questions-that-need-a-second-account.md` | Settle the Jira live-check questions that need a second account |
| TCW-93 | inbox `2026-10-15-tidy-what-tcw-74-s-reviews-left-for-the-eval-harness.md` | Tidy what TCW-74's reviews left for the eval harness |

TCW-92 and TCW-93 are the inbox entries' tickets, for step 8.

**Pass 2, reconciling.** One `PUT` per ticket that differed, 31 in all;
TCW-68 and TCW-76 differed in nothing (their titles' `<KEY> — ` prefix is
not a difference). Each set of values was compared with the plan's item
table before it was sent, and all agree:

- priority: `Highest` on TCW-5, TCW-9, TCW-10, TCW-14, TCW-21, TCW-78 and
  TCW-80; `High` on TCW-22, TCW-23, TCW-26 and TCW-27; `Low` on TCW-42;
  `Lowest` on TCW-48, TCW-81 and TCW-82. The rest keep `Medium`.
- labels: each item's tags, on every ticket but TCW-68, TCW-76 and TCW-91
  (which have none). No ticket had a label its folder lacks.
- effort and complexity: as the item table gives them, on TCW-5, TCW-9,
  TCW-10, TCW-21, TCW-23, TCW-26, TCW-27, TCW-33, TCW-39, TCW-41, TCW-42,
  TCW-78, TCW-81, TCW-82 and TCW-91.
- summaries and parents: none differed; TCW-76's parent TCW-68 was already
  set.
- `Blocks` links, 2: TCW-14 blocks TCW-10, TCW-76 blocks TCW-91. Read back on
  both sides: TCW-10 lists `is blocked by TCW-14` (`inwardIssue` TCW-14),
  TCW-14 lists `blocks TCW-10`; TCW-91 lists `is blocked by TCW-76`, TCW-76
  `blocks TCW-91`.

**Pass 3, moves**, by the global transitions, no comment: 21 moved, 14
already at their status.

- To `Won't Do`: TCW-33, TCW-10, TCW-40, TCW-26, TCW-54, TCW-79 (D4), TCW-80,
  TCW-81, TCW-82, TCW-83, TCW-86, TCW-89.
- To `Done`: TCW-9 (from `In Progress`: the 2.x completion that never reached
  Jira), TCW-78, TCW-88.
- To `Planning`: TCW-50.
- To `To Do`: TCW-84, TCW-85, TCW-87, TCW-90, TCW-91.
- Already there: TCW-5, TCW-14, TCW-21, TCW-22, TCW-23, TCW-27, TCW-39,
  TCW-41, TCW-42, TCW-48, TCW-68 (`To Do`); TCW-76 (`In Progress`); TCW-92,
  TCW-93 (`Triage`).

**Pass 4, closing comments**, 13, the approved text exactly:
`Closed at the migration to TCW 3.0 as discarded` / blank line /
`subject removed by TCW 3.0 (TCW-68)` on TCW-33, TCW-10, TCW-40, TCW-26,
TCW-54, TCW-79, TCW-80, TCW-81, TCW-82, TCW-83, TCW-86 and TCW-89; and
`Closed at the migration to TCW 3.0 as completed` / blank line /
`Delivered by the TCW 3.0 redesign (TCW-68)` on TCW-88.

**Pass 5, `TCW Project` and `TCW Item`.** `TCW Project` `tcw` and `TCW Item`
`tcw/<folder>` (the new folder names below, from each summary as it stands,
computed with 3.0's own `title_words`) set on the 33 items' tickets. D8:
`TCW Project` `tcw` alone on TCW-67, TCW-69, TCW-70, TCW-71, TCW-72, TCW-73,
TCW-74, TCW-75 and TCW-77. TCW-92 and TCW-93 have no item, so neither field
is set on them.

**Pass 6, folders renamed** with `git mv`, old and new names for step 9:

| 2.x folder (after step 4) | 3.0 folder |
| --- | --- |
| `2026-08-18-decide-whether-tcw-work-scaffold-should-stage-its-draft-in-git` | `TCW-33-decide-whether-tcw-work-scaffold-should-stage-its-draft-in-git` |
| `2026-08-31-nothing-verifies-that-a-changed-capability-was-actually-changed` | `TCW-5-nothing-verifies-that-a-changed-capability-was-actually-changed` |
| `2026-09-01-fan-the-backlog-audit-out-across-every-connected-work-root` | `TCW-22-fan-the-backlog-audit-out-across-every-connected-work-root` |
| `2026-09-01-make-tcw-validate-usable-as-a-gate-suppressible-references-and-graded-exit-codes` | `TCW-14-make-tcw-validate-usable-as-a-gate-suppressible-references-and-graded-exit-codes` |
| `2026-09-04-tcw-provision-cannot-be-scoped-and-a-third-hop-config-can-name-a-checkout-directory` | `TCW-23-tcw-provision-cannot-be-scoped-and-a-third-hop-config-can-name-a-checkout-directory` |
| `2026-09-11-run-the-eval-harness-and-act-on-what-it-finds` | `TCW-48-run-the-eval-harness-and-report-what-it-finds` |
| `2026-09-15-add-tcw-work-tracker-create-to-make-and-bind-a-ticket-for-an-existing-item` | `TCW-9-add-tcw-work-tracker-create-to-make-and-bind-a-ticket-for-an-existing-item` |
| `2026-09-15-check-the-tracker-s-workflow-against-the-statuses-mapping-in-tcw-validate` | `TCW-10-check-the-tracker-s-workflow-against-the-statuses-mapping-in-tcw-validate` |
| `2026-09-15-check-the-whole-tracked-tree-ledgers-included-for-removed-skill-names` | `TCW-39-check-the-whole-tracked-tree-ledgers-included-for-removed-skill-names` |
| `2026-09-15-decide-claim-exclusivity-from-a-jira-project-s-workflow-definition` | `TCW-40-decide-claim-exclusivity-from-a-jira-project-s-workflow-definition` |
| `2026-09-15-let-tcw-work-list-sort-by-created-priority-effort-or-title` | `TCW-50-order-and-limit-the-output-of-the-commands-that-list-entities` |
| `2026-09-15-make-pnpm-prettify-check-pass-on-a-clean-checkout` | `TCW-42-make-pnpm-prettify-check-pass-on-a-clean-checkout` |
| `2026-09-15-repair-sentences-references-and-headings-in-the-guides` | `TCW-41-repair-misplaced-sentences-broken-references-and-overloaded-headings-in-the-guides` |
| `2026-09-15-test-as-ci-does-and-warn-on-red-ci-and-unpublished-tags` | `TCW-21-test-the-suite-the-way-ci-runs-it-and-notice-red-ci-runs-unpublished-tags-and-a-shadowing-install` |
| `2026-09-15-write-work-item-properties-to-mapped-tracker-fields` | `TCW-26-write-work-item-properties-to-mapped-tracker-fields` |
| `2026-09-16-add-a-rename-verb-to-tcw-capabilities-and-tcw-taxonomy` | `TCW-27-add-a-rename-verb-to-tcw-capabilities-and-tcw-taxonomy` |
| `2026-09-17-stop-offering-a-version-cut-after-every-completed-work-item` | `TCW-78-stop-offering-a-version-cut-after-every-completed-work-item` |
| `2026-09-19-aggregate-descendant-nodes-taxonomy-and-capabilities-in-tcw-serve` | `TCW-54-aggregate-descendant-nodes-taxonomy-and-capabilities-in-tcw-serve` |
| `2026-09-21-tidy-the-loose-ends-the-combined-v2-5-1-review-found-in-children-and-config-messages` | `TCW-79-tidy-the-loose-ends-the-combined-v2-5-1-review-found-in-children-and-config-messages` |
| `2026-09-21-two-tracker-create-runs-at-once-can-make-two-tickets-for-one-item` | `TCW-80-two-tracker-create-runs-at-once-can-make-two-tickets-for-one-item` |
| `2026-09-22-let-a-leftover-start-record-stop-refusing-a-legitimate-rework` | `TCW-81-let-a-leftover-start-record-stop-refusing-a-legitimate-rework` |
| `2026-09-22-refuse-an-unconfigured-start-before-the-ticket-leaves-triage` | `TCW-82-refuse-an-unconfigured-start-before-the-ticket-leaves-triage` |
| `2026-09-24-give-a-strict-tracker-claim-past-the-active-status-a-way-forward-instead-of-a-transition-list` | `TCW-83-give-a-strict-tracker-claim-past-the-active-status-a-way-forward-instead-of-a-transition-list` |
| `2026-09-24-make-the-test-suite-run-in-minutes-not-half-an-hour` | `TCW-84-make-the-test-suite-run-in-minutes-not-half-an-hour` |
| `2026-09-26-decide-whether-a-capability-path-may-name-a-connected-project-by-an-unambiguous-shorthand` | `TCW-85-decide-whether-a-capability-path-may-name-a-connected-project-by-an-unambiguous-shorthand` |
| `2026-09-30-compare-git-s-store-root-with-a-project-s-node-path-without-depending-on-letter-case` | `TCW-86-compare-git-s-store-root-with-a-project-s-node-path-without-depending-on-letter-case` |
| `2026-09-30-follow-renamed-slugs-in-the-web-app-tracker-verbs-and-capability-drift-check` | `TCW-87-follow-renamed-slugs-in-the-web-app-tracker-verbs-and-capability-drift-check` |
| `2026-09-30-keep-an-item-s-folder-in-one-place-and-its-status-only-in-state-yaml` | `TCW-88-keep-an-item-s-folder-in-one-place-and-its-status-only-in-state-yaml` |
| `2026-09-30-let-the-worktree-merge-back-wait-out-a-store-commit-s-index-lock` | `TCW-89-let-the-worktree-merge-back-wait-out-a-store-commit-s-index-lock` |
| `2026-09-30-run-ci-on-python-3-12-as-well` | `TCW-90-run-ci-on-python-3-12-as-well` |
| `2026-10-01-tcw-68-tcw-3-0-a-simpler-work-lifecycle-with-jira-as-a-first-class-backend` | `TCW-68-tcw-3-0-a-simpler-work-lifecycle-with-jira-as-a-first-class-backend` |
| `2026-10-01-tcw-76-migration-guide-from-2-x-to-3-0-0-and-migrate-the-tcw-repository-first` | `TCW-76-migration-guide-from-2-x-to-3-0-0-and-migrate-the-tcw-repository-first` |
| `2026-10-16-make-the-migration-guide-s-test-check-its-2-x-and-3-0-names-against-the-code` | `TCW-91-make-the-migration-guide-s-test-check-its-2-x-and-3-0-names-against-the-code` |

**Pass 7, `item.yaml` reduced** to its one `ticket:` line in all 33 folders,
and the 19 `tracker.yaml` files removed with `git rm` (`-f`, since each was
staged as part of its folder's rename; its content is in the step 5 commit).

**The rerun (criterion 31).** The whole step was run a second time, every
pass, straight after the first. It made no write: the reads found every
ticket (the 14 items by the key in their folder's name, the 2 inbox tickets by
the search), every field, label, link and status already set, the 13
comments already posted (first line and author), the folders already named
and every `item.yaml` already reduced. The script's call log shows no `POST`
or `PUT` in the rerun other than the searches, and `git status` was the same
before and after. Passes 2 and 3 of the rerun read each item's properties
from its `item.yaml` in the step 5 commit, since pass 7 had already reduced
the files; they agreed with Jira in every case.

**Check:** `find docs/work -name tracker.yaml` printed nothing;
`ls docs/work | grep -vxE 'inbox|TCW-[1-9][0-9]*-[a-z0-9]+(-[a-z0-9]+)*'`
printed nothing (exit 1); the guide's loop over `docs/work/*/` printed
nothing.

Tests: the files that read the guide or this log (as at step 3), those naming
`tracker.yaml` (`tests/test_migration_guide.py`,
`tests/work/jira/test_jira_guards.py`, `tests/work/test_no_2x_names.py`),
those that read under `docs/work` from the repository root
(`tests/test_eval_coverage.py`, `tests/test_git_example.py`,
`tests/test_store_provisioning.py`, `tests/test_validate.py`,
`tests/work/test_cli_installed.py`), `tests/test_documentation_sync_wiring.py`
and the standing guard files: 1586 passed, 29 skipped.
`pytest --collect-only -q` collected 5275 tests.

### Step 7: Move documents

Made on 2026-10-20, through the same script and with the reads of rule 6.

**Requests.** Each request file was decided by the guide's last command in
"Talking to Jira", run as written, on a fresh read of the ticket's
description:

- **Contained, deleted without posting** (21 files): TCW-68's and TCW-76's
  `intake.md` (the 2.x imports, identical to what their import commits
  added), and every request file of the 14 tickets step 6 created (TCW-78 to
  TCW-91), whose descriptions are their requests.
- **TCW-76's `initial-request.md`** was not contained. Its description was
  left as it is, and the request was posted as a comment (D3): the approved
  text, `Request as written in the repository before 3.0` / blank line / the
  file exactly. Then the file was deleted.
- **The 17 tickets of D2** (TCW-5, TCW-9, TCW-10, TCW-14, TCW-21, TCW-22,
  TCW-23, TCW-26, TCW-27, TCW-33, TCW-39, TCW-40, TCW-41, TCW-42, TCW-48,
  TCW-50, TCW-54): none of their 24 files was contained, and each description
  was the 2026-09-20 binding note ("Tracked in the TCW work system as
  `<slug>`. …"). Each description was replaced by the request text (the
  approved text without its first line and the blank line after it,
  `initial-request.md` then `## Original intake` and `intake.md` where both
  exist), and no comment was posted. The same command was run again on each
  file after the write, and every one printed `true`; then the files were
  deleted.

46 request files deleted in all; nothing posted for a request but TCW-76's
comment.

**Stage folders.** With `git mv`: `spec.md` to `spec/spec.md` and `plan.md`
to `plan/plan.md` in TCW-9, TCW-50, TCW-76 and TCW-78; `outcome.md` to
`implement/round-1.md` in TCW-9, TCW-76 (its 2.x implement document) and
TCW-78. No item has `post-mortem.md`.

**Acceptance history.** No item has `rework.md`. The two `refined-outcome.md`
files became comments, the approved text exactly,
`Carried over from TCW 2.x: qa round 1, verdict accepted` / blank line / the
file: on TCW-9 and on TCW-78 (item 33). Both files were deleted, so no item
has a `qa/` folder.

**`capabilities.yaml`.** Two, both mappings with no `added:` key. D9:
TCW-78's line `    - work/customize-the-definition-of-done` (a record
TCW-70 deleted) was removed; its other three entries, and TCW-76's three,
name records that exist. No item has `rollup.md`.

`TCW-76-…/notes-from-tcw-74.md` stays at the item's root, as the Documents
table says for any other file.

**Read back.** After the writes of steps 6 and 7, every ticket the migration
touched was read again and compared with the plan, the expected values taken
from the step 5 commit (`38e6b82b`), the plan's decisions and step 6's first
reads, not from the script's own record: for the 33 items' tickets, summary,
status, priority, labels, effort, complexity, `TCW Project`, `TCW Item` (and
that the folder name is the key and the summary's title words), parent,
`Blocks` links, description (D2: the request; TCW-68 and TCW-76: as read
before; the new tickets: the request) and every comment's author and text;
for TCW-92 and TCW-93, summary, `Triage`, the entry's text as the
description, no fields, labels or comments; for the 9 tickets of D8,
`TCW Project` `tcw`, no `TCW Item`, and every other field as read before.
All 44 agree (`differences: 0`). The comparison was checked by breaking it
(one word of the closing comment's expected text, and one label dropped from
every ticket's labels): it then reported the 12 discarded tickets' comments
and the 30 tickets with labels, and nothing else.

The tickets now: 16 at `To Do` (TCW-5, TCW-14, TCW-21, TCW-22, TCW-23,
TCW-27, TCW-39, TCW-41, TCW-42, TCW-48, TCW-68, TCW-84, TCW-85, TCW-87,
TCW-90, TCW-91), 1 at `Planning` (TCW-50), 1 at `In Progress` (TCW-76), 3 at
`Done` (TCW-9, TCW-78, TCW-88), 12 at `Won't Do`, and 2 at `Triage` (TCW-92,
TCW-93).

**Check:** the `find docs/work -maxdepth 2 \( -name intake.md … \)` command
printed nothing, and the loop over `review/round-*.md` and `qa/round-*.md`
printed nothing (no item has either folder).

Tests: step 6's files, and those naming `outcome.md`, `refined-outcome.md`,
`capabilities.yaml` or `notes-from-tcw-74.md` (`tests/serve/test_files.py`,
`tests/test_capabilities_rm.py`, `tests/test_command_suggestions.py`,
`tests/test_eval_grading.py`, `tests/test_shipped_prompts.py`,
`tests/test_skill_flow.py`, `tests/test_validate_target.py`, the four under
`tests/work/jira/` for drift and validate, `tests/work/test_drift_work.py`,
`tests/work/test_layout.py`, `tests/work/test_review_findings.py`,
`tests/work/test_validate_work.py`), 40 files: 2024 passed, 45 skipped, run
with the files sorted. Given in the order of the lists above, the same files
gave 52 errors, `fixture 'jira_project' not found`, in the tests of
`tests/work/jira/`: pytest does not find that folder's `conftest.py` fixtures
when its files are named on either side of a file from `tests/work/`
(`tests/work/jira/test_jira_guards.py tests/work/test_no_2x_names.py
tests/work/jira/test_jira_drift.py` is enough). The same three files in that
order give the same 2 errors on a copy of the step 5 commit, and pass in any
order that keeps each folder's files together, so it is how the files were
named, not this step. `pytest --collect-only -q` collected 5275 tests.

### Step 8: Convert the inbox

Jira mode. Both entries' tickets were created at step 6 and read back at step
7 with each entry's whole text as the description, at `Triage`:
`2026-10-13-settle-the-jira-live-check-questions-that-need-a-second-account.md`
is TCW-92, and `2026-10-15-tidy-what-tcw-74-s-reviews-left-for-the-eval-harness.md`
is TCW-93. The plan pruned neither. Both files and `inbox/.gitkeep` were
removed with `git rm`, which leaves no `inbox/` folder. `docs/work` now holds
the 33 item folders and nothing else.

Tests: the files that read the guide or this log (as at step 3), the one that
names the inbox (`tests/test_eval_grading.py`, on its own fixtures),
`tests/test_documentation_sync_wiring.py` and the standing guard files: 1364
passed, 6 skipped. `pytest --collect-only -q` collected 5275 tests.

**Check:** `ls docs/work | grep -x inbox` printed nothing (exit 1).

### Step 9: Rewrite live references

**Amendment 5, made before the step** (D10, as approved): the guide's step 9
now says that in Jira mode an old folder name inside text steps 6 and 7
already posted to Jira (the 6 request files of open items named in the
plan's Step 9 entry, now ticket descriptions, and the two acceptance-history
comments) is left as written, since step 9 rewrites only files. Nothing in
Jira was read or changed for this step.

**Old names**, one per line in a file in the session's scratch folder
(`tcw76/step9-oldnames.txt`), 35 in all: the 33 old folder names of step 6's
table (taken from this log's table and compared with the rename list the
step 6 script used: identical; every new name is a folder under `docs/work`),
and the two old slugs of `renames.yaml` from step 4. In Jira mode step 4
renamed no folder.

**Searched**, as the plan's Step 9 entry says:

- open item folders, 17: the 16 at `request` (TCW-5, TCW-14, TCW-21,
  TCW-22, TCW-23, TCW-27, TCW-39, TCW-41, TCW-42, TCW-48, TCW-68, TCW-84,
  TCW-85, TCW-87, TCW-90, TCW-91) and TCW-50 at `plan`. TCW-76's folder is
  skipped. After step 7 only TCW-50's holds documents (`spec/spec.md`,
  `plan/plan.md`); the others hold only `item.yaml`;
- live documents: `git ls-files` without `docs/work/`, `docs/changelogs/`,
  `docs/release-notes/`, `docs/plan/`, `docs/superpowers/`, the
  `docs/migration-guide-*` files, this log and `tests/fixtures/`: 704 files,
  `tcw-config.yaml` among them.

**Found and rewritten**, 1 line: `TCW-50-…/plan/plan.md:432`,
`tcw work path 2026-09-15-let-tcw-work-list-sort-by-created-priority-effort-or-title`
became `tcw work path TCW-50-order-and-limit-the-output-of-the-commands-that-list-entities`.
No live document names an old folder or slug, and no `tcw://work/` link in
either set names one. No relative link between an open item's documents
names a document by its 2.x path; TCW-50's documents mention `spec.md`,
`plan.md`, `outcome.md` and `initial-request.md` in backquotes as names, not
as links, so the guide's link rule does not reach them, and they are left as
written.

**Check:** `grep -rnF -f tcw76/step9-oldnames.txt <the 17 open item folders>`
printed nothing (exit 1); the same search over the 704 live documents printed
nothing (exit 1); and
`grep -rnE '\]\((\./)?(intake|initial-request|spec|plan|outcome|refined-outcome|rework|post-mortem)\.md' <the 17 open item folders>`
printed nothing (exit 1).

Tests: the files that read the guide or this log, or name TCW-50's folder
(those of step 3, and `tests/work/jira/test_jira_validate_remote.py`), those
that read under `docs/work` from the repository root (as at step 6),
`tests/test_documentation_sync_wiring.py` and the standing guard files, 25
files run in sorted order: 1544 passed, 29 skipped.
`pytest --collect-only -q` collected 5275 tests.

### Step 10: Review the project's own files

As the approved plan's "The project's own files" and "Capability records"
say:

- **`AGENTS.md`** (`CLAUDE.md` is a symbolic link to it, so it was edited
  once). "Work Planning and Implementation" rewritten for 3.0 (spec Design 7
  and 8.6): it says the items are kept in Jira; `tcw work stage prompt` before
  a stage, `tcw work advance` after it, and `tcw work advance --dry-run`
  instead of `tcw work stage gate`; the bindings table gains `review`
  (`docs/lifecycle/review.md`) and `completed` (`tcw validate`), and its
  `spec` row names the two outlines; a paragraph names the pull text and the
  commit hook; a new paragraph says an item is advanced to `implement` before
  the first change to code (what TCW-75 removed from `implementation.md`); the
  exception now says to move tickets by hand in Jira and edit item folders
  directly while `tcw/` is being changed, and that `tcw validate --remote`
  reports a hand move that skips a stage's document; the GitHub-issue
  paragraph no longer names `dod.yaml` or `refined-outcome.md`, and records
  the deferral in the item's qa findings, a comment on its ticket. Versioning:
  `upcoming/<work-item-slug>.md` became `upcoming/<work-item-folder>.md`. The
  worktree section and "Measuring the skill layer" are untouched
  (`notes-from-tcw-74.md` items 1 and 3).
- **`.gitignore`**: the comment `# Discarded work: …`, `docs/work/discarded/*`
  and `!docs/work/discarded/.gitkeep` removed; `/tcw-config.local.yaml` added
  under a comment line.
- **Capability records**: the `Planning doc:` line removed from the 13
  records the plan names (no other line changed); no record has `Tracker:`.
- **`tests/doc_allowance.py`**: `tcw work stage gate` removed from
  `REMOVED_COMMANDS` (spec amendment 23), which is now an empty tuple, and its
  comments say so. **Not foreseen by the plan:**
  `tests/test_docs_describe_3_0.py::test_the_allowance_check_sees_a_removed_command`
  read that entry from the list, so it failed once the list was empty
  (`assert 'tcw work stage gate' in []`). It now gives the check the entry
  with `monkeypatch`, as its neighbour
  `test_the_allowance_check_sees_a_removed_flag_and_a_refused_key` already
  does for the other lists. Mutation: `allowance_names` made to skip
  `REMOVED_COMMANDS` → the test fails with the same assertion; restored → it
  passes. Task B18 deletes the allowance and this test with it.
- **Already clean**, as the plan expected: `scripts/require_artifact.py`,
  both templates, `docs/lifecycle/review.md`, `docs/procedures/create-work.md`.

**Other text that relies on removed behavior**, pointed out for the owner
(not changed, since the plan does not cover it; step 12 proposes it):
`AGENTS.md:5`, "**Live status & pending work:** `tcw work` — this repo
dogfoods its own work component (`docs/work/`)": in 3.0 a bare `tcw work`
prints a usage error, and in Jira mode the board is the Jira project, listed
by `tcw work list`.

**Check**, over the plan's `<hook files>`:
`grep -nE 'TCW_(STATUS|TRANSITION|NODE_ROOT|RESOLUTION)\b' <hook files>`
printed nothing (exit 1);
`grep -rlnE '^(Planning doc|Tracker):' docs/capabilities` printed nothing
(exit 1); `grep -nE 'docs/work/(completed|discarded)' .gitignore` printed
nothing (exit 1); `grep -cx '/tcw-config.local.yaml' .gitignore` printed `1`.
A wider search of the hook files for `state.yaml`, `dod.yaml`, `Definition of
Done`, `refined-outcome`, `stage gate`, `--worktree`, the 2.x verbs, status
folders, `claim`, `retain` and `auto-commit` found only the ordinary word
"claim" (the templates' "A claim recalled …", `AGENTS.md`'s "what it claims
to observe").

Tests: step 9's files; those naming `doc_allowance`, `AGENTS.md`,
`.gitignore` or `Planning doc` (`tests/config/test_personal_validate_init.py`,
`tests/test_capabilities.py`, `tests/test_config_edit_writers.py`,
`tests/test_eval_files_changed.py`, `tests/test_smoke.py`,
`tests/test_worktree_sibling_nodes.py`, `tests/work/test_drift_work.py`,
`tests/work/test_init_provision.py`, `tests/work/test_open.py`, beside those
already in step 9's list); and the three code tests of Task A1
(`tests/work/test_removed_commands.py`, `tests/work/test_no_2x_names.py`,
`tests/work/test_cli_config.py`), 36 files in sorted order: 1773 passed, 44
skipped (before the test fix: 1 failed, the one above).
`pytest --collect-only -q` collected 5275 tests.

### Step 11: Validate

**3.0 on `PATH`, and the plugin.** Not done as the guide words it, by the
plan's rules: 3.0.0 is not released yet, so there is no
`pipx install 'tcw-cli>=3,<4'` to run and no 3.0 plugin release to update
to, and the epic's rule is a private virtual environment rather than a
re-pointed shared install. Every `tcw` of this step, and the hooks it runs,
ran with the private environment `tcw76/venv` first on `PATH`
(`which tcw` printed its `bin/tcw`; `import tcw` resolved to this worktree's
`tcw/__init__.py`). The shared install stays 2.8.3 and the plugins stay as
they are until 3.0.0 is published (Task B24). This is not a fault in the
guide, which is written for a released 3.0: it is the epic's own ordering
(deviation f).

Jira credentials: `TCW_JIRA_EMAIL` and `TCW_JIRA_API_KEY` were already set in
the session's environment, and `source ~/.bashrc` was run first as well.
`git status --porcelain` printed nothing before and after each run.

**`tcw validate; echo "exit $?"`** printed:

```text
0 errors, 0 warnings, 0 unresolved
exit 0
```

**`tcw validate --remote; echo "exit $?"`** printed:

```text
tcw: the credentials and Jira project TCW are readable
tcw: moves read from the workflow definition had their screen fields left unchecked; only a sample ticket shows them
tcw: 33 item folders checked against their tickets
tcw: the model checks ran over 33 items
0 errors, 1 warning, 0 unresolved
warning: work.jira: unchecked: the Sub-task edit screen: no Sub-task ticket in TCW to sample
exit 0
```

Each line read:

- **Errors:** none in either run.
- **`unchecked:` warning, listed for the owner:** the `Sub-task` edit screen,
  the one step 3 listed. Every type uses one screen for create and edit
  (step 2, item 5), step 2 read the `Sub-task` create screen with every field
  TCW needs, and TCW has no `Sub-task` ticket to read an edit screen on. Kept,
  with that reason.
- **The note on moves' screen fields** is the one step 3 listed. As step 3
  said, it was read again on real items:
  `GET /rest/api/3/issue/<key>/transitions?expand=transitions.fields` on one
  ticket at each status in use, TCW-92 (`Triage`), TCW-5 and TCW-68 (`To Do`),
  TCW-50 (`Planning`), TCW-76 (`In Progress`), TCW-9 (`Done`) and TCW-33
  (`Won't Do`): each lists 9 transitions, one into each of the nine statuses,
  and none has a field (all `HTTP 200`).
- **The board against Jira:** 33 item folders checked against their tickets,
  and the model checks ran over 33 items, with no finding.
- **Other findings:** none.

**Stages.** `tcw work list --all --json` (exit 0) lists 33 items. Each one's
`stage` was compared, by its new folder name, with the stage the approved
plan's item table gives its 2.x folder (D4 applied to item 17), through step
6's table of old and new names: 0 differences. 16 at `request` (TCW-5,
TCW-14, TCW-21, TCW-22, TCW-23, TCW-27, TCW-39, TCW-41, TCW-42, TCW-48,
TCW-68, TCW-84, TCW-85, TCW-87, TCW-90, TCW-91), 1 at `plan` (TCW-50), 1 at
`implement` (TCW-76), 3 at `completed` (TCW-9, TCW-78, TCW-88) and 12 at
`discarded` (TCW-10, TCW-26, TCW-33, TCW-40, TCW-54, TCW-79, TCW-80, TCW-81,
TCW-82, TCW-83, TCW-86, TCW-89).

**Check:** `tcw validate; echo "exit $?"` ended with `exit 0`, and
`tcw validate --remote; echo "exit $?"` ended with `exit 0`, as above.

Tests: step 11 changed only this log. The files that read the guide or this
log (as at step 3), `tests/test_documentation_sync_wiring.py` and the
standing guard files, 19 files in sorted order: 1282 passed, 9 skipped.
`pytest --collect-only -q` collected 5275 tests.

### Step 12: Revisit agent instructions and memories

**Amendment 6, made during the step** (above): the step's reading rule for
files someone else installed. `tests/test_migration_guide.py` and the other
files that read the guide pass after it (923 passed).

Run from this worktree on 2026-10-20, read only outside it: nothing outside
the migration worktree was changed. The guide's snippet built 23 places
(the bound files of the plan's `<hook files>` added by hand):

- in the repository: `CLAUDE.md`, `AGENTS.md`, `.claude/settings.json` (the
  only tracked file under `.claude/`; there is no `.codex/` or
  `.agents/skills/`), and `docs/lifecycle/abstraction.md`, `harness.md`,
  `implementation.md`, `review.md`, `docs/lifecycle/templates/spec.md`,
  `spec-bug.md`, `docs/procedures/create-work.md`,
  `scripts/require_artifact.py`,
  `docs/guide/examples/commit-item-after-move.sh`;
- the primary checkout's one untracked file under `.claude` and `.codex`:
  `/Users/brian/Projects/TCW/.claude/settings.local.json`;
- the owner's files: `~/.claude/CLAUDE.md`, `~/.codex/AGENTS.md`,
  `~/.claude/skills`, `~/.claude/agents`, `~/.codex/skills`,
  `~/.agents/skills`, `~/.claude/settings.json`, `~/.codex/rules`
  (`~/.claude/commands` and `~/.codex/prompts` do not exist);
- memories: `~/.codex/memories`, and
  `~/.claude/projects/-Users-brian-Projects-TCW/memory`, the only Claude Code
  memory folder whose session records start in one of the three checkouts
  (the primary checkout and this worktree; `.worktrees/tcw-3-0-epic` has no
  session of its own).

The files-to-read search printed 145 files: 99 installed by someone else
(`~/.claude/skills/synced/…`, `~/.codex/skills/.system/…`,
`~/.agents/skills/pi/…`), none naming `tcw` or `TCW`, read as amendment 6
says and not about TCW; and 46 read in full.

The proposal, with the passages and the proposed text, is in a private file
in the session's scratch folder (`tcw76/step12-proposal.md`), since most of
it quotes files outside the repository. It goes to the owner as the step's
one question. **Nothing has been changed yet.**

Tests: the guide and this log changed. The files that read them (as at step
3), `tests/test_documentation_sync_wiring.py` and the standing guard files,
19 files in sorted order: 1282 passed, 9 skipped. `pytest --collect-only -q`
collected 5275 tests. The step's check runs after the owner's answer is
applied.

## Agent instructions

Status: **answered.** Proposed on 2026-10-20; the owner answered the same
day, in chat: "as recommended". Every finding below was applied as its
recommendation says, and nothing else was changed. One line per finding: the
file and line as found, the decision, and what was done. For a file outside
the repository, or one git does not track, only its path and line numbers are
given (rule 7); its passages and the approved text are in the private
proposal (`tcw76/step12-proposal.md` in the session's scratch folder).

In the repository:

- A1. `AGENTS.md:5` (also `CLAUDE.md:5`, the same file), "**Live status &
  pending work:** `tcw work` — this repo dogfoods its own work component
  (`docs/work/`)": **rewrite**, approved. Done: the line now names
  `tcw work list`, the Jira project `TCW`, and each item's documents under
  `docs/work/`. The new text matches no `NAMES` pattern.
- A2. `AGENTS.md`, every other section: **keep**, approved. Unchanged.
- A3. `.claude/settings.json`: **keep**, approved. Unchanged.
- A4. The bound files: **keep**, approved. Unchanged. The proposal named
  only the templates' `spec/spec.md` line as their `NAMES` match; the search
  after the answer also prints `TCW_SLUG` in
  `docs/guide/examples/commit-item-after-move.sh` and
  `scripts/require_artifact.py`. Both use it as 3.0 defines it (the full
  slug, put in a commit message or passed to `tcw work path` as it is; the
  guide's Hook variables table), so the same keep covers them, and they are
  in the block below.

The primary checkout's untracked file
(`/Users/brian/Projects/TCW/.claude/settings.local.json`):

- B1. Its `tcw` allow entries: **keep**, approved. Unchanged.
- B2. Lines 72, 74, 76, 78, 80, 101: **delete**, approved. Done by the owner,
  who removed the six entries themselves.
- B3. Line 111: **delete at Task B24**, approved. Unchanged until then.
- B4. Lines 90, 91, 95, 96, 98, 99, 110: no finding. Unchanged.

The owner's own files:

- C1. `~/.claude/CLAUDE.md:43`: **keep** until the `llama` project migrates
  to 3.0, approved. Unchanged.
- C2. `~/.claude/CLAUDE.md:27`: **keep**, approved. Unchanged.
- C3. `~/.claude/skills/autonomous-work/SKILL.md:3, 8, 14, 49, 50, 52, 53,
  54, 74`: **delete**, approved. Done by moving the folder, not deleting it,
  to `~/.claude/deprecated-skills/autonomous-work`, where Claude Code no
  longer loads it; deleting it for good is offered to the owner at Task B24.
- C4. `~/.claude/settings.json:81`: **keep**, approved. Unchanged.
- C5. `~/.claude/settings.json:314-317, 339, 340, 373, 374`: **keep**,
  approved. Unchanged.
- C6. `~/.codex/rules/default.rules:20, 21, 23, 26, 58, 62, 73, 74`:
  **delete**, approved. Done: the eight lines removed (a backup is in the
  scratch folder). Lines 3, 38, 41, 42, 57, 59: **keep**, approved;
  unchanged, now lines 3, 34, 37, 38, 53, 54 after the deletions. Lines 44
  and 47-52 as they now stand match `NAMES` only through `review/` inside a
  temporary folder's name that has nothing to do with TCW: no finding,
  unchanged, in the private expected file.
- C7. `~/.claude/agents/adversarial-code-reviewer.md:187`,
  `~/.claude/agents/adversarial-spec-reviewer.md:74, 88, 112`: **keep**,
  approved. Unchanged.
- C8. `~/.codex/AGENTS.md`: no finding. Unchanged.
- `~/.claude/skills/synced/…/google-workspace/references/sheets.md:149`, a
  skill someone else installed (amendment 6): no finding, unchanged, in the
  private expected file.

Claude Code memories (`~/.claude/projects/-Users-brian-Projects-TCW/memory/`):

- D1. `tcw-can-be-driven-by-manual-edits.md:3, 11, 15`, `MEMORY.md:7`:
  **rewrite**, approved. Done: the description, both paragraphs and the
  index line's hook rewritten as proposed.
- D2. `the-item-is-truth-always-applies.md`, `MEMORY.md:13`: **delete**,
  approved. Done: the file and its index line deleted.
- D3. `triage-writes-the-request-read-it-first.md:3, 11, 15`,
  `MEMORY.md:14`: **rewrite**, approved. Done. Line 11's new text still
  matches `NAMES` (it names the 2.x file the migration moved), so it is in
  the private expected file.
- D4. `fold-small-follow-ups-into-the-current-item.md:3, 19, 20`,
  `MEMORY.md:9`: **rewrite**, approved. Done.
- D5. `venv-instead-of-repointing-the-shared-tcw-install.md:11-15`:
  **rewrite**, approved. Done: the opening paragraph only, as proposed.
- D6. `source-bashrc-for-jira-credentials.md:13, 15-18`: **rewrite**,
  approved. Done.
- D7. `no-backward-compat-for-old-tcw-reading-new-configs.md:16-18, 24-27`:
  **rewrite**, approved. Done: the 2.x examples replaced and the dead link
  dropped. Line 12, the owner's dated quote, is kept as history and is in
  the private expected file.
- D8. `skills-restructure-resume-point.md`, `MEMORY.md:6`: **delete**,
  approved. Done: the file and its index line deleted.
- D9. `tcw-release-is-ci-published-on-tag-push.md`,
  `push-releases-without-asking.md`,
  `ci-runs-bare-pytest-not-python-m-pytest.md`: **keep**, approved.
  Unchanged.
- D10. `skip-full-suite-during-tcw-3-0-epic.md`,
  `tcw-3-0-epic-adversarial-review-is-approval.md`,
  `tcw-3-0-epic-resume-point.md`, `MEMORY.md:15-17`: **delete at Task B24**,
  approved; until then their lines that match `NAMES` are in the private
  expected file. `tcw-3-0-epic-resume-point.md:23-29, 37-41`: **rewrite
  now**, approved. Done: the file rewritten to the current state, its 2.x
  closing route removed.
- D11. `MEMORY.md`: each line follows its file's decision. Done, hooks
  updated.

Codex memories (`~/.codex/memories/`):

- E1. `memory_summary.md:23`: **rewrite**, approved. Done.
- E2. `memory_summary.md:21`, `MEMORY.md:142-144`: **keep**, approved.
  Unchanged.
- E3. `MEMORY.md:57-96, 239-261, 312-338`, `memory_summary.md:49-53,
  80-85`, `raw_memories.md`, and three files under `rollout_summaries/`:
  **keep** as history, approved. Unchanged.
- E4. The other files under `rollout_summaries/` and the rest of
  `raw_memories.md`: **keep**, approved. Unchanged.

**Amendment 7, made during the step.** The step's check gave a different
result depending on which `grep` ran. `CLAUDE.md` here is a symbolic link to
`AGENTS.md`: GNU grep's `-r` reads a link named on its command line, and
macOS's `/usr/bin/grep -r` skips it, so the same search printed each
`AGENTS.md` line once more, as `CLAUDE.md:…`, under one and not the other,
and no `expected-names` block could pass under both. The guide's list of
places now replaces each place that is a link with the file it points to, or
leaves it out when that file is listed already. Here that drops `CLAUDE.md`,
and the search prints the same lines under both greps (checked). A link to a
file outside the list, which macOS's grep would have skipped without a word,
is now searched as well.

The block below holds the lines of tracked files that the check's search
still prints, each read and judged above (A2 and A4). The other lines it
prints are in files outside the repository, and are in the private file the
guide names, `~/.tcw-3.0-migration-expected-names.txt`.

```expected-names
AGENTS.md:| `spec`      | [`docs/lifecycle/abstraction.md`](docs/lifecycle/abstraction.md) · [`docs/lifecycle/harness.md`](docs/lifecycle/harness.md) · the spec outline, [`spec.md`](docs/lifecycle/templates/spec.md) or, for an item tagged `bug`, [`spec-bug.md`](docs/lifecycle/templates/spec-bug.md) |
docs/guide/examples/commit-item-after-move.sh:git commit --quiet -m "Move $TCW_SLUG to $TCW_STAGE" -- .
docs/lifecycle/templates/spec-bug.md:_The outline for this item's spec: the file `tcw work path <slug> spec` names (`spec/spec.md`)._
docs/lifecycle/templates/spec.md:_The outline for this item's spec: the file `tcw work path <slug> spec` names (`spec/spec.md`)._
scripts/require_artifact.py:        print("require_artifact: TCW_SLUG is not set; this runs as a tcw "
scripts/require_artifact.py:    slug = os.environ.get("TCW_SLUG")
scripts/require_artifact.py:Fails closed. An unset `TCW_SLUG`, a `tcw` that cannot be run, or a `tcw`
scripts/require_artifact.py:It asks `tcw work path "$TCW_SLUG" <stage>` where the document lives rather
scripts/require_artifact.py:`docs/work/<folder>/spec/spec.md` would hardcode one store's layout.
```

**Check**, run as the guide gives it from this worktree on 2026-10-20, with
the list of places built afresh by the amended snippet (22 places: the 23
of the survey less `CLAUDE.md`) and the bound files added by hand:
`grep -c '^## Agent instructions'` printed `1`, and the `diff` printed
nothing. The search printed 70 lines: the 9 in the block above and 61 in the
private file. Run under both macOS's `/usr/bin/grep` and ugrep, it printed
the same 70 lines.

No configuration-bound file changed at this step (`AGENTS.md` and the guide
are not bound), so `tcw validate` was not required.

Tests: `AGENTS.md`, the guide and this log changed. The test files that read
any of them, 10 files in sorted order (`grep -rl` over `tests`, less the
helper `tests/doc_allowance.py` and a fixture): 930 passed.
`pytest --collect-only -q` collected 5275 tests.

## After the migration: Tasks B17 to B20

### Task B17: `tests/test_repo_lifecycle.py` for 3.0

New file, 8 tests, written against the 3.0 parser (spec Design 7):

- `tcw-config.yaml` loads through `tcw.config.load_config` with
  `TCW_NO_PERSONAL_CONFIG=1` and no problems, and its `work.jira` block
  parses through `tcw.work.jira.config.parse_jira_config` with none;
- every `file:` bound to a stage or a procedure exists and is not empty;
- every `command:` that runs a script through `sh` or `python` names a script
  that exists (and the two scripts, `scripts/require_artifact.py` and
  `docs/guide/examples/commit-item-after-move.sh`, are among them). The one
  other command, `tcw validate` on `completed`, names a program found on
  `PATH` and no file, so it has nothing to check;
- `plan` binds no spec template, and some stage does;
- both templates carry the seven sections `tcw/work/prompts/spec.md` asks for
  (Capability changes, Problem, Goals, Non-goals, Design, Acceptance criteria,
  Risks);
- the documentation entries are exactly the seven of Design 6.4, by path and
  trigger: `Jira-Change` present, no `Tracker-Change`, the upcoming entries at
  `upcoming/<folder>.md` and none at `<slug>`, no description naming
  `dod.yaml`, and the `Guide-Topic-Change` description naming `Jira-Change`.

Mutations, each restored with `git checkout` afterwards:

- `## Non-goals` renamed `## Out of scope` in `docs/lifecycle/templates/spec.md`:
  1 failed, `test_a_template_carries_the_seven_spec_sections[…spec.md]`,
  "lacks ['Non-goals']". (Plan's mutation.)
- `trigger: Jira-Change` put back to `trigger: Tracker-Change`: 1 failed,
  `test_the_documentation_entries_are_those_of_design_6_4`, on the set of
  path and trigger pairs. (Plan's mutation.)
- `implement`'s second `pre` pointed at `scripts/require_artifactX.py`: 1
  failed, `test_every_hook_script_exists`, naming the missing script.
- `docs/lifecycle/templates/spec.md` added to `plan`'s prompt: 1 failed,
  `test_plan_binds_no_spec_template`.
- an unknown key `projekt` added to `work.jira`: 2 failed, the two
  no-problems tests.

Tests: `tests/test_repo_lifecycle.py`, `tests/test_documentation_sync_wiring.py`
and the standing guard files, 12 files in sorted order: 803 passed, 9 skipped.
`pytest --collect-only -q` collected 5283 tests.

### Task B18: the documentation allowance emptied and deleted

Every list in `tests/doc_allowance.py` was already empty (the last entries
went at step 10 and with `AGENTS.md`'s rewrite), so the module and its guard
were deleted:

- **Deleted** `tests/doc_allowance.py` and `tests/test_doc_allowance.py`.
- **`tests/test_documented_cli_surface.py`:** the import, the
  removed-flag exception in `_check`, `_allowed` and its use, and the
  refused-key exception in `test_documents_name_no_refused_key` removed. A
  documented removed command, flag or refused key now fails with no way
  through.
- **`tests/test_shipped_text.py`:** the import, `_names`, `_flag_named`,
  `ENTRIES` and the three allowance-only tests
  (`test_no_allowance_entry_is_named_only_by_owned_text`, `…_value_…`,
  `…_flag_…`) removed, with the imports only they used.
- **`tests/test_docs_describe_3_0.py`** (step 10 had added `monkeypatch`
  tests here): the import, `allowance_names`,
  `test_no_owned_document_names_an_allowance_entry` and both
  `test_the_allowance_check_sees_…` tests removed; the module's docstring no
  longer lists the allowance-name check, and says TCW-75's criterion 4 went
  with the allowance.
- **`tests/work/removed_2x.py`:** its docstring named the module's path; it
  now describes the allowance without naming it. Its list,
  `REMOVED_2X_COMMANDS`, still holds 21 entries and is what the three code
  tests of Task A1 read.
- **`tests/test_migration_guide.py`:** new
  `test_the_documentation_allowance_is_gone`: neither file exists, and no
  file under `tests/` names the module (the test spells the name in two
  parts so it does not name it itself).

Collected tests went from 5283 to 5253: 30 removed (7 in
`test_doc_allowance.py`, 21 in `test_docs_describe_3_0.py`, 3 parametrized
on empty lists in `test_shipped_text.py`) and 1 added.

Mutations, each restored afterwards:

- `tests/doc_allowance.py` recreated from `HEAD`: the new test failed on
  the file existing. (Plan's mutation.)
- a comment naming `tests/doc_allowance.py` appended to
  `tests/work/removed_2x.py`: the new test failed, naming that file.
- ``Run `tcw work stage gate spec <slug>`.`` appended to `docs/guide/work.md`:
  `test_documented_verbs_and_flags_exist[docs/guide/work.md]` failed, "no
  such verb: tcw work stage gate", which the allowance's command list would
  once have let through.
- ``Set `work.retain`.`` appended to `docs/guide/work.md`:
  `test_documents_name_no_refused_key[docs/guide/work.md]` failed, "names
  configuration keys TCW 3.0 refuses: work.retain".

Tests: the four edited test files, the three code tests of Task A1, the new
`tests/test_repo_lifecycle.py` and the standing guard files, 15 files in
sorted order: 1229 passed. `pytest --collect-only -q` collected 5253 tests.

### Task B19: this item's release notes and changelog

Two entry files, named by this item's folder name after step 6,
`TCW-76-migration-guide-from-2-x-to-3-0-0-and-migrate-the-tcw-repository-first.md`,
under `docs/release-notes/upcoming/` and `docs/changelogs/upcoming/`, each
starting at its first `##` with no text before it (criterion 29):

- release notes: `## Upgrading`, how a 2.8 project moves to 3.0.0 with a
  link to the guide (`../migration-guide-2.8-to-3.0.0.md`), and that TCW's
  own repository was moved first by following it;
- changelog: `## Added` (the guide, `docs/lifecycle/review.md`, this log,
  and the new tests), `## Changed` (TCW's own configuration and board on
  3.0, `AGENTS.md`, `.gitignore` and the `Planning doc:` lines,
  `scripts/require_artifact.py`, the spec templates and `create-work.md`)
  and `## Removed` (the documentation allowance).

Mutation: a line of text put before the changelog entry's first `##`:
`test_an_entry_starts_at_a_level_two_heading[changelogs/TCW-76-…]` failed;
restored from a copy.

Tests: `tests/test_upcoming_entries.py`, `tests/test_cut_version.py`
(including `test_the_cut_puts_the_introduction_first`, which combines every
release-notes entry), `tests/test_documentation_config.py`,
`tests/test_documented_cli_surface.py` and `tests/test_shipped_text.py` (which
read every Markdown file) and the standing guard files, 12 files in sorted
order: 860 passed, 1 skipped. `pytest --collect-only -q` collected 5255
tests.
