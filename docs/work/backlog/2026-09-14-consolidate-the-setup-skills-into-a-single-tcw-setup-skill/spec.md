# Spec — Separate setting up TCW from using it: `tcw-setup`, `tcw-config`, and a Feature per skill

> The item's title still says "a single tcw-setup skill". The requester revised
> that to two skills during this stage (`initial-request.md`, revision note at
> the top). Retitling is a plan-stage task.

## Capability changes

Planned ledger and taxonomy changes only; nothing is written at this stage.
Taxonomy comes first, because `tcw capabilities set` refuses a `Feature` that does
not resolve yet (`skills/tcw-capabilities/SKILL.md`, "ordering is now
load-bearing").

### Taxonomy

- **New Vocabulary — `skill`.** "An agent skill the TCW plugin ships: a document an
  agent loads to learn how to do one kind of TCW task." No such term exists
  today. `tcw taxonomy search` for `skill`, `plugin`, and `setup` finds only the
  unrelated `configurable-work-lifecycle` Feature.
- **Sixteen new Features, one per top-level skill** (table below). Each names the
  vocabulary `skill`, plus one domain term where one clearly applies. Every
  Feature slug is the skill's directory name followed by `-skill`, so the mapping
  from skill to Feature can be checked mechanically.

### Capabilities

```yaml
new:
    - skills/tcw-setup
    - skills/tcw-config
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
    - plugin/bootstrap-the-cli
    - taxonomy/bootstrap-the-taxonomy
    - capabilities/bootstrap-the-capabilities
    - plugin/report-an-issue-upstream
    - plugin/run-a-post-mortem
    - plugin/triage-github-issues
    - plugin/work-lifecycle
    - work/consolidate-plans
    - work/search-the-work-items
```

**New:** a `skills/` namespace with one capability per skill. Each capability's
path is the skill's directory name, its `Feature` is that skill's Feature, and its
`Subject` is `skill`. All are seeded `Missing` at planning and flipped to
`Supported` at completion. Each description follows the requester's pattern:
"Offer a skill dedicated to instructing agents how to …".

**Changed — Feature links.** Each of these existing capabilities describes what a
user does *through* one skill and has no `Feature` today, so it gains
`Feature=<that skill's Feature>`. The path and the behavior it describes don't
change.

| Capability | Gains `Feature` |
| --- | --- |
| `plugin/bootstrap-the-cli` | `tcw-setup-skill` |
| `taxonomy/bootstrap-the-taxonomy` | `tcw-setup-skill` |
| `capabilities/bootstrap-the-capabilities` | `tcw-setup-skill` |
| `plugin/report-an-issue-upstream` | `tcw-report-skill` |
| `plugin/run-a-post-mortem` | `tcw-post-mortem-skill` |
| `plugin/triage-github-issues` | `tcw-triage-issues-skill` |
| `plugin/work-lifecycle` | `tcw-work-skill` |
| `work/consolidate-plans` | `tcw-work-skill` (the procedure lives at `skills/tcw-work/references/procedures/consolidate-plans.md`) |
| `work/search-the-work-items` | `tcw-work-skill` (`skills/tcw-work/references/procedures/search.md`) |

**Changed — wording.**
- `plugin/bootstrap-the-cli` names "the `tcw-plugin` setup" and "the `tcw-plugin`
  skill"; both become `tcw-setup`.
- `taxonomy/bootstrap-the-taxonomy` and `capabilities/bootstrap-the-capabilities`
  open "I run `/tcw-taxonomy-init`" and "I run `/tcw-capabilities-init`". Those
  commands are deleted, so each becomes "I ask my agent to …, and the `tcw-setup`
  skill …".

**Deliberately not touched:**
- `work/run-a-lifecycle-stage` and `work/configure-the-work-lifecycle` already
  carry `Feature: configurable-work-lifecycle`, and `Feature` holds a single value.
- `work/declare-which-documents-track-which-changes`,
  `work/read-the-documentation-gate-for-a-change`, and
  `work/customize-the-definition-of-done` describe CLI and configuration-file
  behavior, not a skill.
- `plugin/install-as-a-plugin` describes the plugin, not a skill.
- No existing capability moves path. Paths are stable addresses, and "maps neatly"
  is met by the `Feature` link rather than by renaming.

## Problem

Setup material is spread across four skills and three slash commands. Nothing
about the names says which skills set TCW up, which change its configuration, and
which use it:

| Setup or configuration material | Where it lives today |
| --- | --- |
| Installing or repairing the `tcw` CLI | `skills/tcw-plugin/SKILL.md:62-115` |
| Starting a taxonomy | `commands/tcw-taxonomy-init.md:5` → `skills/tcw-taxonomy/references/init.md` (61 lines) |
| Starting a capabilities ledger | `commands/tcw-capabilities-init.md:5` → `skills/tcw-capabilities/references/init.md` (32 lines) |
| Declaring documentation entries | `commands/tcw-docs-sync-setup.md:7` → `skills/documentation-sync/references/setup.md` (62 lines) |
| Binding instructions to lifecycle stages | `skills/tcw-work/references/hooks.md:1-41` |
| The Definition of Done file | One clause, `skills/tcw-work/references/transitions.md:112` |
| `tcw init`, `tcw provision`, where each store lives | No skill document. Only refusal-handling text in usage skills (`skills/tcw-taxonomy/SKILL.md:30-36`, `skills/tcw-capabilities/SKILL.md:17-24`, `skills/tcw-work/references/commands.md:150-210`); the user guides are `README.md:336-351` and `docs/guide/multi-repo.md:199-230` |

Five concrete consequences:

1. **Setup requests go to usage skills.** `tcw-taxonomy`'s `description` and
   `when_to_use` list "bootstrapping a taxonomy from an existing codebase"
   (`skills/tcw-taxonomy/SKILL.md:3-4`). A setup request therefore loads the
   whole taxonomy usage skill just to follow a pointer to `references/init.md`
   (`:104-107`).
2. **Two ways to do one thing.** Each setup procedure is reachable through a slash
   command or through a usage skill's pointer. Codex has no slash commands, so a
   Codex user only has the second way.
3. **`tcw-plugin` is two unrelated things in one skill.** It is a map of the other
   skills (`skills/tcw-plugin/SKILL.md:12-60`) plus CLI installation (`:62-115`).
   Its name describes neither.
4. **Nothing explains setting up a repository or changing where its stores live.**
   It is only explained at the moment a command refuses.
5. **The skills are invisible to the project's own taxonomy.** No Vocabulary term
   or Feature describes a skill, so the capabilities that a skill delivers
   (`plugin/report-an-issue-upstream`, `plugin/run-a-post-mortem`, …) point at no
   Feature, and some skills have no capability that mentions them at all —
   `autonomous-work` is one.

## Goals

1. **`tcw-setup`** is the one skill for getting TCW working where it doesn't
   work yet: a project that doesn't use TCW, a machine that lacks the CLI or a
   store, or a CLI that is missing, broken, or out of date.
2. **`tcw-config`** is the one skill for changing the configuration of a project
   that already uses TCW.
3. Both skills' `SKILL.md` files only route. They say which reference document
   covers which situation, and the reference documents hold the instructions.
4. The usage skills keep their names. They stop presenting themselves as setup or
   configuration skills, and each keeps one line pointing to the right new skill.
5. There is one way into each procedure, and it works the same under Claude and
   Codex.
6. Existing setup and configuration material is moved, not rewritten.
7. Every top-level skill has a taxonomy Feature and a capability linked to it.

## Non-goals

- Renaming or restructuring any usage skill beyond removing setup and
  configuration material.
- Changing what `tcw-report`, `tcw-triage-issues`, `tcw-post-mortem`,
  `autonomous-work`, or the six `tcw-work-stage*` skills say. They gain a Feature
  and a capability only.
- Any change to the `tcw` CLI, including what `tcw init` prints.
- Stub commands or a stub `tcw-plugin` under the old names. The requester decided
  nobody else uses TCW yet.
- Rewriting history: completed work items under `docs/work/`, and changelogs and
  release notes of past versions, keep the names they were written with.
- Setup and configuration text for the external tracker (Jira). The active item
  `2026-08-04-supplement-filesystem-tcw-work-with-an-external-tracker-bridge`
  is building that configuration now (see Risks).
- Federation (`tcw taxonomy extends`, `tcw capabilities extends`) and the tag
  vocabulary (`skills/tcw-work/references/tags.md`). Both are done with ordinary
  commands during use, so they stay in their usage skills.
- Separating the plugin from the Python source
  (`2026-08-12-separate-the-agent-plugin-from-the-python-cli-source`), and
  refining skills against eval results
  (`2026-09-11-refine-the-plugin-skills-and-lifecycle-prompts-against-the-eval-findings`).
- Running the paid eval harness. Cases are authored and their assertions
  mutation-checked (deliberately broken to confirm they go red); running them is
  not part of this item.

## Design

### The skill set after this change

`skills/` goes from **fifteen** skills to **sixteen**: `tcw-plugin` is removed,
and `tcw-setup` and `tcw-config` are added. The grouping is for the reader only;
it is not a folder structure.

| Group | Skill | Taxonomy Feature (slug · name) | Extra Vocabulary | Change in this item |
| --- | --- | --- | --- | --- |
| **Setting up** | `tcw-setup` | `tcw-setup-skill` · TCW Initialization Skill | `node` | **new** — install half of `tcw-plugin`, both `init.md`s, new `project.md` |
| **Configuring** | `tcw-config` | `tcw-config-skill` · TCW Configuration Skill | `node` | **new** — configuration half of `hooks.md`, docs-sync `setup.md`, new `stores.md` |
| **Using TCW** | `tcw-work` | `tcw-work-skill` · TCW Work Skill | `work-item` | loses the configuration half of `references/hooks.md`; points to `tcw-config` |
| | `tcw-taxonomy` | `tcw-taxonomy-skill` · TCW Taxonomy Skill | `vocabulary` | loses `references/init.md` and "bootstrapping" from its description; points to `tcw-setup` |
| | `tcw-capabilities` | `tcw-capabilities-skill` · TCW Capabilities Skill | `capability` | loses `references/init.md`; points to `tcw-setup` |
| | `documentation-sync` | `documentation-sync-skill` · TCW Documentation Sync Skill | `work-item/lifecycle-stage` | loses `references/setup.md`; points to `tcw-config` |
| | `tcw-work-stage` | `tcw-work-stage-skill` · TCW Work Stage Skill | `work-item/lifecycle-stage` | Feature and capability only |
| | `tcw-work-stage-request` | `tcw-work-stage-request-skill` · TCW Request Stage Skill | `work-item/lifecycle-stage` | Feature and capability only |
| | `tcw-work-stage-spec` | `tcw-work-stage-spec-skill` · TCW Spec Stage Skill | `work-item/lifecycle-stage` | Feature and capability only |
| | `tcw-work-stage-plan` | `tcw-work-stage-plan-skill` · TCW Plan Stage Skill | `work-item/lifecycle-stage` | Feature and capability only |
| | `tcw-work-stage-implement` | `tcw-work-stage-implement-skill` · TCW Implement Stage Skill | `work-item/lifecycle-stage` | Feature and capability only |
| | `tcw-work-stage-verify` | `tcw-work-stage-verify-skill` · TCW Verify Stage Skill | `work-item/lifecycle-stage` | Feature and capability only |
| | `tcw-triage-issues` | `tcw-triage-issues-skill` · TCW Issue Triage Skill | `work-item/intake` | Feature and capability only |
| | `tcw-post-mortem` | `tcw-post-mortem-skill` · TCW Post-Mortem Skill | `work-item/lifecycle-stage` | Feature and capability only |
| | `autonomous-work` | `autonomous-work-skill` · TCW Autonomous Work Skill | `work-item` | Feature and capability only |
| **Reporting to TCW** | `tcw-report` | `tcw-report-skill` · TCW Report Skill | — | Feature and capability only |
| *(removed)* | ~~`tcw-plugin`~~ | — | — | install half → `tcw-setup`; skill map deleted (D5) |

The resulting tree, showing only folders this item changes in detail:

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
  tcw-config/                    # new
    SKILL.md                     # routing only
    references/
      work.md                    # lifecycle bindings; Definition of Done
      docs-sync.md               # documentation entries
      stores.md                  # where each store lives; a store in another repository
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
  tcw-work/                      # references/hooks.md trimmed; otherwise unchanged
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

- **`tcw-setup` covers getting TCW working where it doesn't yet**, including on
  an existing TCW project. It covers a new machine that needs the CLI or a
  declared store (`tcw provision`), and a CLI that is missing, broken, or stale.
  The requester's wording was "a project that does not currently use TCW". The
  CLI and store cases are included because each is the same kind of situation
  ("TCW doesn't work here yet"), and neither changes any configuration.
- **`tcw-config` covers changing a working project's configuration**: lifecycle
  bindings, the Definition of Done, documentation entries, and where each store
  lives.
- **First-time setup that also wants configuration** ends at `project.md`'s last
  step, which hands off to `tcw-config` by name. No procedure is written twice.

### D2 — Each `SKILL.md` routes and nothing else

Each body holds:

- A short statement of what the skill is for.
- A statement of what the *other* skill is for, so a request that reached the
  wrong one gets sent on.
- **A routing table** with columns *situation* → *document*: one row per
  reference document, with the situation described in the user's words.

`tcw-setup`'s body also states one rule on order: install, then project, then
taxonomy before capabilities. That rule exists today at
`skills/tcw-capabilities/references/init.md:7-9`.

**Size limit:** each body (everything after the closing `---` of the frontmatter)
is at most **60 lines**, counted the way `tests/test_skill_lifecycle_parity.py:276-285`
counts `tcw-work`'s body.

**Frontmatter:**

- `tcw-setup`'s `description` names: a project that doesn't use TCW, a `tcw` that
  is missing, broken, or stale, obtaining a declared store, and starting a
  taxonomy or capabilities ledger. The broken-CLI trigger must stay explicit,
  because it is the trigger `tcw-plugin` carries today
  (`skills/tcw-plugin/SKILL.md:3-4`).
- `tcw-config`'s `description` names: changing configuration, lifecycle bindings,
  the Definition of Done, documentation entries, and store locations.
- Both fill in `when_to_use`, as the other skills do.
- `allowed-tools` (the Claude list of tool calls a skill may make without asking
  first) is the union of the lists on the skills each one takes material from.
  Nothing outside those lists is added.
  - `tcw-setup`: `skills/tcw-plugin/SKILL.md:5` plus `Read, Grep, Glob` from
    `skills/tcw-taxonomy/SKILL.md:5`.
  - `tcw-config`: `skills/tcw-work/SKILL.md:5`, which is where `hooks.md` comes
    from. `documentation-sync` declares none.
- `compatibility`, `metadata`, and `license` on `tcw-setup` carry over from
  `skills/tcw-plugin/SKILL.md:6-9`. `tcw-config` carries `metadata` and `license`.

**Harness rule.** Under Claude, either skill can be invoked with a hint
(`/tcw:tcw-setup taxonomy`). Skill arguments are Claude-only, so a hint is a
convenience, never the route. The routing table must let a model pick the right
document from the request alone. Neither body may depend on `$ARGUMENTS` or on
dynamic context injection (`` !`cmd` ``, which under Claude runs a command and
inserts its output into the skill).

### D3 — Where each reference document comes from

| New document | Source | How |
| --- | --- | --- |
| `tcw-setup/references/install.md` | `skills/tcw-plugin/SKILL.md:62-115` | **Moved.** Only wording that names the old skill changes. |
| `tcw-setup/references/project.md` | *(none)* | **New, short.** `tcw init --id` and the per-component `init`s (`README.md:336-351`); `tcw provision` for a store declared in another repository; `tcw validate` as the closing check; hand-off to `tcw-config`. |
| `tcw-setup/references/taxonomy.md` | `skills/tcw-taxonomy/references/init.md` | **Moved** with `git mv`. |
| `tcw-setup/references/capabilities.md` | `skills/tcw-capabilities/references/init.md` | **Moved** with `git mv`. Line 9's "point the user at `/tcw-taxonomy-init`" becomes a pointer to `taxonomy.md`. |
| `tcw-config/references/work.md` | `skills/tcw-work/references/hooks.md:1-41`, `:97-98`; `docs/work/dod.yaml` | **Moved:** binding shape, roles, kinds, `when:`, and the note that `tcw-config.yaml` is trusted like any other file. **New text:** how to set the Definition of Done, drawn from capability `work/customize-the-definition-of-done`. |
| `tcw-config/references/docs-sync.md` | `skills/documentation-sync/references/setup.md` | **Moved** with `git mv`. Its pointers to "`SKILL.md`'s Trigger Reference" (`:34`, `:37`) name the `documentation-sync` skill explicitly, because they now point from one skill to another. |
| `tcw-config/references/stores.md` | *(none)* | **New, short.** `taxonomy.path` / `capabilities.path` / `work.path`, and a `repository` block for a store kept in another Git repository, drawn from `docs/guide/multi-repo.md:199-230`. Ends with `tcw validate` and, where a `repository` block was added, `tcw provision`. How stores behave at runtime stays in `tcw-work`'s `commands.md` (D4). |

A pointer from one skill to another names the **skill** and the document ("the
`tcw-setup` skill's `references/taxonomy.md`"), matching how commands already
refer to skill files (`commands/tcw-taxonomy-init.md:5`). Reference documents are
self-contained: they do not send an agent into `docs/guide/`, which a plugin
install is not guaranteed to carry once the plugin and the Python source are
separated.

### D4 — What each usage skill loses and keeps

- **`tcw-taxonomy`**:
  - Remove "bootstrapping a taxonomy from an existing codebase" from `description`
    and `when_to_use` (`SKILL.md:3-4`).
  - Remove "See `tcw-plugin` for the cross-skill map." (`:24-25`).
  - Replace `## Bootstrap` (`:104-107`) with one line pointing to `tcw-setup`.
  - The refusal text for a store that isn't provisioned (`:30-36`) stays, because
    an agent needs it when a command refuses mid-use.
- **`tcw-capabilities`**:
  - Replace `## Bootstrap` (`SKILL.md:117-120`) with one line pointing to
    `tcw-setup`.
  - The refusal text at `:17-24` stays.
- **`tcw-work`**:
  - Delete "`tcw-plugin` maps the skills." (`SKILL.md:19-20`).
  - `:55` keeps its pointer to `hooks.md` for what bindings do while a stage runs,
    and adds a pointer to `tcw-config` for declaring them.
  - `references/hooks.md` keeps "The three verbs" (`:43-66`), "What runs, and what
    does not" (`:68-84`), and "Two limits worth knowing" (`:86-95`).
  - The body stays within its existing 60-line limit.
- **`documentation-sync`**:
  - The three references to `references/setup.md` (`SKILL.md:15`, `:29`, and the
    table row at `:98`) point to `tcw-config`'s `docs-sync.md` instead.
  - The skill otherwise stays whole, since it also serves projects that don't use
    TCW. The same plugin ships both skills, so `tcw-config` is present wherever
    `documentation-sync` is.

### D5 — The skill map is deleted

`skills/tcw-plugin/SKILL.md:12-60` is not moved anywhere. Everything it says is
already said by a skill that stays:

| What the map says | Already said at |
| --- | --- |
| The order `Vocabulary → Features → Capabilities → Work` | `skills/tcw-work/SKILL.md:17`, `skills/tcw-taxonomy/SKILL.md:20` |
| Capabilities point loosely at a `Subject` and strongly at a `Feature` | `skills/tcw-capabilities/SKILL.md:27` |
| The axes point forward; taxonomy never points back | `skills/tcw-taxonomy/SKILL.md:23-24` |
| `tcw-work` runs the capability check for product changes | `skills/tcw-work/SKILL.md:18-19` |
| `tcw-report` sends feedback to TCW; `tcw-triage-issues` reads the user's own issues | both skills' `description` fields |
| Which axis skill handles which kind of request | each axis skill's `description`, and `tcw-taxonomy` and `tcw-capabilities` name their neighbours (`:3`) |

### D6 — Eval coverage is rebuilt

`tests/test_eval_coverage.py` fails unless every shipped skill is named by an eval
case or listed in `EXCLUSIONS` in `evals/coverage.py`.

- **Removed:** case `B5` (`evals/evals.json:592-622`). It measures the skill map,
  which no longer exists. The `PARTIAL` entry for `tcw-plugin`
  (`evals/coverage.py:46-57`) goes with it.
- **Added:** at least one case whose `invokes` is `tcw-setup`, and at least one
  whose `invokes` is `tcw-config`, each with `with-skill` and `no-skill` arms.
  Every assertion is mutation-checked before it is trusted, as
  `CLAUDE.md` § Measuring the skill layer requires.
- **The route CLI install/repair stays unmeasured.** Faking a broken install
  inside a test session is unsafe and would measure the fake, as
  `evals/coverage.py:53-56` already records. `PARTIAL` records that for
  `tcw-setup`.
- **Which routes get cases is an open question for the spec's reviewers.** The
  requester left it open. Candidates, and what each could check mechanically:
  - Documentation entries (`tcw-config`): `tcw work docs --json` reports
    `source: config` with the declared entry; `tcw validate` exits 0.
  - Lifecycle binding (`tcw-config`): `tcw work lifecycle` lists the binding;
    `tcw validate` exits 0.
  - Project initialization (`tcw-setup`): `tcw-config.yaml` exists with the given
    ID; `tcw validate` exits 0.
  - Taxonomy bootstrap (`tcw-setup`): the procedure asks the user to refine a
    draft, which a non-interactive eval can't answer, so its checks are weaker.
  - Routing (both): a request meant for one skill reaches that skill's router
    and not the other's.

### D7 — Everything else that names the removed things, or counts skills

| File | Change |
| --- | --- |
| `commands/tcw-taxonomy-init.md`, `commands/tcw-capabilities-init.md`, `commands/tcw-docs-sync-setup.md` | Deleted. |
| `scripts/session_bootstrap.sh:9`, `:45` | The comments name `tcw-setup` and its `install.md`. |
| `README.md:217`, `:227` | `tcw-plugin` → `tcw-setup`. |
| `README.md:352` | Replace the two slash commands with asking for the `tcw-setup` skill. |
| `README.md:430-432` | "Fifteen skills … Nine carry a distinct procedure" → sixteen and ten. |
| `README.md:440` | The `tcw-plugin` row becomes two rows, `tcw-setup` and `tcw-config`. |
| `README.md:470-471` | Drop the three commands from the list. |
| `docs/guide/taxonomy-and-capabilities.md:59` | As `README.md:352`. |
| `.codex-plugin/plugin.json` `longDescription` | "fifteen skills" → "sixteen skills". "tcw-plugin for installing and repairing the CLI" → "tcw-setup for setting TCW up and repairing the CLI; tcw-config for changing a project's TCW configuration". |
| `tests/test_documentation_sync_wiring.py:13-19`, `:23-26` | `SKILL_FILES` drops `references/setup.md`. The `COMMAND_ROUTES` entry for `tcw-docs-sync-setup` goes; the `tcw-cut-version` entry stays. |
| `tests/test_plugin_manifests.py:4` | The docstring names `tcw-setup`. |
| `evals/evals.json`, `evals/coverage.py` | Per D6. |
| `docs/taxonomy/…`, `docs/capabilities/…` | Per **Capability changes**, written with `tcw taxonomy add` and `tcw capabilities add` / `set`, never by hand. |
| `docs/changelogs/upcoming.md`, `docs/release-notes/upcoming.md` | Record the removed commands and skill, the two new skills, and the new taxonomy and capability entries. |

### Abstraction and harness checks

- **Abstraction litmus test.** No store operation is added, changed, or removed.
  Taxonomy and capability entries are written through the existing commands.
- **Harness.** Every procedure is reachable by invoking a skill, which both Claude
  and Codex can do. Deleting three slash commands removes a Claude-only way in
  without removing anything from either harness. D2 forbids depending on
  arguments or on context injection.

## Acceptance criteria

Each is checked from the repository root after implementation.

1. `ls skills` lists exactly: `autonomous-work documentation-sync
   tcw-capabilities tcw-config tcw-post-mortem tcw-report tcw-setup tcw-taxonomy
   tcw-triage-issues tcw-work tcw-work-stage tcw-work-stage-implement
   tcw-work-stage-plan tcw-work-stage-request tcw-work-stage-spec
   tcw-work-stage-verify`.
2. `ls skills/tcw-setup/references` lists exactly `capabilities.md install.md
   project.md taxonomy.md`. `ls skills/tcw-config/references` lists exactly
   `docs-sync.md stores.md work.md`.
3. None of these exist: `skills/tcw-plugin/`,
   `skills/tcw-taxonomy/references/`, `skills/tcw-capabilities/references/`,
   `skills/documentation-sync/references/setup.md`,
   `commands/tcw-taxonomy-init.md`, `commands/tcw-capabilities-init.md`,
   `commands/tcw-docs-sync-setup.md`.
4. `git grep -nE 'tcw-plugin|tcw-taxonomy-init|tcw-capabilities-init|tcw-docs-sync-setup' -- . ':!docs/work' ':!docs/changelogs' ':!docs/release-notes'`
   prints nothing. `docs/changelogs/upcoming.md` names each of the four as
   removed.
5. For each of `skills/tcw-setup/SKILL.md` and `skills/tcw-config/SKILL.md`:
   - the body, counted as in `tests/test_skill_lifecycle_parity.py:280-282`, is
     at most 60 lines;
   - it links every file in its own `references/`, and every relative link in it
     resolves;
   - it contains neither `$ARGUMENTS` nor `` !` ``;
   - it names the other of the two skills.
6. Compared case-insensitively:
   - the `description` of `tcw-setup` contains each of `missing`, `stale`,
     `taxonomy`, and `capabilities`;
   - the `description` of `tcw-config` contains each of `lifecycle`,
     `definition of done`, `documentation`, and `store`.
7. Neither `description` nor `when_to_use` in `skills/tcw-taxonomy/SKILL.md`
   contains `bootstrap`, compared case-insensitively.
8. `skills/tcw-taxonomy/SKILL.md` and `skills/tcw-capabilities/SKILL.md` each
   contain `tcw-setup` and no `## Bootstrap` heading.
   `skills/tcw-work/SKILL.md` and `skills/documentation-sync/SKILL.md` each
   contain `tcw-config`.
9. `git log --follow --oneline` on each of `skills/tcw-setup/references/taxonomy.md`,
   `skills/tcw-setup/references/capabilities.md`, and
   `skills/tcw-config/references/docs-sync.md` reaches commits made before this
   item. That is, git detects each as a rename rather than a new file.
10. Content arrived whole:
    - `skills/tcw-setup/references/install.md` contains `dir_info.editable` and
      `pipx install tcw-cli`;
    - `skills/tcw-config/references/work.md` contains `blob:`, `file:`,
      `generate:`, `builtin:`, `skill:`, `when:`, and `dod.yaml`;
    - `skills/tcw-config/references/stores.md` contains `work.path` and
      `repository`.
11. `skills/tcw-work/references/hooks.md` still contains `tcw work stage gate`
    and "`tcw serve` runs no hooks", and no longer contains the line beginning
    `| Role`.
12. For every directory `<s>` under `skills/`:
    - `tcw taxonomy show <s>-skill` exits 0 and prints `kind: Feature` and a
      `vocabulary:` line containing `skill`;
    - `tcw capabilities show skills/<s>` exits 0 and prints
      `**Feature:** <s>-skill` and `**Status:** Supported`.
13. `tcw capabilities show` prints `**Feature:**` with the value given in the
    Feature-links table for each of the nine changed capabilities. The three
    reworded ones print none of the four removed names.
14. `evals/evals.json` has no case whose `skill` or `invokes` is `tcw-plugin`, and
    has at least one case whose `invokes` is `tcw-setup` and one whose `invokes`
    is `tcw-config`. `evals/coverage.py` `PARTIAL` has no `tcw-plugin` key.
15. Bare `pytest` (not `python -m pytest`) passes, which is how CI runs it.
16. `tcw validate` exits 0, `tcw taxonomy check` exits 0, and
    `tcw capabilities check` prints `capabilities OK`.

## Risks

- **Setup and configuration requests still land in usage skills.** If a usage
  skill's description keeps describing setup or configuration, the model keeps
  choosing it. AC 7 covers the one description that does so today. Reviewers
  should read the other descriptions for the same problem.
- **The two new skills compete with each other.** "Set up documentation entries"
  says *set up* but belongs to `tcw-config` under D1. Each router naming the other
  (AC 5) is the fallback. Whether the descriptions separate cleanly enough is a
  judgment for review, or for an eval case of the "routing" kind in D6.
- **A Codex user reaches a router with no hint.** D2 and AC 5 make the routing
  table, not an argument, carry the choice.
- **The taxonomy grows by seventeen entries and the ledger by sixteen.** That is
  the requester's decision. The risk is naming: sixteen Feature names are
  proposed in the Design table. Once written they become stable IDs other
  entries point at, so reviewers should settle the names before `plan`.
- **Other open work items cite files that move.**
  - `2026-08-18-report-the-missing-skill-caveat-from-tcw-work-lifecycle-rather-than-the-skill`
    quotes `skills/tcw-work/references/hooks.md:83`. That text stays in
    `hooks.md`, but its line number shifts.
  - `2026-08-12-separate-the-agent-plugin-from-the-python-cli-source` names
    `skills/tcw-plugin/…` throughout its `plan.md`. Those paths were already stale
    (`docs/changelogs/v2.0.3.md:150-152`), and this item makes them more so.
  - Implementation adds a one-line note to each item rather than rewriting its
    documents.
- **The external tracker item adds configuration at the same time.** If it lands
  first, `tcw-config` gains a routing row for its setup text. If this item lands
  first, a note on the bridge item says its configuration instructions belong in
  `tcw-config`.
- **Material lost in moving.** AC 9 and AC 10 check that the moved documents
  arrive whole and keep their history. `project.md`, `stores.md`, and the
  Definition of Done text in `work.md` are new writing, and get reviewed as such.

## Notes

- **Open for the spec's reviewers:** which setup and configuration routes get
  eval cases (D6). The requester left this open deliberately.
- **Open for the spec's reviewers:** the sixteen Feature names and the extra
  vocabulary term chosen for each (Design table). The requester supplied two
  names, "TCW Initialization Skill" and "TCW Configuration Skill"; the other
  fourteen follow that pattern and are proposals.
- **A judgment, flagged:** D1 puts CLI repair and `tcw provision` in `tcw-setup`,
  although the requester's wording for that skill was "a project that does not
  currently use TCW".
- **Assumption, not verified:** that `tcw-plugin` is mostly opened when the CLI is
  broken. This rests on the skill's own description and on the automatic install
  covering the ordinary case; no usage data was checked. The design doesn't
  depend on it, because the broken-CLI trigger stays either way.
- **Sweep for other places to change.** The search for the removed names covered
  the whole repository: AC 4's command, plus manifests, hooks, scripts, tests,
  evals, the ledger, and the taxonomy. It was narrowed only to exclude history
  (`docs/work/`, and changelogs and release notes of past versions), which is a
  non-goal. The search for places that count skills found `README.md:430-432`
  and `.codex-plugin/plugin.json`; `tests/test_plugin_manifests.py` checks the
  latter.
