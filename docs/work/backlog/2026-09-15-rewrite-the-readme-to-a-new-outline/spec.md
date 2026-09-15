# Spec: Rewrite the README to a new outline

## Capability changes

None. This is a documentation change: no capability is added, removed, or
changes status. The ledger entries the README describes, such as
`plugin/install-as-a-plugin`, `plugin/bootstrap-the-cli`, `cli/install-from-pypi`
and the `skills/*` entries, stay `Supported` and unchanged. No taxonomy
Vocabulary or Feature entry is touched.

## Problem

`README.md` (660 lines) is organized as a pitch followed by reference material,
and the requester considers that structure bad. Readers cannot find the three
axes explained one at a time: taxonomy and capabilities have no section of their
own; the work lifecycle is never shown; Jira takes up about 200 lines
(`README.md:359-561`) that sit apart from the lifecycle they change; and skills
are listed in one block (`README.md:582-630`) with no link to the axis each one
drives.

The current text also contradicts itself and the code in ways a rewrite must
not carry forward:

- `README.md:175-177` and `README.md:650-653` say tracker adapters and tracker
  synchronization are "not built", while `README.md:359-561` documents them as
  shipped (the `tcw work tracker` group is defined at `tcw/work/cli.py:2619-2620`).
- `docs/guide/work.md:605-823` ("Working from an external tracker") is out of
  date:
    - It says `link` claims the ticket (`docs/guide/work.md:615`,
      `docs/guide/work.md:771-772`). `_tracker_link` writes only the binding and
      makes "no transition, no assignee change" (`tcw/work/cli.py:2101-2109`), and
      its help says "In the tracker: nothing" (`tcw/work/cli.py:2686-2691`).
    - It says "No other command gains a network dependency"
      (`docs/guide/work.md:607-609`), but `start`, `submit`, `rework` and
      `complete` now reach Jira for a bound item (`README.md:473-490`).
    - It says "Everything but `timeout-seconds` is required"
      (`docs/guide/work.md:635`), but `statuses`, `comments`, `link` and `strict`
      are optional (`README.md:386`, `:509`, `:527`).
    - It never mentions `statuses`, `tracker sync`, comments or strict mode.
- Nothing flags these guides for update. `tcw-config.yaml:15-39` declares
  documentation entries for `README.md`, the release notes, the changelog and
  skill files, and none for `docs/guide/`. That is how the tracker section
  drifted.

## Goals

1. `README.md` follows the requester's outline as amended by the decisions in
   `initial-request.md`, heading for heading, in order.
2. Each axis is explained on its own: what it is, how it relates to the others,
   and how to use it through skills and through the CLI.
3. The work lifecycle is shown as a diagram of stages and statuses, and Jira is
   described in terms of where it attaches to that lifecycle, with worked
   examples.
4. There is one current, complete, user-facing Jira guide, `docs/guide/jira.md`,
   with a documentation entry that flags it when tracker behavior changes, and
   no out-of-date copy remains in `docs/guide/work.md`.
5. Every command, flag, default and behavior the new README states is true of
   the code at the time of writing.
6. `skill-cefailures` is no longer enabled in this repository (request
   decision 8).

## Non-goals

- Keeping any current README section the outline does not name ("What it looks
  like", "Why many repositories…", "What it deliberately refuses", "What
  adopting it costs", "Who it's for", "Storage abstraction", "Quickstart",
  "Status"). They are removed, not moved to another document (request decision 1).
- Changing `docs/guide/web-viewer.md` (request decision 7). This also leaves
  items 3 and 4 of the inbox entry
  `2026-09-11-prose-defects-the-heading-sweep-found` (a broken anchor at
  `web-viewer.md:47`, and contributor formatting commands inside that guide)
  for that entry to fix.
- Rewriting or restructuring any other guide beyond what Design § 3 names.
- Changing TCW's code, tests, CLI, skills or plugin manifests. The skill
  reference files `skills/tcw-configure/references/tracker.md` and
  `skills/tcw-work/references/commands.md` stay the agent-facing tracker
  references; `docs/guide/jira.md` is the user-facing one.
- Removing `skill-cefailures` from historical records: `docs/plan/`,
  `docs/superpowers/`, released changelogs, and
  `tests/test_documentation_sync_wiring.py`, which is the guard against it
  coming back.
- Making the README render well on PyPI. `pyproject.toml:9` publishes it as the
  package description; see Risks.

## Design

### 1. Heading structure

The title is the one `#` heading. Every other heading takes its level from its
depth in the outline: top-level outline items are `##`, their children `###`,
and their children `####`. Heading text is the outline's text exactly, with one
addition from request decision 4 (`## Skills and Agents`) and the Development
subsections this spec chooses, as the outline invites.

```
# TCW — Taxonomy · Capabilities · Work
## Contents
## Problem Statement
## Installation
### Plugin
### CLI
### Cloud Environment Instructions
## Overview
## Taxonomy
### Overview
### Usage
#### Skills
#### CLI
## Capabilities
### Overview
#### Relationship to Taxonomy
### Usage
#### Skills
#### CLI
## Work
### Overview
#### Relationship to Capabilities and Taxonomy
### Lifecycle
#### Jira integration
### Usage
#### Skills
#### CLI
## Skills and Agents
## TCW Local Web App
## Documentation
## Development
### Setting up
### Running the tests
### How work is tracked here
### Measuring the skill layer
### Releasing
### Reporting problems
### License
## Further Reading
```

"Overview", "Usage", "Skills" and "CLI" repeat. GitHub gives a repeated heading
an anchor ending in `-1`, `-2` and so on, counting every earlier heading with
the same text at any level. The Contents anchors are therefore fixed:

| Heading                              | Anchor                            |
| ------------------------------------ | --------------------------------- |
| `## Problem Statement`               | `#problem-statement`              |
| `## Installation`                    | `#installation`                   |
| `### Plugin`                         | `#plugin`                         |
| `### CLI` (Installation)             | `#cli`                            |
| `### Cloud Environment Instructions` | `#cloud-environment-instructions` |
| `## Overview`                        | `#overview`                       |
| `## Taxonomy`                        | `#taxonomy`                       |
| `### Overview` (Taxonomy)            | `#overview-1`                     |
| `### Usage` (Taxonomy)               | `#usage`                          |
| `## Capabilities`                    | `#capabilities`                   |
| `### Overview` (Capabilities)        | `#overview-2`                     |
| `### Usage` (Capabilities)           | `#usage-1`                        |
| `## Work`                            | `#work`                           |
| `### Overview` (Work)                | `#overview-3`                     |
| `### Lifecycle`                      | `#lifecycle`                      |
| `### Usage` (Work)                   | `#usage-2`                        |
| `## Skills and Agents`               | `#skills-and-agents`              |
| `## TCW Local Web App`               | `#tcw-local-web-app`              |
| `## Documentation`                   | `#documentation`                  |
| `## Development`                     | `#development`                    |
| `### Setting up`                     | `#setting-up`                     |
| `### Running the tests`              | `#running-the-tests`              |
| `### How work is tracked here`       | `#how-work-is-tracked-here`       |
| `### Measuring the skill layer`      | `#measuring-the-skill-layer`      |
| `### Releasing`                      | `#releasing`                      |
| `### Reporting problems`             | `#reporting-problems`             |
| `### License`                        | `#license`                        |
| `## Further Reading`                 | `#further-reading`                |

### 2. Section contents

**Title and foreword.** One or two sentences summarizing TCW. Then the current
table (`README.md:6-10`) without its "Lives in" column.

**Contents.** A nested list with exactly the 28 links in the § 1 anchor table,
in that order. It does not link to itself or to `####` headings.

**Problem Statement.** The current text of "The problem" (`README.md:42-53`),
unchanged apart from the heading.

**Installation.**

- _Plugin_: the Claude Code, web/desktop app and Codex install steps and the
  "start a new session" explanation from `README.md:202-231`.
- _CLI_: `pipx install tcw-cli`, why the package is named `tcw-cli`, and the
  requirements (Python ≥ 3.11; Node.js ≥ 22.12 for `tcw serve` only), from
  `README.md:233-247`. The `pip install -e .` line moves to Development.
- _Cloud Environment Instructions_: why a disposable container needs TCW
  installed each session, then two worked examples:
    - **Claude Code on the web**: the session-start script and the
      `.claude/settings.json` wiring from `README.md:256-314`.
    - **Codex cloud**: the install goes in the environment's _setup script_,
      which is set in the environment settings rather than read from the
      repository. The setup script runs with internet access, but the agent has
      none by default. The setup script runs in a separate shell, so `export` does
      not reach the agent; a `PATH` change has to be written to `~/.bashrc`.
      (Source: <https://learn.chatgpt.com/docs/environments/cloud-environment>,
      reached on 2026-09-15 by following the redirect from
      `developers.openai.com/codex/cloud/environments`.)
    - The `tcw provision` note for a work store in another repository
      (`README.md:316-320`) and the plugin-in-a-container note
      (`README.md:322-325`). The pointer to `scripts/remote_session_setup.sh`
      (`README.md:327-330`) moves to Development.

**Overview** (TCW as a whole; request decision 3). Brief: at most 60 lines. It
covers:

- the three axes and their one-directional pointers (a capability names taxonomy
  terms; a work item names the capability it changes);
- the one CLI, `tcw`, and its top-level commands (`init`, `provision`,
  `validate`, `serve`, `taxonomy`, `capabilities`, `work`), with
  `tcw init --id <project-id>` shown as how a repository adopts TCW. Command
  descriptions are written fresh, not copied from `tcw --help`, which still calls
  `serve` "a local read-only web viewer" although the app edits all three axes;
- that everything is plain files in the repository, and a work item's status is
  the folder it sits in;
- that the agent plugin supplies judgment while the CLI enforces the rules;
- `tcw serve`;
- connected projects across repositories, in one or two sentences linking
  `docs/guide/multi-repo.md`. They include the promise that a checkout missing
  some connected projects still works, with the missing ones dropping out
  rather than breaking commands (from `README.md:114-116`), because
  `tcw/store/fs.py:290` cites the README for that promise.

**Taxonomy.**

- _Overview_: vocabulary terms and features, how features name the vocabulary
  they operate on, and inheriting another project's taxonomy (`extends`). Draws
  on `docs/guide/taxonomy-and-capabilities.md:15-60`.
- _Usage › Skills_: `tcw-taxonomy`, with a pointer to `tcw-setup` (in Skills
  and Agents) for bootstrapping a taxonomy from an existing codebase.
- _Usage › CLI_: every `tcw taxonomy` subcommand from its `--help` (`init`,
  `list`, `add`, `show`, `path`, `rm`, `search`, `check`, `extends`), each with
  one line, plus a short example.

**Capabilities.**

- _Overview_: what a capability is (a path-addressed user story with a status),
  federation and local overrides. Draws on
  `docs/guide/taxonomy-and-capabilities.md:62-149`.
- _Overview › Relationship to Taxonomy_: a capability names the vocabulary
  terms it involves and the Feature that delivers it; the pointer runs from
  capability to taxonomy and never the other way.
- _Usage › Skills_: `tcw-capabilities`.
- _Usage › CLI_: every `tcw capabilities` subcommand from its `--help` (`init`,
  `list`, `show`, `path`, `add`, `set`, `reset`, `rm`, `search`, `extends`,
  `check`, `drift`), each with one line, plus a short example.

**Work.** This is the largest section, as the outline allows.

- _Overview_: items, statuses as folders, the inbox, tags, blockers, epics and
  children, the Definition of Done gate, and worktrees, each in a sentence or
  two, linking `docs/guide/work.md` for depth.
- _Overview › Relationship to Capabilities and Taxonomy_: an item declares the
  capabilities it adds, changes or removes, and `complete` refuses until they
  are reconciled (`tcw work lifecycle`, the `complete` gates). Taxonomy is
  reached through those capabilities.
- _Lifecycle_: the two ladders (a stage produces a document; a transition moves
  status; nothing is both), a sentence describing the flow in words, then **one
  Mermaid diagram** showing both (request decision 5):
    - statuses `backlog`, `active`, `review`, `completed`, `discarded`, and one
      "removed" node;
    - transitions `start` (backlog → active), `submit` (active → review),
      `rework` (review → active), `complete` (review | active → completed),
      discard (backlog | active | review → discarded), `drop` (backlog → removed,
      `tcw/store/base.py:3435-3439`), and removal of a resolved item
      (completed | discarded → removed) when `work.retain` says the status is
      not kept (`tcw work lifecycle`, `auto-delete`);
    - stages placed against the status they run in (`STAGE_STATUSES`,
      `tcw/store/base.py:1719-1727`): `inbox` before an item exists; `request`,
      `spec`, `plan` in backlog; `implement` in active; `verify` in review, with
      a note that it may also run in active; `postmortem` out of band, in review
      or completed.

    After the diagram comes a table of transitions and their gates. Its rows are
    the same transitions the diagram shows. The gates are the built-in `gates:`
    lines from `tcw work lifecycle`, without this repository's own `pre:` and
    `bind:` lines. The `drop` row, which `tcw work lifecycle` does not list, says it
    works from backlog only. A closing note says a project binds its own
    instructions and checks to stages and transitions, linking
    `docs/guide/configuration.md`.

- _Lifecycle › Jira integration_: a short opening on what it does, then **a
  table mapping each lifecycle step to its tracker effect** — the requirement
  that it show exactly where Jira fits. Its content, checked against
  `tcw/work/cli.py` and `skills/tcw-work/references/commands.md:195-215`:

    | Lifecycle step                          | Without a tracker     | With a tracker                                                                                       |
    | --------------------------------------- | --------------------- | ---------------------------------------------------------------------------------------------------- |
    | an item is created                      | `inbox accept`, `new` | `tracker import` claims the ticket, then creates a backlog item whose intake is the ticket           |
    | `request` … `plan`                      | unchanged             | unchanged                                                                                            |
    | any time                                | —                     | `tracker link` / `unlink` records or removes a binding; Jira is not touched                          |
    | `start`                                 | moves the item        | also claims a bound ticket, and comments if `comments: true`                                         |
    | `submit`, `rework`, `complete`, discard | moves the item        | also moves a bound ticket to the status mapped under `statuses`, and comments if `comments: true`    |
    | a ticket did not follow                 | —                     | the item still moves; the command exits 1 and records pending or conflicting; `tracker sync` retries |
    | strict mode                             | —                     | see below                                                                                            |

    Strict mode gets its own short list rather than a table cell, because it
    changes several steps differently (`tcw/work/cli.py:371-418`, `:2416-2418`,
    `:2537-2543`):
    - `new` (except `--epic`) and `inbox accept` are refused, pointing at
      `tracker import`;
    - `start` refuses an item with no ticket, and for a bound item claims the
      ticket first and moves only if the claim worked;
    - `submit`, `rework` and `complete --resolution done` read the ticket first and
      refuse unless it is assigned to you and where the item's last step left it;
    - discarding is always allowed, and `drop` refuses an item that was ever bound;
    - a tracker that cannot be reached means refusal, and `tcw serve` refuses the
      same changes.

    Then **three worked examples**, each a short command sequence with one
    sentence per step on what happens in TCW and in Jira: (1) taking a ticket from
    import to completion; (2) linking an item that already exists and starting
    it; (3) the same flow with `strict: true`, showing a refusal. The subsection
    closes with a link to `docs/guide/jira.md` for configuration and limits. It
    holds no configuration reference itself beyond one minimal `tracker` block.

- _Usage › Skills_: `tcw-work` and `tcw-post-mortem`, with a pointer to Skills
  and Agents for the command skills and `tcw-work-stage`.
- _Usage › CLI_: every `tcw work` subcommand from its `--help` (24 of them),
  grouped as board and items, transitions, lifecycle stages, inbox and
  cross-node, tracker, and housekeeping, each with one line.

**Skills and Agents** (request decision 4). It opens by saying the CLI enforces
the rules while skills carry the judgment, and that every entry point is a skill
under both Claude Code and Codex. Then tables for the skills that span axes:
`tcw-setup`, `tcw-configure`, `documentation-sync`, `tcw-work-stage`, the four
`tcw-commands-*` skills, the three `tcw-extras-*` skills; and a table of the
three read-only agents `tcw-verifier`, `tcw-backlog-auditor`, `tcw-post-mortem`.

Across the whole README, each of the 15 directories in `skills/` gets exactly
one row in a skill table, and each of the 3 files in `agents/` exactly one row in
the agents table. `tcw-taxonomy`, `tcw-capabilities`, `tcw-work` and
`tcw-post-mortem` (the skill) go in their axis sections; every other skill goes
here.

**TCW Local Web App** (request decision 7). A full summary that links
`docs/guide/web-viewer.md` for the detail. It covers:

- what it is: a local app for browsing and editing all three axes;
- requirements: Node.js ≥ 22.12, with the web assets prebuilt in the package;
- options `--port` (default 8765) and `--no-open` (`tcw serve --help`);
- loopback-only binding and the request checks (`docs/guide/web-viewer.md:106-111`);
- the tabs, deep links and `tcw://` links;
- creating and editing items, taxonomy entries and capabilities;
- the lifecycle actions it offers: `start`, `complete` and `drop`
  (`web/client/src/ui/app.tsx:703`), where `complete` also discards
  (`docs/guide/web-viewer.md:83-85`);
- that it runs no lifecycle hooks (`docs/guide/configuration.md:229-230`);
- aggregating descendant boards;
- the troubleshooting line for Node version and port collisions.

**Documentation** (request decision 6). A table mapping each topic to a document
a TCW user would read:

1. Configuration (`docs/guide/configuration.md`), first, as requested
2. The Work component (`docs/guide/work.md`)
3. Working from Jira (`docs/guide/jira.md`), new
4. Taxonomy and Capabilities (`docs/guide/taxonomy-and-capabilities.md`)
5. Working across repositories (`docs/guide/multi-repo.md`)
6. The local web viewer (`docs/guide/web-viewer.md`)
7. Linking and validation (`docs/guide/linking-and-validation.md`)
8. The abstraction rules (`docs/lifecycle/abstraction.md`), kept because it is
   in the current table, which the requester said is fine. It explains the
   model to users, unlike the other two files in `docs/lifecycle/`.
9. Release notes (`docs/release-notes/`)
10. Upgrading between major versions: the six `docs/migration-guide-*.md` files
11. Filing a request (`docs/work-inbox-template.md`)

`docs/releasing.md` leaves this table for Development. The line "Every command
group also has `--help`, and a `check` that validates its tree"
(`README.md:578`) stays.

**Development.** Contributor-facing, with the § 1 subsections in this order:

- _Setting up_: clone, `pip install -e '.[dev]'` or
  `scripts/remote_session_setup.sh --force`, and the SessionStart hook that runs
  it in a Claude Code remote session. The `tcw` plugin is enabled for this
  repository in `.claude/settings.json` (request decision 8). A warning that
  `--worktree` implementation needs the editable install repointed, linking the
  `AGENTS.md` section.
- _Running the tests_: `pytest` (what CI runs: `.github/workflows/test.yml`), the
  web checks `pnpm typecheck`, `pnpm lint`, `pnpm test`, `pnpm test:e2e` and
  `pnpm build` (`package.json:8-17`), and the formatting commands
  `pnpm prettify` and `pnpm prettify:check`. These are listed here in their own
  right; `docs/guide/web-viewer.md` keeps its copy (see Non-goals).
- _How work is tracked here_: this repository tracks its own work with
  `tcw work`; the rules are in `AGENTS.md`; `docs/lifecycle/harness.md` and
  `docs/lifecycle/implementation.md` are this repository's own stage rules.
- _Measuring the skill layer_: one paragraph pointing at `evals/`.
- _Releasing_: `scripts/cut_version.py`, the five version files, and
  `docs/releasing.md`.
- _Reporting problems_: GitHub issues, and the `tcw-extras-report` skill.
- _License_: `LICENSE`.

`docs/plan/` (the original phase designs), `docs/superpowers/` and
`docs/changelogs/` are named in Development as contributor history, not in the
Documentation table.

**Further Reading.** Short: `AGENTS.md`, `docs/lifecycle/abstraction.md`,
`docs/plan/`, and `tcw work list` for what is being changed right now.

### 3. Supporting changes

- **New `docs/guide/jira.md`** (request decision 2): the full user-facing Jira
  reference. Its sources, in order of trust:
    1. `skills/tcw-configure/references/tracker.md` and
       `skills/tcw-work/references/commands.md:82-269`, the most current and
       complete tracker text. It includes per-resolution `discarded` statuses,
       strict mode needing every resolution mapped, the `link` template rules,
       `tracker: {}` turning inheritance off, and how parents are found through
       `connected-projects`. This text is written for agents and gets rewritten
       for people.
    2. `README.md:359-561`, current.
    3. From `docs/guide/work.md:605-823`, only what is still true:
        - the inheritance rules;
        - how problems name the file to fix, and fail-closed parsing;
        - unknown keys being reported rather than ignored (`:635-637`);
        - TCW not judging whether `transitions.claim` is misspelled (`:762-766`);
        - the claimable/exclusive output examples;
        - the four-step claim;
        - `import`'s title and ownership (`:795-799`);
        - a binding not being proof of a claim, and having no web edit (`:808-813`);
        - an uncommitted binding being invisible to other clones (`:803-804`).

    Each sentence taken from a source is checked against `tcw/work/cli.py` and
    `tcw/tracker/` before it is kept. The three false claims named in Problem are
    dropped. Where the skill references and the code disagree, the code wins, and
    the disagreement is recorded in `outcome.md`.

- **`docs/guide/work.md`**: the "Working from an external tracker" section
  (`docs/guide/work.md:603-823`) is replaced by a short section of the same name
  that points to `docs/guide/jira.md`. It must keep the literal text
  `tcw work tracker`, which `tests/test_documented_cli_surface.py:261-271`
  requires in that file. No other part of that guide changes. No file links to
  that section's anchor (checked for `work.md#` across Markdown, Python and
  TypeScript files).
- **`tcw-config.yaml`**:
    - The README's documentation entry (`tcw-config.yaml:16-20`) says "install,
      commands, quickstart". It is reworded to match the new README.
    - A new entry (request decision 9): path `docs/guide/jira.md`, trigger
      `Tracker-Change`, described as the user-facing guide to the Jira
      integration, to update whenever `tcw work tracker` behavior, a lifecycle
      command's effect on a bound ticket, or a `work.tracker` key changes.
- **`.claude/settings.json`**: the `"skill-cefailures@skill-cefailures": true`
  line (`.claude/settings.json:4`) is removed (request decision 8).
- Release notes and changelog entries are decided by the `documentation-sync`
  skill at implementation, as this repository requires.

### 4. Abstraction and harness checks

The abstraction test does not apply: no operation is added or changed. On
harness compatibility, the README must describe Claude Code and Codex as equal
targets. Installation gives both harnesses' plugin steps and cloud setup, and
Skills and Agents states that every entry point is a skill both harnesses can
invoke.

## Acceptance criteria

1. **Heading order.** The Markdown headings in `README.md` outside fenced code
   blocks, with their levels, are exactly the Design § 1 list, in order.
2. **No dropped section survives.** No heading in `README.md` contains any of:
   "What it looks like", "Why many repositories", "What it deliberately
   refuses", "What adopting it costs", "Who it's for", "Storage abstraction",
   "Quickstart", "Status".
3. **Contents links.** The link targets in the `## Contents` list are exactly
   the anchor column of the Design § 1 table, in that order, and nothing else.
4. **Foreword.** The first table has columns "Component" and "Answers" and no
   "Lives in" column, and at most two sentences of prose sit between the title
   and that table.
5. **Problem Statement.** The lines between `## Problem Statement` and the next
   heading, with leading and trailing blank lines removed, are identical to
   `README.md:42-53` at commit `0633e7b4`.
6. **Overview length.** From the `## Overview` line up to, but not including, the
   `## Taxonomy` line is at most 60 lines, counting blank lines.
7. **CLI coverage.** For each group (`taxonomy`, `capabilities`, `work`), take
   the subcommand names listed under "positional arguments" in
   `tcw <group> --help`. The group's `#### CLI` subsection contains, for each
   name, a backticked span starting `tcw <group> <name>`, which may continue with
   more words (for example `tcw work tracker import`). Every backticked span in
   that subsection that starts `tcw <group> ` continues with a listed name.
8. **Skill and agent coverage.** Each name in `ls skills/` (15) appears as a link
   in the first column of exactly one skill-table row, in the section Design § 2
   assigns it. Each name in `ls agents/` (3, without `.md`) appears in the first
   column of exactly one row of the agents table in Skills and Agents.
9. **Lifecycle diagram.** Work › Lifecycle holds exactly one ` ```mermaid `
   block. It names all seven stages and the five statuses `backlog`, `active`,
   `review`, `completed`, `discarded`, and has an edge for each of `start`,
   `submit`, `rework`, `complete`, discard, `drop` and removal of a resolved
   item. The block, saved to its own file, renders without error through
   `npx -y @mermaid-js/mermaid-cli@11 -i <file> -o <file>.svg`. If that command
   cannot run on the machine, the criterion is met only by viewing the diagram
   rendered on GitHub.
10. **Transitions table matches the diagram.** The Lifecycle transitions table has
    a row for exactly the transitions named in criterion 9.
11. **Jira placement.** Jira integration contains the lifecycle-to-tracker table,
    the strict-mode list with all five points in Design § 2, and three worked
    examples (import to completion, link then start, strict mode with a refusal).
    It links `docs/guide/jira.md` and has no `tracker` configuration example
    longer than 12 lines.
12. **Jira guide.** `docs/guide/jira.md` exists and has a heading for each of:
    configuration, inherited settings, claimable and exclusive, taking a ticket,
    linking and unlinking, tickets following their items (statuses and sync),
    comments, strict mode, and limits. Every sentence in it that contains the
    word `link` is read. None says `link` claims, transitions or assigns a ticket.
    The file contains neither "No other command gains a network dependency" nor
    "Everything but `timeout-seconds` is required".
13. **work.md is no longer out of date.** `docs/guide/work.md` contains neither
    "claim it for an item that already exists" nor "does the same claim". Its
    `## Working from an external tracker` section is at most 10 lines, links
    `jira.md`, and contains `tcw work tracker`.
14. **Web app.** The TCW Local Web App section names `--port`, the default port
    `8765`, `--no-open`, Node.js 22.12, loopback-only binding, the actions
    `start`, `complete` and `drop`, that `complete` also discards, and that hooks
    do not run. It links `docs/guide/web-viewer.md`. `docs/guide/web-viewer.md`
    is byte-identical to commit `0633e7b4`.
15. **Documentation table.** Its first row is Configuration. It has a row for
    `docs/guide/jira.md`, one for release notes, and one covering the migration
    guides. It has no row for `docs/releasing.md`, `docs/plan/`,
    `docs/superpowers/` or `docs/changelogs/`.
16. **Development** mentions that `.claude/settings.json` enables the `tcw`
    plugin, and names `pytest`, `scripts/remote_session_setup.sh`,
    `scripts/cut_version.py` and `docs/releasing.md`.
17. **Cloud installation** has a Claude Code example and a Codex cloud example.
    The Codex one says the setup script is configured in the environment
    settings and that `export` does not carry over to the agent.
18. **No stale claim.** `README.md` contains no match for `not built`.
19. **Links resolve.** Every relative Markdown link in `README.md`,
    `docs/guide/jira.md` and `docs/guide/work.md` points to a file that exists.
20. **Nothing else breaks.** `pytest` passes, `tcw validate` passes, and
    `pnpm prettier --check README.md docs/guide/jira.md docs/guide/work.md`
    passes. (`README.md` and `docs/guide/work.md` both fail that check at commit
    `0633e7b4`, so meeting it means formatting them.)
21. **Documentation entries.** `tcw work docs` prints a `README.md` entry whose
    description does not contain "quickstart", and a `docs/guide/jira.md` entry
    with trigger `Tracker-Change`.
22. **skill-cefailures removed.** `.claude/settings.json` parses as JSON, still
    enables `tcw@tcw`, and does not contain `skill-cefailures`.
    `git grep -n skill-cefailures -- README.md AGENTS.md .claude skills scripts`
    prints nothing.

## Risks

- **Anchors on repeated headings.** Four headings repeat. The Design § 1 anchor
  table fixes them in advance, and verification checks them on GitHub.
- **Mermaid off GitHub.** PyPI shows `README.md` as the package description
  (`pyproject.toml:9`) and does not render Mermaid, so the diagram shows there
  as a code block. Relative links already fail on PyPI today. Accepted as a
  non-goal; the sentence before the diagram describing the flow in words keeps
  that page readable.
- **Carrying stale text into the new guide.** `docs/guide/work.md`'s tracker
  section has already drifted once. Trusting the skill references and the code
  first (Design § 3) is the guard, criterion 12 checks the known false claims,
  and the new documentation entry flags the guide on future tracker changes.
- **Three tracker references.** The README section, `jira.md` and the two skill
  references all describe tracker behavior, for different readers. The README
  keeps only placement and examples. The documentation entry names `jira.md`,
  and the existing `Configuration-Key-Change` and `Skill-Driven-Component`
  entries already name the skill references.
- **Removed skill names.** `tests/test_skill_lifecycle_parity.py:503-526` fails if
  `README.md` or `docs/guide/` names a removed skill such as `autonomous-work` or
  `tcw-plan-work`. Criterion 20's `pytest` catches it. Using names only from
  `ls skills/` avoids it.
- **Collision with plugin separation.** Backlog item
  `2026-08-12-separate-the-agent-plugin-from-the-python-cli-source` would move
  `skills/` and `agents/`. Whichever lands second updates the README's skill
  links.
- **Claim exclusivity may change.** Backlog item
  `2026-09-15-decide-claim-exclusivity-from-a-jira-project-s-workflow-definition`
  would change the claimable/exclusive output `jira.md` shows as examples. Its
  own documentation evaluation will be flagged by the new `jira.md` entry.
- **README length.** Dropping the pitch sections saves about 160 lines, and
  moving Jira reference to a guide saves about 150, but the new per-axis
  sections add content. No length limit is set beyond Overview's. The Work
  section is expected to be long, as the outline says.

## Notes

- Decided by the spec author, not the requester:
    - the Jira guide replaces the out-of-date section of `docs/guide/work.md`
      rather than sitting beside it;
    - the Contents list stops at `###` and does not link to itself;
    - the migration guides share one Documentation row;
    - `docs/work-inbox-template.md` and `docs/lifecycle/abstraction.md` count as
      user-facing;
    - the new documentation entry's trigger is named `Tracker-Change`;
    - the diagram and the transitions table both show `drop` and the removal of
      resolved items.
- Sibling sweep: every description of `tracker link` in `README.md`,
  `docs/guide/` and `skills/` was checked. Only `docs/guide/work.md:615` and
  `:771-772` are wrong; `skills/tcw-work/references/commands.md:95,213` is
  correct. The search for `skill-cefailures` covered the whole repository
  (`git grep`). Live uses: only `.claude/settings.json:4`.
- Adversarial spec review, round 1 (single reviewer), all findings checked
  against the repository:
    - **Accepted:**
        - the `skill-cefailures` test conflict (resolved by request decision 8);
        - the strict-mode and `start` rows of the Jira table;
        - the wrong and incomplete sources for `jira.md`;
        - the two further false sentences in `work.md`;
        - the missing documentation entry (request decision 9);
        - the `tcw work tracker` string that `work.md` must keep;
        - the diagram and gates table naming different transitions;
        - `verify` also being legal in active;
        - the criteria that could be checked more than one way (1, 3, 6, 7, 9, 11);
        - stale `tcw --help` wording;
        - `complete` discarding in the web app;
        - the self-contradicting sentence about the formatting commands;
        - the overlap with the prose-defects inbox entry and the exclusivity
          backlog item;
        - the imprecise `cli.py:2684` citation.
    - **Rejected:** the doubt about the Codex documentation URL. It was fetched
      during this stage through a redirect from `developers.openai.com`.
    - **Not adopted:** making one tracker document the only source. The
      requester chose a documentation entry instead, and the skill references
      serve agents.
- Assumption: the Codex cloud facts come from OpenAI's documentation as of
  2026-09-15, not from running a Codex cloud environment.
