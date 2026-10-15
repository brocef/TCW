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

## 2.x behavior that had no key

_Written in Task A5._

## The steps

_Written in Task A5._

## Talking to Jira

_Written in Task A5._

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
| `completed/` | `completed` |
| `discarded/` (tracked, or ignored by `.gitignore`) | `discarded`; the 2.x resolution (`wontfix`, `duplicate` or `superseded`) and any reason become a comment |

- **The rule picks a stage whose documents are already written.** A later
  stage would make `tcw validate` warn that the item is ahead of its documents.
  When the stage the rule picks is turned off in the new configuration, the
  item takes the next flow stage that is on.
- **Discarded folders ignored by `.gitignore`** exist only on the machine
  that discarded them. Step 0 finds them and the plan lists them. The user
  chooses which to keep; a kept one becomes a tracked `discarded` item, since
  3.0 has no folder left to ignore, and the `.gitignore` rule is removed at
  step 10. The rest stay untracked on that machine and are not migrated.
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
| `blocked_by` | `blocked-by`, a list of full slugs using the folders' final names. A blocker written as free text is dropped and listed, since a 3.0 blocker is an item. Jira: a `Blocks` link; a link to a ticket that has no item shows as `untracked` in `tcw work show` |
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
| `graveyard.yaml` | deleted at step 4; git history keeps it. Items it records stay deleted, and their old slugs stop resolving |
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
| `work.lifecycle.stages.inbox`, `.request`, `.spec`, `.plan`, `.implement` | the same stage under `work.stages`. A stage's `pre` and `prompt` keep their names, and a stage now also takes `post`. A bare list given as the stage (the oldest shape) becomes its `prompt`, and a `command` entry in that list becomes `generate`. An empty `prompt` list, an error in 2.x, now means "print nothing" |
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
applies as before. **Any other shape** (an earlier entry with `not_tags`, or
with both keys) needs an "or" to negate, which one `when:` cannot say: list it
in the plan with a proposed rewrite (for example, adding a tag to the affected
items), and the user chooses. A `builtin` fallback entry is dropped, since
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
| `{{tcw:body}}…{{/tcw:body}}` in prompt text | `{{tcw:request}}…{{/tcw:request}}`. 3.0 leaves `{{tcw:body}}` as written, so an unconverted pair is printed as it stands rather than refused |

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
| a `.gitignore` rule naming a status folder, such as `docs/work/discarded/*` | removed. Add the line `/tcw-config.local.yaml`, as `tcw init` writes for a new project, so personal configuration is never committed |
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

- **Create it.** The agent creates the ticket in the Jira project, with the
  item's `title` as its summary, its request as the description
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

- An `intake.md` whose text the ticket's description already contains,
  ignoring an `Imported on … from [KEY]` line and white space, is deleted
  without asking.
- Other request text goes into the description when the description is
  empty. When it has text, the request is posted as a comment whose first
  line is `Request as written in the repository before 3.0`, and the
  description is left as it is: Jira owns it, and someone outside engineering
  may have written it. The plan offers "replace" or "append" instead, per
  ticket.
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
