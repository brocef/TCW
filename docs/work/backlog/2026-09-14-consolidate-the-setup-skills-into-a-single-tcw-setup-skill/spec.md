# Spec — Separate setting up and configuring TCW from using it: `tcw-setup`, `tcw-configure`, and one Feature and capability per skill

> The item's title still says "a single tcw-setup skill". The requester revised
> the request twice during this stage (`initial-request.md`, revision notes 1–8
> at the top). Retitling the item is a plan-stage task. The requester has said a
> large change is acceptable, because the goal is cleanup.

## Capability changes

This section lists planned ledger and taxonomy changes only; nothing is written
at this stage. Order matters when writing them:

1. Vocabulary terms first.
2. Then Features. `tcw taxonomy add` refuses a Feature naming vocabulary that
   isn't registered yet (`skills/tcw-taxonomy/SKILL.md:57-67`).
3. Then capabilities. `tcw capabilities set` refuses a `Feature` or
   `Superseded by` reference that doesn't resolve yet
   (`skills/tcw-capabilities/SKILL.md:55-63`).

### Taxonomy

**New Vocabulary — `skill`.** "An agent skill: a document an agent loads to learn
how to do one kind of task. The TCW plugin ships some, and a project can bind its
own to lifecycle stages." The definition is deliberately general, because
`configurable-work-lifecycle` already uses "agent skills" for a project's *own*
skills (`tcw taxonomy show configurable-work-lifecycle`). No term named `skill`
exists today.

**Sixteen new Features, one per top-level skill.**
- **Slugs.** Every slug is the skill's directory name followed by `-skill`, set
  explicitly with `-s`. Without it, `add` makes the slug from the name, so "TCW
  Initialization Skill" would become `tcw-initialization-skill`.
- **Vocabulary.** Each Feature names `skill` plus every existing term it
  operates on. `--vocab` can be repeated, and `local-web-app` already names
  several.
- **Nesting.** The five per-stage Features are nested under
  `tcw-work-stage-skill`, following "Nest specializations under a parent"
  (`skills/tcw-taxonomy/SKILL.md:79-80`).
- **Related Features.** A Feature that covers the same area as an existing Feature
  gets a `relatesTo` link to it. This is the one metadata edit the taxonomy skill
  does by hand (`skills/tcw-taxonomy/SKILL.md:116`), followed by
  `tcw taxonomy check`.

Per the taxonomy skill's boundary rule (`:76-78`), a Feature description names
the interaction area only, never behavior; behavior lives in the capability.

| Skill | Feature path | Feature name | Vocabulary | `relatesTo` |
| --- | --- | --- | --- | --- |
| `tcw-setup` | `tcw-setup-skill` | TCW Initialization Skill | `skill`, `cli`, `node`, `store` | `provisioned-component-stores` |
| `tcw-configure` | `tcw-configure-skill` | TCW Configuration Skill | `skill`, `node`, `store`, `work-item/lifecycle-hook`, `work-item/definition-of-done` | `configurable-work-lifecycle`, `configurable-component-store-location`, `external-work-tracker`, `connected-project-registry` |
| `tcw-work` | `tcw-work-skill` | TCW Work Skill | `skill`, `work-item`, `work-item/transition` | `work-inbox` |
| `tcw-taxonomy` | `tcw-taxonomy-skill` | TCW Taxonomy Skill | `skill`, `vocabulary`, `feature` | `taxonomy-feature-registry` |
| `tcw-capabilities` | `tcw-capabilities-skill` | TCW Capabilities Skill | `skill`, `capability` | `capability-feature-association` |
| `documentation-sync` | `documentation-sync-skill` | TCW Documentation Sync Skill | `skill`, `work-item/lifecycle-stage` | — |
| `tcw-work-stage` | `tcw-work-stage-skill` | TCW Work Stage Skill | `skill`, `work-item/lifecycle-stage` | `configurable-work-lifecycle` |
| `tcw-work-stage-request` | `tcw-work-stage-skill/tcw-work-stage-request-skill` | TCW Request Stage Skill | `skill`, `work-item/lifecycle-stage` | — |
| `tcw-work-stage-spec` | `tcw-work-stage-skill/tcw-work-stage-spec-skill` | TCW Spec Stage Skill | `skill`, `work-item/lifecycle-stage` | — |
| `tcw-work-stage-plan` | `tcw-work-stage-skill/tcw-work-stage-plan-skill` | TCW Plan Stage Skill | `skill`, `work-item/lifecycle-stage` | — |
| `tcw-work-stage-implement` | `tcw-work-stage-skill/tcw-work-stage-implement-skill` | TCW Implement Stage Skill | `skill`, `work-item/lifecycle-stage` | — |
| `tcw-work-stage-verify` | `tcw-work-stage-skill/tcw-work-stage-verify-skill` | TCW Verify Stage Skill | `skill`, `work-item/lifecycle-stage` | — |
| `tcw-triage-issues` | `tcw-triage-issues-skill` | TCW Issue Triage Skill | `skill`, `work-item/intake` | `work-inbox` |
| `tcw-post-mortem` | `tcw-post-mortem-skill` | TCW Post-Mortem Skill | `skill`, `work-item/lifecycle-stage` | — |
| `autonomous-work` | `autonomous-work-skill` | TCW Autonomous Work Skill | `skill`, `work-item` | — |
| `tcw-report` | `tcw-report-skill` | TCW Report Skill | `skill` | — |

### Capabilities

```yaml
new:
    - skills/tcw-setup
    - skills/tcw-configure
    - skills/tcw-work
    - skills/tcw-taxonomy
    - skills/tcw-capabilities
    - skills/documentation-sync
    - skills/tcw-work-stage
    - skills/tcw-work-stage-request
    - skills/tcw-work-stage-spec
    - skills/tcw-work-stage-plan
    - skills/tcw-work-stage-implement
    - skills/tcw-work-stage-verify
    - skills/tcw-triage-issues
    - skills/tcw-post-mortem
    - skills/autonomous-work
    - skills/tcw-report
changed:
    - plugin/work-lifecycle
    - work/consolidate-plans
    - work/search-the-work-items
    - work/audit-work-backlog
    - plugin/report-an-issue-upstream
    - plugin/run-a-post-mortem
    - plugin/triage-github-issues
    - taxonomy/bootstrap-the-taxonomy
    - capabilities/bootstrap-the-capabilities
    - plugin/bootstrap-the-cli
    - work/complete-a-work-item
```

**New — one capability per skill, under a `skills/` namespace.** For each skill:

- **Path:** `skills/<skill-directory>`.
- **Name:** the requester's form, "Offer a skill dedicated to instructing agents
  how to …" (for example, `skills/tcw-setup`: "Offer a skill dedicated to
  instructing agents how to set up TCW where it does not work yet").
- **Body:** the ledger's existing form, "As a user or agent, I …", which every
  capability read during this spec uses. The body carries the behavior of every
  capability folded into it (below), so nothing that capability said is lost.
- **Fields:** `Feature` is the skill's Feature path from the table above, and
  `Subject` is `skill`.
- **Status:**
  - The fourteen skills that ship today are created `Supported`. The completion
    gate only fails a `new:` path that is still `Missing` (`tcw/work/recursion.py:58-61`),
    so a path created `Supported` passes it. Seeding a skill that already ships as
    `Missing` would record a false status on `main` until completion.
  - `skills/tcw-setup` and `skills/tcw-configure` are created `Missing` and
    flipped at completion.

**Changed — retired and folded in.** Each of these capabilities describes what a
user does through one skill, so its content moves into that skill's capability.

- **How it is retired:** `tcw capabilities set <path> --status Omitted --field "Superseded by=<successor>"`.
- **Why not delete it:** `tcw capabilities` has no command that deletes a
  capability (`tcw capabilities --help` lists `init, list, show, path, add, set,
  reset, search, extends, check, drift`), and deleting the folder by hand is the
  kind of filesystem shortcut `docs/lifecycle/abstraction.md` rules out.
- **Why it still works:** `Superseded by` is a checked reference
  (`tcw/store/fs.py:2818-2820`), so the successor must exist first. The retired
  paths stay readable and resolvable.

| Retired capability | Folded into |
| --- | --- |
| `plugin/work-lifecycle` | `skills/tcw-work` |
| `work/consolidate-plans` | `skills/tcw-work` (procedure `skills/tcw-work/references/procedures/consolidate-plans.md`) |
| `work/search-the-work-items` | `skills/tcw-work` (`…/procedures/search.md`) |
| `work/audit-work-backlog` | `skills/tcw-work` (`…/procedures/audit-backlog.md`) |
| `plugin/report-an-issue-upstream` | `skills/tcw-report` |
| `plugin/run-a-post-mortem` | `skills/tcw-post-mortem` |
| `plugin/triage-github-issues` | `skills/tcw-triage-issues` |
| `taxonomy/bootstrap-the-taxonomy` | `skills/tcw-setup` |
| `capabilities/bootstrap-the-capabilities` | `skills/tcw-setup` |

**Changed — kept, reworded:**
- **`plugin/bootstrap-the-cli`.** Its body is mostly the `SessionStart` hook that
  installs the CLI, which is plugin behavior rather than skill behavior. So it stays
  in `plugin/` beside `plugin/install-as-a-plugin`, and gets no `Feature`. Its two
  mentions of `tcw-plugin` become `tcw-setup`.
- **`work/complete-a-work-item`.** Line 25 of its description links
  `tcw://C/plugin/triage-github-issues`; that becomes
  `tcw://C/skills/tcw-triage-issues`. A `git grep` found no other reference to
  any retired path outside past changelogs.

**Deliberately not touched:**
- `work/run-a-lifecycle-stage`, `work/configure-the-work-lifecycle`,
  `work/declare-which-documents-track-which-changes`,
  `work/read-the-documentation-gate-for-a-change`, and
  `work/customize-the-definition-of-done` describe CLI and configuration-file
  behavior, which works with or without any skill.
- `plugin/install-as-a-plugin` describes the plugin, not a skill.

## Problem

Setup and configuration material is spread across four skills and three slash
commands. Nothing about the names says which skills set TCW up, which change its
configuration, and which use it.

| Material | Where it lives today |
| --- | --- |
| Installing or repairing the `tcw` CLI | `skills/tcw-plugin/SKILL.md:62-115` |
| Starting a taxonomy | `commands/tcw-taxonomy-init.md:5` → `skills/tcw-taxonomy/references/init.md` |
| Starting a capabilities ledger | `commands/tcw-capabilities-init.md:5` → `skills/tcw-capabilities/references/init.md` |
| `tcw init`, `tcw provision` | No skill document. Refusal text only (`skills/tcw-taxonomy/SKILL.md:30-36`, `skills/tcw-capabilities/SKILL.md:18-25`); user guide `README.md:336-351` |
| `work.documentation` | `commands/tcw-docs-sync-setup.md:7` → `skills/documentation-sync/references/setup.md` |
| `work.lifecycle` (bindings, `timeout`) | `skills/tcw-work/references/hooks.md:1-41`; `timeout` in `docs/guide/configuration.md:173` only |
| `docs/work/dod.yaml` | One clause, `skills/tcw-work/references/transitions.md:112` |
| `work.retain`, `work.auto-commit-transitions` | `skills/tcw-work/references/transitions.md:11-14`, `:23-30` |
| `work.trunk-branch` | No skill document; `docs/guide/work.md:188` |
| `work.publish-transitions` | `skills/tcw-work/references/commands.md:227` |
| `work.tracker` | `skills/tcw-work/references/commands.md:93-107` |
| `<component>.path`, `<component>.repository` | Refusal text only; `skills/tcw-work/references/commands.md:150-210`; user guide `docs/guide/multi-repo.md:199-230` |
| `connected-projects` | `skills/tcw-work/references/commands.md:173-177` |
| `taxonomy.extends`, `capabilities.extends` | `skills/tcw-taxonomy/SKILL.md:93-102`, `skills/tcw-capabilities/SKILL.md:86-91` |

Six concrete consequences:

1. **Setup requests go to usage skills.** `tcw-taxonomy`'s `description` lists
   "bootstrapping a taxonomy from an existing codebase", and its `when_to_use`
   lists "seeding" (`skills/tcw-taxonomy/SKILL.md:3-4`).
2. **Configuration requests go to usage skills.** `documentation-sync`'s
   description advertises "a project declares documentation entries — in
   `tcw-config.yaml` under `work.documentation`" (`skills/documentation-sync/SKILL.md:3`).
3. **Two ways to reach one procedure.** Each setup procedure is reachable through
   a slash command or through a usage skill's pointer. Codex has no slash commands.
4. **`tcw-plugin` is two unrelated things in one skill.** It combines a map of the
   other skills (`skills/tcw-plugin/SKILL.md:12-60`) with CLI installation
   (`:62-115`).
5. **Configuration keys are documented piecemeal or not at all.** The table
   shows eleven places across four files, and two keys have no skill text at all.
6. **The skills are invisible to the project's own taxonomy.** No term or Feature
   describes a skill. Their capabilities are scattered across `plugin/`, `work/`,
   `taxonomy/` and `capabilities/`, and some skills have no capability at all;
   `autonomous-work` is one.

## Goals

1. **`tcw-setup`** is the one skill for getting TCW working where it doesn't work
   yet: a project that doesn't use TCW, a machine that lacks the CLI or a declared
   store, or a CLI that is missing, broken, or stale.
2. **`tcw-configure`** is the one skill for changing the configuration of a
   project that already uses TCW. That means every key in `tcw-config.yaml` that
   the CLI reads, plus `docs/work/dod.yaml`, except `id` and `work.tags` (see
   Non-goals).
3. Both skills' `SKILL.md` files route and nothing else. Their bodies say which
   reference document to open, and, for first-time setup, in what order.
4. The usage skills keep their names. They stop presenting themselves as setup or
   configuration skills. Where they still describe a key's effect at runtime,
   they point to `tcw-configure` for how to set it.
5. There is one way into each procedure, and it works the same under Claude and
   Codex.
6. Existing setup and configuration text is moved, not rewritten, wherever it
   already exists.
7. Every top-level skill has exactly one Feature and exactly one capability, and
   every capability that describes a skill is that one.

## Non-goals

- Changing what `tcw-report`, `tcw-triage-issues`, `tcw-post-mortem`,
  `autonomous-work`, or the six `tcw-work-stage*` skills say, beyond pointers.
- Any change to the `tcw` CLI, including adding a command that deletes a
  capability (see Notes).
- Stub commands or a stub `tcw-plugin` under the old names.
- Rewriting history: completed work items under `docs/work/`, and changelogs and
  release notes of past versions.
- **`id`.** It is written once by `tcw init --id` (`project.md`), and changing it
  is not a supported configuration change.
- **`work.tags`.** The tag vocabulary is registered with `tcw work tags add` in
  the middle of filing work (`skills/tcw-work/references/lifecycle/stage-inbox.md`
  step 3; `skills/tcw-triage-issues/SKILL.md:165`), and `procedures/search.md:30`
  reads `tags.md` too. It is part of using `tcw-work`, so `tags.md` stays there.
- Separating the plugin from the Python source
  (`2026-08-12-separate-the-agent-plugin-from-the-python-cli-source`), beyond a
  one-line note on that item.
- Running the paid eval harness. That belongs to
  `2026-09-11-run-the-eval-harness-and-act-on-what-it-finds` (see Risks).

## Design

### The skill set after this change

`skills/` goes from **fifteen** skills to **sixteen**: `tcw-plugin` is removed,
and `tcw-setup` and `tcw-configure` are added. The grouping in the table is for the
reader only; it is not a folder structure.

| Group | Skill | Change in this item |
| --- | --- | --- |
| **Setting up** | `tcw-setup` | **new**: install half of `tcw-plugin`, both `init.md`s, new `project.md` |
| **Configuring** | `tcw-configure` | **new**: all configuration text listed in Problem |
| **Using TCW** | `tcw-work` | loses configuration text from `hooks.md`, `transitions.md`, `commands.md`; points to `tcw-configure` |
| | `tcw-taxonomy` | loses `references/init.md`, the setup triggers in its description, and how to declare `extends`; points to both new skills |
| | `tcw-capabilities` | loses `references/init.md` and how to declare `extends`; points to both new skills |
| | `documentation-sync` | loses `references/setup.md` and the configuration trigger in its description; points to `tcw-configure` |
| | `tcw-work-stage`, `…-request`, `…-spec`, `…-plan`, `…-implement`, `…-verify` | Feature and capability only |
| | `tcw-triage-issues`, `tcw-post-mortem`, `autonomous-work` | Feature and capability only |
| **Reporting to TCW** | `tcw-report` | Feature and capability only |
| *(removed)* | ~~`tcw-plugin`~~ | install half → `tcw-setup`; skill map deleted (D5) |

```
skills/
  autonomous-work/
  documentation-sync/
    SKILL.md
    references/
      cut-version.md
      release-notes-and-changelogs.md
  tcw-capabilities/
    SKILL.md                     # references/ removed
  tcw-configure/                 # new
    SKILL.md                     # routing only
    references/
      work.md                    # work.lifecycle (bindings, timeout), dod.yaml,
                                 #   work.retain, work.auto-commit-transitions,
                                 #   work.trunk-branch, work.publish-transitions
      docs-sync.md               # work.documentation, and the CLAUDE.md fallback
      tracker.md                 # work.tracker
      stores.md                  # <component>.path and <component>.repository
      projects.md                # connected-projects, taxonomy.extends, capabilities.extends
  tcw-post-mortem/
  tcw-report/
  tcw-setup/                     # new
    SKILL.md                     # routing only
    references/
      install.md                 # CLI and plugin; a missing, broken, or stale CLI
      project.md                 # tcw init, tcw provision, tcw validate
      taxonomy.md                # starting a taxonomy from existing code
      capabilities.md            # starting a capabilities ledger
  tcw-taxonomy/
    SKILL.md                     # references/ removed
  tcw-triage-issues/
  tcw-work/
  tcw-work-stage/
  tcw-work-stage-implement/
  tcw-work-stage-plan/
  tcw-work-stage-request/
  tcw-work-stage-spec/
  tcw-work-stage-verify/
```

`commands/` loses three files and keeps ten: `tcw-audit-work-backlog`,
`tcw-consolidate-plans`, `tcw-cut-version`, `tcw-drive-work-to-completion`,
`tcw-plan-work`, `tcw-post-mortem`, `tcw-process-inbox`, `tcw-triage-issues`,
`tcw-verify-work`, `tcw-work-search`.

### D1 — Where the line between the two skills falls

- **`tcw-setup` covers "TCW doesn't work here yet"**: a new project, a new
  machine for an existing project (`tcw provision`), and a CLI that is missing,
  broken, or stale. The requester's original layout already put "a missing or
  stale CLI" in `install.md` and provisioning in `project.md`
  (`initial-request.md`, the agreed shape).
- **`tcw-configure` covers "TCW works here, and the user wants it to behave
  differently"**: every key listed in Goal 2.
- **"Set up X" where X is a configuration area routes to `tcw-configure`.** Users
  say "set up documentation tracking" or "set up a hook". So `tcw-setup`'s routing
  table has explicit rows sending documentation entries, lifecycle bindings, the
  Definition of Done, a tracker, store locations, and connected or inherited
  projects to the `tcw-configure` skill. `tcw-configure`'s description uses the
  words "set up" for those areas.
- **First-time setup that also wants configuration** ends at `project.md`'s last
  step, which hands off to the `tcw-configure` skill by name.

### D2 — Each `SKILL.md` routes and nothing else

Each body holds:

- One sentence on what the skill is for.
- One sentence on what the other skill is for, naming it as "the `tcw-setup`
  skill" or "the `tcw-configure` skill".
- A routing table with columns *situation* → *document*, with situations in the
  user's words. `tcw-setup`'s table also carries the redirect rows from D1.

`tcw-setup`'s body also gives the first-time order: install, then project, then
taxonomy, then capabilities. Only "taxonomy before capabilities" is written down
today (`skills/tcw-capabilities/references/init.md:6-9`); the rest follows from
each step needing the previous one. The order tells the agent which document to
open first, so it counts as routing (Goal 3).

**Size limit.** Each body, meaning everything after the closing `---` of the
frontmatter, is at most 60 lines. `tests/test_skill_lifecycle_parity.py:276-285`
applies that same limit and counting rule to `tcw-work`. D6 extends that test to
cover both new skills, so the limit keeps holding after merge.

**Frontmatter:**

- **`tcw-setup` `description`** names: a project that doesn't use TCW yet; a
  `tcw` that is missing, broken, or stale; getting an existing TCW project working
  on a new machine; starting a taxonomy or capabilities ledger. It says
  configuration changes belong to the `tcw-configure` skill.
- **`tcw-configure` `description`** names: changing or setting up lifecycle
  bindings, the Definition of Done, documentation entries, a tracker, store
  locations, connected projects, and inherited taxonomy or capabilities.
- Both fill in `when_to_use`, as the other skills do.
- **`allowed-tools`** is the list of tool calls Claude lets a skill make without
  asking. For each new skill it is the union of the lists on the skills it takes
  text from, and nothing else is added:
  - `tcw-setup`: `skills/tcw-plugin/SKILL.md:5` plus `Read, Grep, Glob` from
    `skills/tcw-taxonomy/SKILL.md:5`.
  - `tcw-configure`: `skills/tcw-work/SKILL.md:5` plus `Grep, Glob` from
    `skills/tcw-taxonomy/SKILL.md:5`.
- `compatibility`, `metadata` and `license` on `tcw-setup` carry over from
  `skills/tcw-plugin/SKILL.md:6-9`. `tcw-configure` carries `metadata` and
  `license`.

**Harness rule.** Under Claude, a hint can be passed (`/tcw:tcw-setup taxonomy`).
Skill arguments are Claude-only, so a hint is a convenience and never the only
way to reach a document. Neither body may depend on `$ARGUMENTS` or on dynamic
context injection. Dynamic context injection is the `` !`cmd` `` syntax, which
under Claude runs a command and puts its output into the skill.

### D3 — Where each reference document comes from

**Rules for every reference document:**

- It is self-contained. It does not send the agent into `docs/guide/` or the
  README, which a plugin install is not guaranteed to carry once the plugin and
  the Python source are separated.
- A pointer to another skill names that skill and its document, for example "the
  `tcw-configure` skill's `references/docs-sync.md`". `commands/tcw-taxonomy-init.md:5`
  refers to skill files the same way, and `documentation-sync/SKILL.md:21-23`
  already points from one skill into another's reference files.

**`tcw-setup/references/`**

| Document | Source | How |
| --- | --- | --- |
| `install.md` | `skills/tcw-plugin/SKILL.md:62-115` | **Moved.** Wording naming the old skill changes. The "Installing into a cloud environment" paragraph (`:107-110`) currently points to the README; it keeps the rule in its own words and drops that pointer. |
| `project.md` | none | **New.** Covers `tcw init --id` and the per-component `init`s, and `tcw provision` for a store or project declared in another repository. It ends with `tcw validate` and the hand-off to the `tcw-configure` skill. |
| `taxonomy.md` | `skills/tcw-taxonomy/references/init.md` | **Moved** with `git mv`. |
| `capabilities.md` | `skills/tcw-capabilities/references/init.md` | **Moved** with `git mv`. Line 9, "point the user at `/tcw-taxonomy-init`", becomes a pointer to `taxonomy.md`. |

**`tcw-configure/references/`**

| Document | Source | How |
| --- | --- | --- |
| `work.md` | `skills/tcw-work/references/hooks.md:1-41` and `:97-98`; `transitions.md:11-14`, `:23-30`, `:112` | **Moved:** binding shape, roles, kinds, `when:`, the trust note, and how to set `work.retain` and `work.auto-commit-transitions`. **New text:** `work.lifecycle.timeout`, `docs/work/dod.yaml` (replaces the built-in list rather than adding to it), `work.trunk-branch`, `work.publish-transitions`. |
| `docs-sync.md` | `skills/documentation-sync/references/setup.md` | **Moved** with `git mv`. It keeps the `CLAUDE.md` form for projects that don't use TCW (`setup.md:27`). It is retitled from "Set Up Documentation Sync" to "Declare which documents track which changes". Its pointers into `SKILL.md` (`:34`, `:37`) name the `documentation-sync` skill explicitly. |
| `tracker.md` | `skills/tcw-work/references/commands.md:93-107` | **Moved.** The `tcw work tracker list` and `show` rows (`:88-91`) stay in `commands.md`, followed by a one-line pointer to `tracker.md`. |
| `stores.md` | none | **New.** Covers `taxonomy.path`, `capabilities.path`, `work.path`, and a `repository` block. It must say that changing a store's path does **not** move existing items: stores that aren't empty are never moved automatically, and moving them is the user's own step (`docs/guide/multi-repo.md:205`). It ends with `tcw validate`, and `tcw provision` wherever a `repository` block was added. How stores behave at runtime stays in `tcw-work`'s `commands.md`. |
| `projects.md` | `skills/tcw-work/references/commands.md:173-177`; `skills/tcw-taxonomy/SKILL.md:93-98`; `skills/tcw-capabilities/SKILL.md:86-91` | **Moved:** declaring `connected-projects` (bare locator or `{path, repository}`), and declaring inheritance with `tcw taxonomy extends add\|rm` and `tcw capabilities extends [--rm]`. How inherited entries are addressed, overridden and reset is usage, and stays in the axis skills. |

**Non-TCW projects and `docs-sync.md`.** `documentation-sync` also serves
projects that don't use TCW. Its pointers to setup therefore open the
`tcw-configure` skill's `references/docs-sync.md` **directly by document**, never
by asking the agent to choose the `tcw-configure` skill from its description,
which is about TCW projects. The same plugin ships both skills, so the document is
always present.

### D4 — What each existing skill and document loses and keeps

- **`tcw-taxonomy`**
  - Remove "bootstrapping a taxonomy from an existing codebase" from `description`,
    and "seeding" and "bootstrapping" from `when_to_use` (`SKILL.md:3-4`).
  - Remove "See `tcw-plugin` for the cross-skill map." (`:24-25`).
  - Replace `## Bootstrap` (`:104-107`) with one line pointing to `tcw-setup`.
  - In `## Inheritance` (`:93-102`), how to declare `extends` moves to
    `projects.md`. How inherited terms resolve stays, with one line pointing to
    `tcw-configure`. The quick-reference row for `extends` (`:119`) points there
    too.
  - The refusal text for a store that isn't provisioned (`:30-36`) stays.
- **`tcw-capabilities`**
  - Replace `## Bootstrap` (`SKILL.md:117-120`) with one line pointing to
    `tcw-setup`.
  - In `## Federation` (`:86-91`), declaring `extends` moves to `projects.md`.
    Overrides and `reset` stay. The quick-reference row (`:133`) points to
    `tcw-configure`.
  - The refusal text at `:18-25` stays.
  - Sibling defect (see Notes): `:107` tells the agent to "use `remove`", a command
    that doesn't exist.
- **`tcw-work`**
  - `SKILL.md`:
    - Delete "`tcw-plugin` maps the skills." (`:19-20`).
    - `:55` points to `hooks.md` for what bindings do at runtime, and to
      `tcw-configure` for declaring them.
    - The body is exactly 60 lines today, the limit. Deleting the `tcw-plugin`
      sentence frees the room this edit needs, and the body must stay at or under
      60.
  - `references/hooks.md` keeps "The three verbs" (`:43-66`), "What runs, and
    what does not" (`:68-84`), and "Two limits worth knowing" (`:86-95`). It
    loses `:1-41` and `:97-98`, and opens with one line pointing to `tcw-configure`.
  - `references/transitions.md` keeps what `retain` and `auto-commit-transitions`
    do at transition time, naming each key with a pointer to `tcw-configure`, and
    loses how to set them.
  - `references/commands.md` loses `:93-107` (tracker configuration) and
    `:173-177` (declaring connected projects), and keeps a pointer where each was.
  - `references/lifecycle/default/README.md:51` says "[`hooks.md`](../../hooks.md)
    has the binding shapes and the conditions". Those move, so it points to the
    `tcw-configure` skill's `references/work.md` instead.
- **`documentation-sync`**
  - `description`: remove the "Use when a project declares documentation entries …"
    sentence (`SKILL.md:3`). Using the entries after a code change stays;
    declaring them is `tcw-configure`'s.
  - The references to `references/setup.md` (`:15`, `:29`, table row `:98`)
    point to the `tcw-configure` skill's `references/docs-sync.md`, by document
    (D3).
  - `references/release-notes-and-changelogs.md:5` ("read `setup.md`") gets the
    same change.

### D5 — The skill map is deleted

`skills/tcw-plugin/SKILL.md:12-60` isn't moved anywhere. Everything it says is
already said by a skill that stays:

| What the map says | Already said at |
| --- | --- |
| The order `Vocabulary → Features → Capabilities → Work` | `skills/tcw-work/SKILL.md:17`, `skills/tcw-taxonomy/SKILL.md:20` |
| Capabilities point loosely at a `Subject` and strongly at a `Feature` | `skills/tcw-capabilities/SKILL.md:27` |
| The axes point forward; taxonomy never points back | `skills/tcw-taxonomy/SKILL.md:23-24` |
| `tcw-work` runs the capability check for product changes | `skills/tcw-work/SKILL.md:18-19` |
| `tcw-report` sends feedback to TCW; `tcw-triage-issues` reads the user's own issues | both skills' `description` fields |
| Which axis skill handles which request | each axis skill's `description`; `tcw-taxonomy` and `tcw-capabilities` name their neighbours (`:3`) |

Retargeted case B5 (D6) measures whether the descriptions still route an
orientation question once the map is gone.

### D6 — Eval coverage is rebuilt

`tests/test_eval_coverage.py` fails unless every shipped skill is named by some
eval case (its `invokes` or `skill` key) or listed in `EXCLUSIONS` in
`evals/coverage.py`.

**Case changes** (the requester accepted the first review's recommendation):

1. **B5 is retargeted, not deleted.** It currently tests the skill map
   (`evals/evals.json:592-622`). It becomes `skill: cross-axis`,
   `invokes: ["tcw-taxonomy", "tcw-capabilities"]`, keeping its prompt and
   assertions. That makes it the measure of D5's claim.
2. **New `tcw-configure` case, phrased "set up", on the existing fixture.**
   - **Prompt:** "Set up documentation tracking so `docs/api.md` is updated
     whenever the public API changes." The fixture's existing entries
     (`evals/seed_fixture.py:243-253`) do not name `docs/api.md`, so the two arms
     can differ.
   - **Assertions, all existing predicates:**
     - `transcript_contains` `tcw-configure/references/docs-sync.md`. Transcript
       text includes tool-call inputs (`evals/grade.py:98-104`).
     - `transcript_absent` `tcw-setup/references/`.
     - `files_changed_exactly` `["tcw-config.yaml"]`.
     - `validate_exit_zero`.
3. **New `tcw-setup` case: initialize a fresh repository.**
   - **Prompt:** asks to start using TCW in a plain git repository.
   - **Assertions:** `transcript_contains` `tcw-setup/references/project.md`;
     `transcript_absent` `tcw-configure/references/`; `validate_exit_zero`.
   - **Needs a new "bare" fixture variant:** a git repository with code and no
     `tcw-config.yaml`. That touches `evals/seed_fixture.py`, `evals/run_evals.py`
     (which today picks the variant only by axis and arm, `:113-119`), a new
     `fixture` key documented in `evals/evals.json`'s schema block, and
     `tests/test_eval_fixture.py`.
4. **B4 and B8 each gain `transcript_absent` `tcw-setup/references/`.** B8 ends
   "Set it up.", so this catches the setup skill taking a usage request.

**Coverage bookkeeping.** `PARTIAL` in `evals/coverage.py:51-57` moves from
`tcw-plugin` to `tcw-setup`. Its reason is rewritten: the install and repair route
stays deliberately unmeasured, because faking a broken install inside a test
session is unsafe and would measure the fake (`:53-56`).

**Mutation checks without a paid run.** Each new or changed assertion is checked
by grading a hand-built transcript and fixture through `evals/grade.py`, as
`tests/test_eval_grading.py` already does:

- one transcript where the assertion should pass, and it does;
- one where it should fail, and it does — for example, a transcript that opens
  `tcw-setup/references/project.md` for the "set up documentation tracking" case.

These live as pytest tests, so they keep running after merge.

**Lasting guards, not one-time searches:**

- **A `DELETED`-style test for the removed names.** It follows the pattern at
  `tests/test_skill_lifecycle_parity.py:47,254` and covers `tcw-plugin`,
  `tcw-taxonomy-init`, `tcw-capabilities-init` and `tcw-docs-sync-setup` under
  `skills/`, `commands/`, the manifests, and `README.md`.
- **`tests/test_skill_lifecycle_parity.py`'s router tests extended to both new
  skills:** the 60-line body limit, and every file in the skill's `references/` is
  linked from its `SKILL.md`.

### D7 — Other files that name removed things, or count skills

| File | Change |
| --- | --- |
| `commands/tcw-taxonomy-init.md`, `commands/tcw-capabilities-init.md`, `commands/tcw-docs-sync-setup.md` | Deleted. |
| `scripts/session_bootstrap.sh:9`, `:45` | Comments name `tcw-setup` and its `install.md`. |
| `README.md:217`, `:227` | `tcw-plugin` → `tcw-setup`. |
| `README.md:352` | Replace the two slash commands with asking for the `tcw-setup` skill. |
| `README.md:430-432` | "Fifteen skills … Nine carry a distinct procedure" → sixteen and ten. |
| `README.md:440` | The `tcw-plugin` row becomes rows for `tcw-setup` and `tcw-configure`. |
| `README.md:470-471` | Drop the three commands from the list. |
| `docs/guide/taxonomy-and-capabilities.md:59` | As `README.md:352`. |
| `.codex-plugin/plugin.json` `longDescription` | "fifteen skills" → "sixteen skills". "tcw-plugin for installing and repairing the CLI" → "tcw-setup for setting TCW up and repairing the CLI; tcw-configure for changing a project's TCW configuration". |
| `tests/test_documentation_sync_wiring.py` | `SKILL_FILES` (`:13-19`) drops `references/setup.md`. The `COMMAND_ROUTES` entry for `tcw-docs-sync-setup` (`:23-26`) goes. The docstring at `:109-115` and the test at `:127-134`, which reads `setup.md` directly, read the `tcw-configure` skill's `references/docs-sync.md` instead. |
| `tests/test_documentation_config.py:137` | Docstring names the moved document. |
| `tests/test_plugin_manifests.py:4` | Docstring names `tcw-setup`. |
| `evals/*`, `tests/test_eval_*.py`, `tests/test_skill_lifecycle_parity.py` | Per D6. |
| `docs/taxonomy/…`, `docs/capabilities/…` | Per **Capability changes**, written with `tcw taxonomy add`, `tcw capabilities add` and `tcw capabilities set`. |
| `docs/changelogs/upcoming.md`, `docs/release-notes/upcoming.md` | Record the removed commands and skill, the two new skills, the retired capability paths and their successors, and the new taxonomy entries. |
| `2026-08-18-report-the-missing-skill-caveat-…`, `2026-08-12-separate-the-agent-plugin-…`, `2026-09-11-run-the-eval-harness-…`, `2026-09-12-configure-an-external-tracker-…` | A one-line note on each (see Risks). |

### Abstraction and harness checks

- **Abstraction litmus test.** No store operation is added or changed. Retiring
  capabilities uses `set --status Omitted` plus `Superseded by`, both existing
  operations, instead of deleting folders by hand.
- **Harness.** Every procedure is reachable by invoking a skill, which both Claude
  and Codex can do. D2 forbids depending on arguments or on context injection.

## Acceptance criteria

Check each one from the repository root after implementation.

1. `ls skills` lists exactly: `autonomous-work documentation-sync
   tcw-capabilities tcw-configure tcw-post-mortem tcw-report tcw-setup
   tcw-taxonomy tcw-triage-issues tcw-work tcw-work-stage
   tcw-work-stage-implement tcw-work-stage-plan tcw-work-stage-request
   tcw-work-stage-spec tcw-work-stage-verify`.
2. `ls skills/tcw-setup/references` lists exactly `capabilities.md install.md
   project.md taxonomy.md`, and `ls skills/tcw-configure/references` lists exactly
   `docs-sync.md projects.md stores.md tracker.md work.md`.
3. None of these exist: `skills/tcw-plugin/`, `skills/tcw-taxonomy/references/`,
   `skills/tcw-capabilities/references/`,
   `skills/documentation-sync/references/setup.md`,
   `commands/tcw-taxonomy-init.md`, `commands/tcw-capabilities-init.md`,
   `commands/tcw-docs-sync-setup.md`.
4. This command prints nothing:
   `git grep -nE 'tcw-plugin|tcw-taxonomy-init|tcw-capabilities-init|tcw-docs-sync-setup' -- . ':!docs/work' ':!docs/changelogs' ':!docs/release-notes' ':!tests/test_skill_lifecycle_parity.py'`.
   The excluded test is the one that holds the list of deleted names.
5. This command prints nothing:
   `git grep -nE 'references/(init|setup)\.md|[^/]setup\.md' -- skills commands tests`.
6. For each of `skills/tcw-setup/SKILL.md` and `skills/tcw-configure/SKILL.md`:
   - the body is at most 60 lines, counted as in
     `tests/test_skill_lifecycle_parity.py:280-282`;
   - it links every file in its own `references/`, and every relative link in it
     resolves;
   - it contains neither `$ARGUMENTS` nor `` !` ``;
   - it contains the literal text "the `tcw-configure` skill" (in `tcw-setup`) or
     "the `tcw-setup` skill" (in `tcw-configure`).
7. `skills/tcw-setup/SKILL.md` has a routing row pointing to the `tcw-configure`
   skill for each of: documentation entries, lifecycle bindings, Definition of
   Done, tracker, store locations, connected or inherited projects.
8. Compared case-insensitively:
   - `tcw-setup`'s `description` contains `missing`, `broken`, `stale`,
     `taxonomy`, and `capabilities`;
   - `tcw-configure`'s `description` contains `lifecycle`, `definition of done`,
     `documentation`, `tracker`, `store`, and `set up`.
9. Compared case-insensitively:
   - neither `description` nor `when_to_use` in `skills/tcw-taxonomy/SKILL.md`
     contains `bootstrap` or `seed`;
   - `skills/documentation-sync/SKILL.md`'s `description` does not contain
     `declares documentation entries`.
10. `skills/tcw-taxonomy/SKILL.md` and `skills/tcw-capabilities/SKILL.md` each
    contain "`tcw-setup`" and no `## Bootstrap` heading.
    `skills/tcw-work/SKILL.md`, `skills/tcw-taxonomy/SKILL.md`,
    `skills/tcw-capabilities/SKILL.md` and `skills/documentation-sync/SKILL.md`
    each contain "`tcw-configure`".
11. **Moved text arrived whole.**
    - **Renames.** `git diff --find-renames=90% --name-status <base> HEAD`, where
      `<base>` is the commit before this item's first implementation commit, shows
      `R` with a similarity of at least 90% for
      `skills/tcw-taxonomy/references/init.md → skills/tcw-setup/references/taxonomy.md`,
      `skills/tcw-capabilities/references/init.md → skills/tcw-setup/references/capabilities.md`,
      and
      `skills/documentation-sync/references/setup.md → skills/tcw-configure/references/docs-sync.md`.
    - **Partial moves.** Every non-blank line of `skills/tcw-plugin/SKILL.md:62-115`
      as of `<base>` appears verbatim in `skills/tcw-setup/references/install.md`,
      except lines naming `tcw-plugin` or the README, which the implementation
      lists in `outcome.md`. The same holds for `hooks.md:1-41` into
      `tcw-configure/references/work.md`, and for `commands.md:93-107` into
      `tcw-configure/references/tracker.md`.
12. `skills/tcw-configure/references/work.md` contains `work.lifecycle`,
    `timeout`, `dod.yaml`, `work.retain`, `work.auto-commit-transitions`,
    `work.trunk-branch`, and `work.publish-transitions`.
    `skills/tcw-configure/references/stores.md` contains `work.path`, `repository`,
    and the phrase "does not move". `skills/tcw-configure/references/projects.md`
    contains `connected-projects` and `extends`.
13. `skills/tcw-work/references/hooks.md` still contains `tcw work stage gate` and
    "`tcw serve` runs no hooks", and has no line beginning `| Role`.
    `skills/tcw-work/references/lifecycle/default/README.md` names
    `tcw-configure`.
14. **Taxonomy.**
    - `tcw taxonomy show skill` exits 0.
    - For every row of the Taxonomy table, `tcw taxonomy show <Feature path>` exits
      0, prints `kind: Feature`, and prints a `vocabulary:` line containing every
      term in that row.
    - `tcw taxonomy check` exits 0.
15. **Capabilities.**
    - For every directory `<s>` under `skills/`,
      `tcw capabilities show skills/<s>` exits 0 and prints
      `**Status:** Supported`, and a `**Feature:**` line equal to that skill's
      Feature path in the Taxonomy table.
    - For every row of the retired table, `tcw capabilities show <retired path>`
      prints `**Status:** Omitted` and `**Superseded by:** <successor>`.
    - `tcw capabilities show plugin/bootstrap-the-cli` does not print `tcw-plugin`.
    - `tcw capabilities check` prints `capabilities OK`.
16. **Evals.**
    - `evals/evals.json` has no case whose `skill` or `invokes` is `tcw-plugin`.
    - Case B5 has `skill` `cross-axis`.
    - One case's `invokes` is `tcw-setup`, and one's is `tcw-configure`.
    - B4 and B8 each have a `transcript_absent` assertion on `tcw-setup/references/`.
    - `evals/coverage.py` `PARTIAL` has key `tcw-setup` and not `tcw-plugin`.
    - For each new or changed assertion there is a test in
      `tests/test_eval_grading.py` (or a new `tests/test_eval_*.py`) grading a
      transcript that must fail it.
17. Bare `pytest`, which is how CI runs it (not `python -m pytest`), passes, and
    `tcw validate` exits 0.

## Risks

- **Setup and configuration requests still land in the wrong skill.** D1, D4 and
  ACs 7–9 remove every setup or configuration trigger found in a usage skill's
  description today. The new cases in D6 measure the weakest boundary ("set up"
  meaning configure). Until a paid run happens, the routing is a judgment, not a
  measurement.
- **The two new skills compete.** Each names the other (AC 6), and `tcw-setup`
  carries explicit redirect rows (AC 7).
- **Retired capability paths.** Nine paths become `Omitted`. Anyone reading
  `tcw capabilities list` sees them flagged `[Omitted]`, with `Superseded by`
  naming the replacement. Only one live document links a retired path, and D7
  fixes it.
- **Folding capabilities loses detail.** `skills/tcw-work` absorbs four
  capabilities. The body must carry each one's behavior, and AC 15 only checks
  status and links, so this is left to review.
- **Collision with the active tracker item.**
  `2026-09-12-configure-an-external-tracker-and-read-its-tickets` is `active`, and
  its tracker text is on `main` in `commands.md:83-107`. This item moves
  `:93-107`, so any further edit that item makes to that text conflicts. Order:
  implement this item after that one completes, or rebase the move onto its final
  text. The note D7 adds to it says so.
- **Collision with the eval run.**
  `2026-09-11-run-the-eval-harness-and-act-on-what-it-finds` covers B5 and the
  axis B assertions. This item should land first, so the paid run measures what
  ships, and its note lists the new and changed cases.
- **Other open items cite files that move.**
  - `2026-08-18-…` quotes `hooks.md:83`. That text stays, but its line number
    changes.
  - `2026-08-12-…`'s `plan.md` names `tcw-plugin` paths that were already stale
    (`docs/changelogs/v2.0.3.md:150-152`).
  - Each gets a one-line note.
- **Size.** This roughly triples the item's scope as first estimated, and
  `state.yaml` still says `effort: medium`. Re-estimating is a plan-stage task.

## Notes

- **Sibling defect, separate change:** `skills/tcw-capabilities/SKILL.md:107`
  tells the agent to "use `remove`" for a standalone local capability, but
  `tcw capabilities` has no such command. The same gap is why this item retires
  capabilities rather than deleting them. It warrants its own item: add the
  command, or fix the text. That item is not part of this one.
- **Judgment, flagged for review:** `work.tags` and `id` stay out of
  `tcw-configure` (Non-goals).
- **Judgment, flagged for review:** nesting the five per-stage Features under
  `tcw-work-stage-skill`. It rests on "Nest specializations under a parent"; the
  per-stage skills are the generic one with a stage built in.
- **Not verified:** that `tcw taxonomy add --parent` accepts a Feature as the
  parent of a Feature. Existing nesting is Vocabulary under Vocabulary only. If it
  refuses, the five stage Features are added flat, and AC 14's paths drop the
  `tcw-work-stage-skill/` prefix. The plan must check this first.
- **Assumption:** that `tcw-plugin` is mostly opened when the CLI is broken. The
  design doesn't depend on it.
- **Search for other places to change:**
  - The search for removed names and moved documents covered the whole
    repository: `git grep` for the four names, and for `references/init.md`,
    `references/setup.md`, `references/hooks.md` and bare `setup.md`. It found the
    three places the first review listed, which D4 and D7 now include. It was
    narrowed only to exclude history.
  - The search for configuration keys covered every key the CLI reads in `tcw/`
    (`get("…")` calls in `tcw/store/fs.py`, `tcw/store/base.py` and
    `tcw/store/project.py`), and every skill document naming one.
