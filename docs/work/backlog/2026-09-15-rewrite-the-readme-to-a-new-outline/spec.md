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
  shipped (`tcw work tracker` exists: `tcw/work/cli.py:2684`).
- `docs/guide/work.md:605-823` ("Working from an external tracker") is out of
  date. It says `link` claims the ticket (`docs/guide/work.md:615`,
  `docs/guide/work.md:771-772`). The code says it does not: `_tracker_link`
  writes only the binding and makes "no transition, no assignee change"
  (`tcw/work/cli.py:2101-2109`), and its help says "In the tracker: nothing"
  (`tcw/work/cli.py:2686-2691`). That section also does not mention
  `statuses`, `tracker sync`, comments or strict mode, all of which
  `README.md:473-561` covers.

## Goals

1. `README.md` follows the requester's outline as amended by the decisions in
   `initial-request.md`, heading for heading, in order.
2. Each axis is explained on its own: what it is, how it relates to the others,
   and how to use it through skills and through the CLI.
3. The work lifecycle is shown as a diagram of stages and statuses, and Jira is
   described in terms of where it attaches to that lifecycle, with worked
   examples.
4. There is one current, complete Jira reference, `docs/guide/jira.md`, and no
   out-of-date copy remains in `docs/guide/work.md`.
5. Every command, flag, default and behavior the new README states is true of
   the code at the time of writing.

## Non-goals

- Keeping any current README section the outline does not name ("What it looks
  like", "Why many repositories…", "What it deliberately refuses", "What
  adopting it costs", "Who it's for", "Storage abstraction", "Quickstart",
  "Status"). They are removed, not moved to another document (request decision 1).
- Changing `docs/guide/web-viewer.md`. The README summarizes `tcw serve` and
  links to that guide for the detail (decided during this stage; see Notes).
- Rewriting or restructuring any other guide beyond what Design § 3 names.
- Changing TCW's code, CLI, skills or plugin manifests.
- Making the README render well on PyPI. `pyproject.toml:9` publishes it as the
  package description; see Risks.

## Design

### 1. Heading structure

Heading levels follow outline depth: the title is `#`, top-level outline items
are `##`, their children `###`, and so on. Heading text is the outline's text
exactly, with one addition from request decision 4: `## Skills and Agents`
between `## Work` and `## TCW Local Web App`.

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
### (contributor subsections — see § 2)
## Further Reading
```

Headings such as "Overview", "Usage", "Skills" and "CLI" repeat. GitHub gives
repeated headings anchors ending in `-1`, `-2` and so on, in document order, and
the Contents links must use those suffixed anchors.

### 2. Section contents

**Title and foreword.** One or two sentences summarizing TCW. Then the current
table (`README.md:6-10`) without its "Lives in" column.

**Contents.** A nested list linking every `##` and `###` heading, in order.
`####` headings are left out to keep it short.

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
      checked 2026-09-15.)
    - The `tcw provision` note for a work store in another repository
      (`README.md:316-320`) and the plugin-in-a-container note
      (`README.md:322-325`). The pointer to `scripts/remote_session_setup.sh`
      (`README.md:327-330`) moves to Development.

**Overview** (TCW as a whole; request decision 3). Brief: at most 50 lines of
Markdown. It covers the three axes and their one-directional pointers (a
capability names taxonomy terms; a work item names the capability it changes);
the one CLI, `tcw`, and its top-level commands (`init`, `provision`,
`validate`, `serve`, `taxonomy`, `capabilities`, `work`, from `tcw --help`),
with `tcw init --id <project-id>` shown as how a repository adopts TCW; that
everything is plain files in the repository and a work item's status is the
folder it sits in; that the agent plugin supplies judgment while the CLI
enforces the rules; `tcw serve`; and connected projects across repositories, in
one or two sentences linking `docs/guide/multi-repo.md`.

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
  status; nothing is both), then **one Mermaid diagram** showing both (request
  decision 5):
    - statuses `backlog`, `active`, `review`, `completed`, `discarded`, and the
      removal a `drop` performs;
    - transitions `start` (backlog → active), `submit` (active → review), `rework`
      (review → active), `complete` (review | active → completed), discard
      (backlog | active | review → discarded) and `drop` (backlog → removed);
    - stages placed against the status they normally run in: `inbox` before an
      item exists; `request`, `spec`, `plan` in backlog; `implement` in active;
      `verify` in review; `postmortem` out of band, in review or after completion.

    After the diagram comes a table of each transition's gates, taken from
    `tcw work lifecycle`, and a note that a project binds its own instructions and
    checks to stages and transitions (linking `docs/guide/configuration.md`).

- _Lifecycle › Jira integration_: a short opening on what it does, then **a
  table mapping each lifecycle step to its tracker effect** — the requirement
  that it show exactly where Jira fits:

    | Lifecycle step                          | Without a tracker     | With a tracker                                                                                  |
    | --------------------------------------- | --------------------- | ----------------------------------------------------------------------------------------------- |
    | an item is created                      | `inbox accept`, `new` | `tracker import` claims the ticket and creates the backlog item with the ticket as its intake   |
    | `request` … `plan`                      | unchanged             | unchanged                                                                                       |
    | any time                                | —                     | `tracker link` / `unlink` records or removes a binding; Jira is not touched                     |
    | `start`                                 | moves the item        | also claims a bound ticket                                                                      |
    | `submit`, `rework`, `complete`, discard | moves the item        | also moves the ticket to the status mapped under `statuses`, and comments if `comments: true`   |
    | a ticket did not follow                 | —                     | recorded as pending or conflicting; `tracker sync` retries                                      |
    | strict mode                             | —                     | `new` and `inbox accept` refuse; `start`, `submit`, `rework`, `complete` check the ticket first |

    The final wording of each cell is checked against `docs/guide/jira.md` when
    it is written. Then **three worked examples**, each a short command sequence
    with one sentence per step on what happens in TCW and in Jira: (1) taking a
    ticket from import to completion; (2) linking an item that already exists and
    starting it; (3) the same flow with `strict: true`, showing a refusal. The
    subsection closes with a link to `docs/guide/jira.md` for configuration and
    limits. It holds no configuration reference itself beyond one minimal
    `tracker` block.

- _Usage › Skills_: `tcw-work` and `tcw-post-mortem`, with a pointer to Skills
  and Agents for the command skills and `tcw-work-stage`.
- _Usage › CLI_: every `tcw work` subcommand from its `--help` (24 of them),
  grouped as board and items, transitions, lifecycle stages, inbox and
  cross-node, tracker, and housekeeping, each with one line.

**Skills and Agents** (request decision 4). It opens by saying the CLI enforces
the rules while skills carry the judgment, and that every entry point is a skill
under both Claude Code and Codex. Then tables for the skills that span axes:
`tcw-setup`, `tcw-configure`, `documentation-sync`, `tcw-work-stage`, the four
`tcw-commands-*` skills, the three `tcw-extras-*` skills; and the three
read-only agents `tcw-verifier`, `tcw-backlog-auditor`, `tcw-post-mortem`.

Across the whole README, each of the 15 directories in `skills/` and the 3 files
in `agents/` gets exactly one table row: `tcw-taxonomy`, `tcw-capabilities`,
`tcw-work` and `tcw-post-mortem` (the skill) in their axis sections, and
everything else here.

**TCW Local Web App.** A full summary that links `docs/guide/web-viewer.md` for
the detail. It covers what it is (a local app for browsing and editing all three
axes); requirements (Node.js ≥ 22.12, assets prebuilt in the package); options
`--port` (default 8765) and `--no-open` (`tcw serve --help`); loopback-only
binding and the request checks (`docs/guide/web-viewer.md:106-111`); the tabs,
deep links and `tcw://` links; creating and editing items, taxonomy entries and
capabilities; the lifecycle actions it offers, which are `start`, `complete` and
`drop` only (`web/client/src/ui/app.tsx:703`); that it runs no lifecycle hooks
(`docs/guide/configuration.md:229-230`); aggregating descendant boards; and the
troubleshooting line for Node version and port collisions.

**Documentation** (request decision 6). A table mapping each topic to a document
a TCW user would read:

1. Configuration (`docs/guide/configuration.md`), first, as requested
2. The Work component (`docs/guide/work.md`)
3. Working from Jira (`docs/guide/jira.md`), new
4. Taxonomy and Capabilities (`docs/guide/taxonomy-and-capabilities.md`)
5. Working across repositories (`docs/guide/multi-repo.md`)
6. The local web viewer (`docs/guide/web-viewer.md`)
7. Linking and validation (`docs/guide/linking-and-validation.md`)
8. The abstraction rules (`docs/lifecycle/abstraction.md`), kept from the current table
9. Release notes (`docs/release-notes/`)
10. Upgrading between major versions: the six `docs/migration-guide-*.md` files
11. Filing a request (`docs/work-inbox-template.md`)

`docs/releasing.md` leaves this table for Development. The line "Every command
group also has `--help`, and a `check` that validates its tree"
(`README.md:578`) stays.

**Development.** Contributor-facing. Subsections, chosen as is typical for an
open-source project:

- _Setting up_: clone, `pip install -e '.[dev]'` or
  `scripts/remote_session_setup.sh --force`, and the SessionStart hook that runs
  it in a Claude Code remote session. The `tcw` and `skill-cefailures` plugins
  are both enabled for this repository in `.claude/settings.json`
  (`.claude/settings.json:2-5`), as the outline asks.
- _Running the tests_: `pytest` (what CI runs: `.github/workflows/test.yml`),
  and the web checks `pnpm typecheck`, `pnpm lint`, `pnpm test`,
  `pnpm test:e2e`, `pnpm build` (`package.json:8-17`), with the formatting
  commands moved from `docs/guide/web-viewer.md:20-31`. Only a pointer to them
  moves; that guide is not edited.
- _How work is tracked here_: this repository tracks its own work with
  `tcw work`, and the rules are in `AGENTS.md`; `docs/lifecycle/` holds this
  repository's stage rules.
- _Measuring the skill layer_: one paragraph pointing at `evals/`.
- _Releasing_: `scripts/cut_version.py`, the five version files, and
  `docs/releasing.md`.
- _Reporting problems_: GitHub issues, and the `tcw-extras-report` skill.
- _License_: `LICENSE`.

`docs/plan/` (the original phase designs), `docs/superpowers/` and
`docs/changelogs/` are named here as contributor history, not in the
Documentation table.

**Further Reading.** Short: `AGENTS.md`, `docs/lifecycle/abstraction.md`,
`docs/plan/`, and `tcw work list` for what is being changed right now.

### 3. Supporting documents

- **New `docs/guide/jira.md`** (request decision 2). It is the full Jira
  reference. It starts from `README.md:359-561`, which is current, and adds
  what only `docs/guide/work.md:605-823` has and that is still true: the
  inheritance rules in full, how problems name the file to fix, fail-closed
  parsing, the claimable/exclusive output examples, and the four-step claim
  procedure. Every sentence carried over from `docs/guide/work.md` is checked
  against `tcw/work/cli.py` and `tcw/tracker/` before it is kept. The `link`
  claims are dropped.
- **`docs/guide/work.md`**: the "Working from an external tracker" section
  (`docs/guide/work.md:603-823`) is replaced by a short section of the same name
  that points to `docs/guide/jira.md`. No other part of that guide changes.
  (No file links to that section's anchor; checked for `work.md#` across
  Markdown, Python and TypeScript files.)
- **`tcw-config.yaml:18-20`**: the README's documentation entry says
  "install, commands, quickstart". It is reworded to match the new README, since
  the quickstart is gone.
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
   blocks give exactly the Design § 1 list, in
   order, with the Development subsections in the `###` position.
2. **No dropped section survives.** None of these strings appears as a heading
   in `README.md`: "What it looks like", "Why many repositories", "What it
   deliberately refuses", "What adopting it costs", "Who it's for", "Storage
   abstraction", "Quickstart", "Status".
3. **Contents links resolve.** Every link in the Contents list points to an
   anchor GitHub generates for a `##` or `###` heading in the file, counting
   the `-1`/`-2` suffixes on repeated headings. Every `##` and `###` heading
   has a Contents entry.
4. **Foreword.** The first table has columns "Component" and "Answers" and no
   "Lives in" column, and at most two sentences of prose sit between the title
   and that table.
5. **Problem Statement** body is identical to `README.md:42-53` as of commit
   `0633e7b4`.
6. **Overview** is at most 50 lines.
7. **CLI coverage.** Every subcommand listed by `tcw taxonomy --help`,
   `tcw capabilities --help` and `tcw work --help` appears, backticked, in the
   matching section's Usage › CLI, and no subcommand is named there that the
   help does not list.
8. **Skill and agent coverage.** Each name in `ls skills/` (15) has exactly one
   row across the README's skill tables, and each name in `ls agents/` (3,
   without `.md`) has exactly one row in the agents table, in the section
   Design § 2 assigns it. `tcw-post-mortem` is both, so it has one skill row
   (Work) and one agent row (Skills and Agents).
9. **Lifecycle diagram.** Work › Lifecycle holds exactly one ` ```mermaid `
   block. It names all seven stages and the five statuses `backlog`, `active`,
   `review`, `completed`, `discarded`, and has an edge for each of `start`,
   `submit`, `rework`, `complete`, discard and `drop`. The block, saved to its
   own file, renders without error through
   `npx -y @mermaid-js/mermaid-cli -i <file> -o <file>.svg`.
10. **Jira placement.** Jira integration contains the lifecycle-to-tracker table
    and three worked examples (import to completion, link then start, strict
    mode with a refusal), links `docs/guide/jira.md`, and contains no `tracker`
    configuration example longer than 12 lines.
11. **Jira guide.** `docs/guide/jira.md` exists and covers configuration,
    inherited settings, claimable vs exclusive, import, link/unlink, statuses
    and sync, comments, strict mode and limits. It never says `link` claims,
    transitions or assigns a ticket.
12. **work.md is no longer out of date.** `docs/guide/work.md` no longer
    contains the text "claim it for an item that already exists" or "does the
    same claim". Its external-tracker section is at most 10 lines and links
    `jira.md`.
13. **Web app.** The TCW Local Web App section names `--port`, the default port
    `8765`, `--no-open`, Node.js 22.12, loopback-only binding, the actions
    `start`, `complete` and `drop`, and that hooks do not run, and it links
    `docs/guide/web-viewer.md`. `docs/guide/web-viewer.md` is byte-identical to
    commit `0633e7b4`.
14. **Documentation table.** Its first row is Configuration. It has a row for
    `docs/guide/jira.md`, one for release notes, and one covering the migration
    guides. It has no row for `docs/releasing.md`, `docs/plan/`,
    `docs/superpowers/` or `docs/changelogs/`.
15. **Development** mentions `.claude/settings.json` enabling both the `tcw` and
    `skill-cefailures` plugins, `pytest`, `scripts/remote_session_setup.sh`,
    `scripts/cut_version.py` and `docs/releasing.md`.
16. **Cloud installation** has a Claude Code example and a Codex cloud example.
    The Codex one says the setup script is configured in the environment
    settings and that `export` does not carry over to the agent.
17. **No stale claim.** `README.md` does not say tracker adapters or tracker
    synchronization are unbuilt (no match for `not built` or `designed for but
not built`).
18. **Links resolve.** Every relative Markdown link in `README.md`,
    `docs/guide/jira.md` and the edited part of `docs/guide/work.md` points to a
    file that exists.
19. **Nothing else breaks.** `pytest` passes, `tcw validate` passes, and
    `pnpm prettier --check README.md docs/guide/jira.md docs/guide/work.md`
    passes. (`README.md` and `docs/guide/work.md` both fail that check before
    this change, as of commit `0633e7b4`, so meeting it means formatting them.)
20. **Config description.** `tcw-config.yaml`'s `README.md` documentation entry
    no longer says "quickstart".

## Risks

- **Anchors on repeated headings.** Four headings repeat three or four times.
  Contents links are easy to get wrong by one suffix. Criterion 3 checks them
  against how GitHub generates anchors, not against guesses.
- **Mermaid off GitHub.** PyPI shows `README.md` as the package description
  (`pyproject.toml:9`) and does not render Mermaid, so the diagram shows there
  as a code block. Relative links already fail on PyPI today. Accepted as a
  non-goal; a sentence before the diagram describing the flow in words keeps
  that page readable.
- **Carrying stale text into the new guide.** `docs/guide/work.md`'s tracker
  section has already drifted once. Checking each carried-over sentence against
  the code (Design § 3) is the guard, and criterion 11 checks the known false
  claim.
- **The README and web-viewer.md drifting apart.** The README now summarizes
  what `docs/guide/web-viewer.md` describes in full. Keeping the README to a
  summary, with a link, limits what can drift.
- **Collision with plugin separation.** Backlog item
  `2026-08-12-separate-the-agent-plugin-from-the-python-cli-source` would move
  `skills/` and `agents/`. Whichever lands second updates the README's skill
  links.
- **README length.** Dropping the pitch sections saves about 160 lines, and
  moving Jira reference to a guide saves about 150, but the new per-axis
  sections add content. No length limit is set beyond Overview's. The Work
  section is expected to be long, as the outline says.

## Notes

- Decided during this stage: the README's web app section is a full summary
  linking `docs/guide/web-viewer.md` for detail, rather than a complete copy of
  it. This narrows the outline's "cover everything about `tcw serve`", at the
  requester's choice, to avoid two full copies drifting apart.
- Decided by the spec author, not the requester: the Jira guide replaces the
  out-of-date section of `docs/guide/work.md` rather than sitting beside it.
  This follows from request decision 2 together with the out-of-date text found.
- Decided by the spec author: the Contents list stops at `###`; the migration
  guides share one Documentation row; `docs/work-inbox-template.md` counts as
  user-facing.
- Sibling sweep: every description of `tracker link` in `README.md`,
  `docs/guide/` and `skills/` was checked. Only `docs/guide/work.md:615` and
  `:771-772` are wrong; `skills/tcw-work/references/commands.md:95,213` is
  correct.
- Assumption: the Codex cloud facts come from OpenAI's documentation as of
  2026-09-15, not from running a Codex cloud environment.
