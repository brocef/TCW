# Spec — Separate setting up and configuring TCW from using it: `tcw-setup`, `tcw-configure`, and one Feature and capability per skill

> **About this spec**
>
> - **The item's title is out of date.** It still says "a single tcw-setup skill".
>   The requester revised the request several times during this stage
>   (`initial-request.md`, revision notes 1–15 at the top). Retitling is a
>   plan-stage task.
> - **A large change is acceptable**, because the goal is cleanup.
> - **Reviews so far.** Two multi-review rounds: an adversarial reviewer, Codex,
>   and the local model. Revision notes 13–15 (deleting the per-stage skills, the
>   `tcw-extras-` and `tcw-commands-` prefixes, and removing slash commands) came
>   after them and have not been reviewed.
> - **Dependency.** This item is blocked by
>   `2026-09-14-delete-a-capability-with-tcw-capabilities-rm`, which must land
>   first.

## Capability changes

Planned ledger and taxonomy changes only. Nothing is written at this stage.

**Order when writing:**

1. Vocabulary.
2. Features. `tcw taxonomy add` refuses a Feature naming vocabulary that isn't
   registered (`skills/tcw-taxonomy/SKILL.md:57-67`).
3. New capabilities, with their `Feature`. `set` refuses a `Feature` that doesn't
   resolve (`skills/tcw-capabilities/SKILL.md:55-63`).
4. Deletion of the capabilities they replace.

### Taxonomy

**New Vocabulary — `skill`.** "An agent skill: a document an agent loads to learn
how to do one kind of task. The TCW plugin ships some, and a project can bind its
own to lifecycle stages."

- It is deliberately general, because `configurable-work-lifecycle` already uses
  "agent skills" to mean a project's own skills.
- No term named `skill` exists today.

**Fifteen new Features, one per top-level skill.**

- **Slugs.** Each slug is the skill's directory name plus `-skill`, set with `-s`.
  Without `-s`, "TCW Initialization Skill" would get the slug
  `tcw-initialization-skill`.
- **Vocabulary.** Each Feature names `skill` plus every existing term it operates
  on; `--vocab` can be repeated.
- **Related Features.** Where a Feature overlaps an existing one, it gets a
  `relatesTo` link, followed by `tcw taxonomy check`. This is the taxonomy skill's
  documented hand edit (`:116`).
- **Descriptions.** A description names the interaction area only, never behavior
  (`:76-78`).

| Skill | Feature path | Feature name | Vocabulary | `relatesTo` |
| --- | --- | --- | --- | --- |
| `tcw-setup` | `tcw-setup-skill` | TCW Initialization Skill | `skill`, `cli`, `node`, `store` | `provisioned-component-stores` |
| `tcw-configure` | `tcw-configure-skill` | TCW Configuration Skill | `skill`, `node`, `store`, `work-item/lifecycle-hook`, `work-item/definition-of-done` | `configurable-work-lifecycle`, `configurable-component-store-location`, `external-work-tracker`, `connected-project-registry` |
| `tcw-work` | `tcw-work-skill` | TCW Work Skill | `skill`, `work-item`, `work-item/transition` | `work-inbox` |
| `tcw-taxonomy` | `tcw-taxonomy-skill` | TCW Taxonomy Skill | `skill`, `vocabulary`, `feature` | `taxonomy-feature-registry` |
| `tcw-capabilities` | `tcw-capabilities-skill` | TCW Capabilities Skill | `skill`, `capability` | `capability-feature-association` |
| `documentation-sync` | `documentation-sync-skill` | TCW Documentation Sync Skill | `skill`, `work-item/lifecycle-stage` | — |
| `tcw-work-stage` | `tcw-work-stage-skill` | TCW Work Stage Skill | `skill`, `work-item/lifecycle-stage` | `configurable-work-lifecycle` |
| `tcw-extras-triage-issues` | `tcw-extras-triage-issues-skill` | TCW Extras Issue Triage Skill | `skill`, `work-item/intake` | `work-inbox` |
| `tcw-post-mortem` | `tcw-post-mortem-skill` | TCW Post-Mortem Skill | `skill`, `work-item/lifecycle-stage` | — |
| `tcw-extras-autonomous-work` | `tcw-extras-autonomous-work-skill` | TCW Extras Autonomous Work Skill | `skill`, `work-item` | — |
| `tcw-extras-report` | `tcw-extras-report-skill` | TCW Extras Report Skill | `skill` | — |
| `tcw-commands-plan-work` | `tcw-commands-plan-work-skill` | TCW Plan Work Command Skill | `skill`, `work-item`, `work-item/lifecycle-stage` | — |
| `tcw-commands-drive-work-to-completion` | `tcw-commands-drive-work-to-completion-skill` | TCW Drive Work to Completion Command Skill | `skill`, `work-item`, `work-item/lifecycle-stage`, `work-item/transition` | — |
| `tcw-commands-verify-work` | `tcw-commands-verify-work-skill` | TCW Verify Work Command Skill | `skill`, `work-item/lifecycle-stage`, `work-item/transition` | — |
| `tcw-commands-process-inbox` | `tcw-commands-process-inbox-skill` | TCW Process Inbox Command Skill | `skill`, `work-item/intake` | `work-inbox` |

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
    - skills/tcw-extras-triage-issues
    - skills/tcw-post-mortem
    - skills/tcw-extras-autonomous-work
    - skills/tcw-extras-report
    - skills/tcw-commands-plan-work
    - skills/tcw-commands-drive-work-to-completion
    - skills/tcw-commands-verify-work
    - skills/tcw-commands-process-inbox
changed:
    - plugin/bootstrap-the-cli
    - work/complete-a-work-item
    - work/run-a-lifecycle-stage
# plus the nine deletions below, recorded in whatever form
# 2026-09-14-delete-a-capability-with-tcw-capabilities-rm defines. A deleted path
# cannot sit under `changed:`, because the completion gate refuses a path that
# does not resolve.
```

**New — one capability per skill, under `skills/`.**

- **Path:** `skills/<skill-directory>`.
- **Name:** "Offer a skill dedicated to instructing agents how to …". This is the
  requester's form; for example, `skills/tcw-setup` is "Offer a skill dedicated to
  instructing agents how to set up TCW where it does not work yet".
- **Body:** the ledger's own form, "As a user or agent, I …", written in the
  capability's `description.md`. `tcw capabilities add` takes only a path and a
  name, so the body has to be written into that file.
- **Fields:** `Feature` is the skill's Feature path, and `Subject` is `skill`.
- **Status:**
  - The thirteen skills whose behavior already ships (as a skill or as a slash
    command) are created `Supported`. The completion
    gate fails only a `new:` path still `Missing` (`tcw/work/recursion.py:58-61`),
    and seeding something that ships as `Missing` would put a false status on
    `main`.
  - `skills/tcw-setup` and `skills/tcw-configure` are created `Missing`, with
    `Planning doc` set to this item (`skills/tcw-capabilities/SKILL.md:35`), and
    are flipped at completion.

**Deleted and folded in.** A capability is folded into a skill's capability only
when that skill is its **main subject** (revision note 12). Its behavior moves
into the successor's body. The old entry is deleted with
`tcw capabilities rm <path>`, in the same commit that writes the successor's
body. That way no commit on `main` is missing either one.

| Deleted capability | Folded into |
| --- | --- |
| `plugin/work-lifecycle` | split: planning → `skills/tcw-commands-plan-work`, driving through closeout → `skills/tcw-commands-drive-work-to-completion` (its body describes exactly those two commands) |
| `work/consolidate-plans` | `skills/tcw-work` (`skills/tcw-work/references/procedures/consolidate-plans.md`) |
| `work/search-the-work-items` | `skills/tcw-work` (`…/procedures/search.md`) |
| `work/audit-work-backlog` | `skills/tcw-work` (`…/procedures/audit-backlog.md`) |
| `plugin/report-an-issue-upstream` | `skills/tcw-extras-report` |
| `plugin/run-a-post-mortem` | `skills/tcw-post-mortem` |
| `plugin/triage-github-issues` | `skills/tcw-extras-triage-issues` |
| `taxonomy/bootstrap-the-taxonomy` | `skills/tcw-setup` |
| `capabilities/bootstrap-the-capabilities` | `skills/tcw-setup` |

**Changed — kept:**

- **`plugin/bootstrap-the-cli`.** Its main subject is the `SessionStart` install
  hook, so it stays in `plugin/` with no `Feature`. Its two mentions of
  `tcw-plugin` become `tcw-setup`.
- **`work/complete-a-work-item`.** Line 20 of its description links
  `tcw://C/plugin/triage-github-issues`; the link becomes
  `tcw://C/skills/tcw-extras-triage-issues`. `git grep` found no other live reference to
  a deleted path.

- **`work/run-a-lifecycle-stage`.** Its main subject is the two `tcw work stage`
  verbs, so it stays. Its paragraph introducing the five per-stage skills
  (`description.md:104-115`) is reworded to say `tcw-work-stage` reaches every
  stage, and that the stage id is part of the request (D8).

**Not touched:** these capabilities' main subject is CLI or configuration-file
behavior, or the plugin itself:

- `work/configure-the-work-lifecycle`
- `work/declare-which-documents-track-which-changes`
- `work/read-the-documentation-gate-for-a-change`
- `work/customize-the-definition-of-done`
- `plugin/install-as-a-plugin`

## Problem

Setup and configuration text is spread across four skills, three slash commands,
and the user guides. Nothing about the names says which skills set TCW up, which
change its configuration, and which use it.

| Material | Where it lives today |
| --- | --- |
| Installing or repairing the `tcw` CLI | `skills/tcw-plugin/SKILL.md:62-115` |
| Starting a taxonomy | `commands/tcw-taxonomy-init.md:5` → `skills/tcw-taxonomy/references/init.md` |
| Starting a capabilities ledger | `commands/tcw-capabilities-init.md:5` → `skills/tcw-capabilities/references/init.md` |
| `tcw init` (`--id`, `--work-path`, `--taxonomy-path`, `--capabilities-path`), `tcw provision` | No skill document. Refusal text only (`skills/tcw-taxonomy/SKILL.md:30-36`, `skills/tcw-capabilities/SKILL.md:18-25`); user guide `README.md:336-351` |
| `work.documentation` | `commands/tcw-docs-sync-setup.md:7` → `skills/documentation-sync/references/setup.md` |
| `work.lifecycle` bindings | `skills/tcw-work/references/hooks.md:1-19`, `:38-41`, `:97-98` (how to declare); `:21-36` defines roles, kinds and `when:` |
| `work.lifecycle.timeout`, `work.lifecycle.output-cap` | No skill document. `docs/guide/configuration.md:173` covers `timeout`; the CLI reads `output-cap` at `tcw/store/base.py:1843-1848` |
| `docs/work/dod.yaml` | `skills/tcw-work/references/transitions.md:111-115` (behavior only) |
| `work.retain`, `work.auto-commit-transitions` | `skills/tcw-work/references/transitions.md:11-14`, `:23-30` (behavior only, no "how to set") |
| `work.trunk-branch` | No skill document; `docs/guide/work.md:188` |
| `work.publish-transitions` | `skills/tcw-work/references/commands.md:227` |
| `work.tracker` | `skills/tcw-work/references/commands.md:93-100` (keys, and credentials by name) |
| `<component>.path`, `work.repository` | `skills/tcw-work/references/commands.md:152-162`; user guide `docs/guide/multi-repo.md:199-230` |
| `connected-projects` (`parent`, `children`; each entry a locator or `{path, repository}`) | `skills/tcw-work/references/commands.md:173-177` (`{path, repository}` only). No skill text gives the `parent`/`children` shape (`tcw/store/project.py:446-450`). |
| `TCW_PROJECT_<ID>` (a per-machine environment variable) | `skills/tcw-work/references/commands.md:179-191` |
| `extends`, stored in `docs/taxonomy/config.yaml` and `docs/capabilities/.config.yaml` (`tcw/store/fs.py:1790`, `:2236`) | `skills/tcw-taxonomy/SKILL.md:93-102`, `skills/tcw-capabilities/SKILL.md:86-91`, and an outdated version at `skills/tcw-taxonomy/references/init.md:15-23` |

Seven concrete consequences:

1. **Setup requests go to usage skills.** `tcw-taxonomy`'s `description` and
   `when_to_use` list "bootstrapping" and "seeding" (`skills/tcw-taxonomy/SKILL.md:3-4`).
2. **Configuration requests go to usage skills.** `tcw-taxonomy`'s description
   lists "federating shared vocabulary across repos" (`:3`).
3. **Two ways into one procedure.** Each setup procedure can be reached through a
   slash command or through a usage skill's pointer. Codex has no slash commands.
4. **`tcw-plugin` is two unrelated things in one skill.** It holds a skill map
   (`skills/tcw-plugin/SKILL.md:12-60`) and CLI installation (`:62-115`).
5. **Configuration is documented piecemeal, inconsistently, or not at all.** Three
   configuration settings have no skill text. `extends` is described in three
   places, and one of them is out of date.
6. **Nothing keeps it together.** The only documentation rule for skills,
   `Skill-Driven-Component` (`tcw-config.yaml:32-38`), sends every change to "the
   matching skill". At least five open items add configuration keys (see Risks),
   so the scatter grows.
7. **The skills are invisible to the project's own taxonomy.** No term or Feature
   describes a skill, and skill capabilities are scattered across four namespaces;
   `autonomous-work` has none.
8. **Six skills do one job.** `tcw-work-stage` reaches all seven stages, and five
   more skills (`tcw-work-stage-request`, `-spec`, `-plan`, `-implement`,
   `-verify`) repeat it with the stage built in (`README.md:451-461`).
9. **Personal extras look like core skills.** `autonomous-work` and
   `tcw-triage-issues` are skills the requester made for their own workflow, but
   nothing in their names sets them apart from the skills every TCW user needs.
10. **Slash commands duplicate skills and exist only under Claude.** `commands/`
    holds thirteen files (`.claude-plugin/plugin.json:21`). Codex has no slash
    commands, so every command must also be reachable as a skill
    (`docs/lifecycle/harness.md:18`). Claude treats a plugin command and a skill
    the same way: in a Claude session, this plugin's commands are listed as
    invocable skills (`tcw:tcw-plan-work`). Of the thirteen:
    - three point only at a setup document (D3);
    - three (`tcw-cut-version`, `tcw-post-mortem`, `tcw-triage-issues`) point only
      at an existing skill;
    - three (`tcw-work-search`, `tcw-audit-work-backlog`,
      `tcw-consolidate-plans`) point only at a `tcw-work` procedure;
    - four (`tcw-plan-work`, `tcw-drive-work-to-completion`, `tcw-verify-work`,
      `tcw-process-inbox`) carry procedure text found nowhere else.

## Goals

1. **`tcw-setup`** is the one skill for getting TCW working where it doesn't yet:
   - a project that doesn't use TCW;
   - a machine that lacks the CLI or a declared store;
   - a CLI that is missing, broken, or stale.
2. **`tcw-configure`** is the one skill for changing how a working project is
   configured:
   - every key the CLI reads from `tcw-config.yaml`;
   - the `extends` entries in each component's own config file;
   - `docs/work/dod.yaml`;
   - the `TCW_PROJECT_<ID>` environment variable;
   - but not `id` or `work.tags` (Non-goals).
3. Both skills' `SKILL.md` files route and nothing else. Their bodies say which
   reference document to open, and, for first-time setup, in what order.
4. **Usage skills keep what an agent needs while working.** That covers what a
   setting does at runtime and the words it uses. For how to declare or change a
   setting, they point to `tcw-configure`.
5. There is one way into each procedure, and it works the same under Claude and
   Codex.
6. Existing setup and configuration text is moved, not copied. No instruction for
   declaring a setting exists in two skills.
7. **Features and capabilities, one each.**
   - Every top-level skill has exactly one Feature and one capability.
   - Every capability whose main subject is a skill is that skill's capability.
8. **New configuration keys land in `tcw-configure` by rule**, not by someone
   remembering.
9. **One skill composes lifecycle stages:** `tcw-work-stage`.
10. **Three kinds of skill, told apart by name:**
    - plain `tcw-*` (plus `documentation-sync`) for the core skills;
    - `tcw-commands-*` for the core workflow entry points;
    - `tcw-extras-*` for optional skills a user may never need.
11. **No slash commands.** `commands/` is removed, and every entry point is a
    skill, the same under Claude and Codex.

## Non-goals

- Changing what `tcw-post-mortem`, `tcw-work-stage`, the three extras skills, or the
  procedures the four command skills carry say, beyond pointers, renames, and the
  harness wording in D8 and D9.
- Any change to the `tcw` CLI. The delete command is its own item.
- Stub commands, or a stub `tcw-plugin`, under the old names.
- Rewriting history: completed work items, and changelogs and release notes of
  past versions.
- **`id`.** `tcw init --id` writes it once (`project.md`), and changing it is not
  a supported configuration change.
- **`work.tags`.** Tags are registered with `tcw work tags add` in the middle of
  filing work (`skills/tcw-work/references/lifecycle/stage-inbox.md` step 3,
  `skills/tcw-triage-issues/SKILL.md:165`), and `procedures/search.md:30` reads
  `tags.md`. It is part of using `tcw-work`.
- Separating the plugin from the Python source
  (`2026-08-12-separate-the-agent-plugin-from-the-python-cli-source`).
- Running the paid eval harness
  (`2026-09-11-run-the-eval-harness-and-act-on-what-it-finds`).

## Design

### The skill set after this change

`skills/` goes from **fifteen** skills to **fifteen** different ones, and
`commands/` goes from thirteen files to none:
- `tcw-plugin` and the five per-stage skills are removed;
- `tcw-setup` and `tcw-configure` are added;
- the four commands with their own procedure become `tcw-commands-*` skills;
- `autonomous-work`, `tcw-triage-issues` and `tcw-report` are renamed into
  `tcw-extras-*`.
 The grouping is for the reader
only; it is not a folder structure.

| Group | Skill | Change in this item |
| --- | --- | --- |
| **Setting up** | `tcw-setup` | **new**: install half of `tcw-plugin`; both `init.md`s; new `project.md` |
| **Configuring** | `tcw-configure` | **new**: all configuration text in the Problem table |
| **Using TCW** | `tcw-work` | loses how-to-declare text from `hooks.md` and `commands.md`; points to `tcw-configure` |
| | `tcw-taxonomy` | loses `references/init.md`, its setup and federation triggers, and how to declare `extends` |
| | `tcw-capabilities` | loses `references/init.md` and how to declare `extends` |
| | `documentation-sync` | loses `references/setup.md`; description reworded; points to `tcw-configure` |
| | `tcw-work-stage` | now the only stage skill; Feature and capability |
| | `tcw-post-mortem` | Feature and capability only |
| **Command skills** | `tcw-commands-plan-work` | **new** from `commands/tcw-plan-work.md` (D9) |
| | `tcw-commands-drive-work-to-completion` | **new** from `commands/tcw-drive-work-to-completion.md` (D9) |
| | `tcw-commands-verify-work` | **new** from `commands/tcw-verify-work.md` (D9) |
| | `tcw-commands-process-inbox` | **new** from `commands/tcw-process-inbox.md` (D9) |
| **Extras** | `tcw-extras-autonomous-work` | renamed from `autonomous-work` (D8); Feature and capability |
| | `tcw-extras-triage-issues` | renamed from `tcw-triage-issues` (D8); its command deleted (D9) |
| | `tcw-extras-report` | renamed from `tcw-report` (D8) |
| *(removed)* | ~~`tcw-plugin`~~ | install half → `tcw-setup`; skill map deleted (D5) |
| *(removed)* | ~~`tcw-work-stage-request`~~, ~~`-spec`~~, ~~`-plan`~~, ~~`-implement`~~, ~~`-verify`~~ | deleted; `tcw-work-stage` covers every stage (D8) |

```
skills/
  documentation-sync/
    SKILL.md
    references/
      cut-version.md
      release-notes-and-changelogs.md
  tcw-capabilities/
    SKILL.md                     # references/ removed
  tcw-extras-autonomous-work/    # renamed from autonomous-work
  tcw-extras-triage-issues/      # renamed from tcw-triage-issues
  tcw-extras-report/             # renamed from tcw-report
  tcw-commands-plan-work/        # SKILL.md from commands/tcw-plan-work.md
  tcw-commands-drive-work-to-completion/
  tcw-commands-verify-work/
  tcw-commands-process-inbox/
  tcw-configure/                 # new
    SKILL.md                     # routing only
    references/
      work.md                    # work.lifecycle (declaring bindings, timeout, output-cap),
                                 #   dod.yaml, work.retain, work.auto-commit-transitions,
                                 #   work.trunk-branch, work.publish-transitions
      docs-sync.md               # work.documentation, and the CLAUDE.md fallback
      tracker.md                 # work.tracker
      stores.md                  # <component>.path, work.repository, the tcw init path flags
      projects.md                # connected-projects, TCW_PROJECT_<ID>, extends
  tcw-post-mortem/
  tcw-setup/                     # new
    SKILL.md                     # routing only
    references/
      install.md                 # CLI and plugin; a missing, broken, or stale CLI
      project.md                 # tcw init, tcw provision, tcw validate
      taxonomy.md                # starting a taxonomy from existing code
      capabilities.md            # starting a capabilities ledger
  tcw-taxonomy/
    SKILL.md                     # references/ removed
  tcw-work/
  tcw-work-stage/
```

`commands/` is removed entirely, along with the `"commands": "./commands/"` key in
`.claude-plugin/plugin.json` (D9).

### D1 — Where the line between the two skills falls

- **`tcw-setup`: "TCW doesn't work here yet."**
  - A new project.
  - A new machine for an existing project (`tcw provision`).
  - A CLI that is missing, broken, or stale.

  The requester's original agreed layout already put these under setup.
- **`tcw-configure`: "TCW works here, and the user wants it to behave
  differently."** That is every setting in Goal 2.
- **"Set up X", where X is a configuration area, routes to `tcw-configure`.**
  `tcw-setup`'s routing table has explicit rows that send each of these to the
  `tcw-configure` skill: documentation entries, lifecycle bindings, Definition of
  Done, tracker, store locations, and connected or inherited projects.
  `tcw-configure`'s description uses the words "set up" for those areas.
- **First-time setup that also wants configuration** ends at `project.md`'s last
  step, which hands off to the `tcw-configure` skill by name.

### D2 — Each `SKILL.md` routes and nothing else

**What each body contains:**

- One sentence on what this skill is for.
- One sentence naming the other skill as "the `tcw-setup` skill" or "the
  `tcw-configure` skill".
- A routing table with columns *situation* → *document*, with situations in the
  user's words. `tcw-setup`'s table also carries D1's redirect rows.
- `tcw-setup` only: the first-time order — install, project, taxonomy,
  capabilities. That order tells the agent which document to open first, so it
  counts as routing.

**Size.** Each body is at most 60 lines, counted as
`tests/test_skill_lifecycle_parity.py:276-285` counts `tcw-work`'s body. D6 extends
that test to both new skills.

**Frontmatter:**

- **`tcw-setup` `description`** names:
  - a project that doesn't use TCW yet;
  - a `tcw` that is missing, broken, or stale;
  - getting an existing TCW project working on a new machine;
  - starting a taxonomy or capabilities ledger.

  It says that configuration changes belong to the `tcw-configure` skill.
- **`tcw-configure` `description`** names setting up or changing: lifecycle
  bindings, the Definition of Done, documentation entries, a tracker, store
  locations, connected projects, and inherited taxonomy or capabilities.
- Both fill in `when_to_use`.
- **`allowed-tools`** (the tool calls Claude lets the skill make without asking)
  is the union of the lists on the skills each new skill takes text from:
  - `tcw-setup`: `skills/tcw-plugin/SKILL.md:5` plus `Read, Grep, Glob` from
    `skills/tcw-taxonomy/SKILL.md:5`.
  - `tcw-configure`: `skills/tcw-work/SKILL.md:5` plus `Grep, Glob`.

  One consequence is accepted knowingly. Pre-approval applies to the whole skill,
  not to one document, so `tcw-setup`'s `Bash(pipx *)` and `Bash(python3 *)`,
  which only `install.md` needs, are also pre-approved while an agent follows
  `taxonomy.md` or `capabilities.md`.
- `compatibility`, `metadata` and `license` on `tcw-setup` carry over from
  `skills/tcw-plugin/SKILL.md:6-9`. `tcw-configure` carries `metadata` and
  `license`.

**Harness rule.** Under Claude a hint can be passed, as in
`/tcw:tcw-setup taxonomy`. Skill arguments are Claude-only, so a hint is a
convenience, never the route. Neither body may depend on `$ARGUMENTS` or on
dynamic context injection (the `` !`cmd` `` syntax, which under Claude runs a
command and inserts its output).

### D3 — Where each reference document comes from

**Rules for every reference document:**

- It is self-contained. It never sends the agent into `docs/guide/` or the README,
  which a plugin install may not carry once the plugin and the Python source are
  separated.
- A pointer to another skill names that skill and its document in words, for
  example "the `tcw-configure` skill's `docs-sync.md`". It never uses a file path
  like `tcw-configure/references/docs-sync.md`. The eval routing checks (D6) look
  for paths, so skill text must not contain them.
- **A move is two commits.** First a commit that only runs `git mv`, then a commit
  with the edits, so git records the move as a rename (AC 11).

**`tcw-setup/references/`**

| Document | Source | How |
| --- | --- | --- |
| `install.md` | `skills/tcw-plugin/SKILL.md:62-115` | **Moved.** Wording naming the old skill changes. The cloud-environment paragraph (`:107-110`) keeps its rule in its own words and drops the README pointer. |
| `project.md` | none | **New.** Covers `tcw init --id`, the per-component `init`s, and `tcw provision` for a store or project declared elsewhere. Ends with `tcw validate` and the hand-off to the `tcw-configure` skill. Store path flags on `tcw init` are mentioned only as "see the `tcw-configure` skill's `stores.md`". |
| `taxonomy.md` | `skills/tcw-taxonomy/references/init.md` | **Moved** (`git mv`, then edit). Step 2, "Inheritance" (`:15-23`), uses an outdated model: it collects sibling-repo paths and derives aliases. It becomes one question ("does this project inherit from another project?") and a pointer to the `tcw-configure` skill's `projects.md`. |
| `capabilities.md` | `skills/tcw-capabilities/references/init.md` | **Moved** (`git mv`, then edit). Line 9's "point the user at `/tcw-taxonomy-init`" becomes a pointer to `taxonomy.md`. |

**`tcw-configure/references/`**

| Document | Source | How |
| --- | --- | --- |
| `work.md` | `skills/tcw-work/references/hooks.md:1-19`, `:38-41`, `:97-98` | **Moved:** the binding example, "a binding declares one kind explicitly" and what `tcw validate` rejects, the legacy bare-list shape, and the trust note. The roles, kinds and `when:` table (`:21-36`) **stays** in `hooks.md`. `work.md` refers to it by name and does not copy it. **New text:** `work.lifecycle.timeout`; `work.lifecycle.output-cap` (a positive byte count); `docs/work/dod.yaml` (it replaces the built-in list rather than extending it); how to set `work.retain`, `work.auto-commit-transitions`, `work.trunk-branch` and `work.publish-transitions`. |
| `docs-sync.md` | `skills/documentation-sync/references/setup.md` | **Moved** (`git mv`, then edit). Keeps the `CLAUDE.md` form for projects that don't use TCW (`setup.md:27`). Retitled "Declare which documents track which changes". Its pointers into `SKILL.md` (`:34`, `:37`) name the `documentation-sync` skill. |
| `tracker.md` | `skills/tcw-work/references/commands.md:93-100` | **Moved:** the `work.tracker` keys and "credentials are named, never stored". What a malformed block does and that `tcw validate` never contacts the tracker (`:102-109`) are runtime behavior, so they **stay** in `commands.md`. |
| `stores.md` | `skills/tcw-work/references/commands.md:156-162` | **Moved:** declaring `work.repository`. **New text:** `taxonomy.path`, `capabilities.path`, `work.path`, and the `tcw init --work-path/--taxonomy-path/--capabilities-path` and `tcw work init --path` flags. It must say that changing a store's path **does not move** existing items, and that a store that isn't empty is never moved automatically (`docs/guide/multi-repo.md:205`, `tcw/store/fs.py:924-934`). Ends with `tcw validate`, plus `tcw provision` where a `repository` block was added. |
| `projects.md` | `skills/tcw-work/references/commands.md:173-191`; `skills/tcw-taxonomy/SKILL.md:93-98`; `skills/tcw-capabilities/SKILL.md:86-91` | **Moved:** declaring a connected project as `{path, repository}`, `TCW_PROJECT_<ID>`, and declaring inheritance with `tcw taxonomy extends add\|rm` and `tcw capabilities extends [--rm]`. **New text:** the `connected-projects` shape — a mapping with `parent` (at most one entry) and `children`, each entry a locator or `{path, repository}` (`tcw/store/project.py:446-450`) — and the fact that `extends` is stored in each component's own config file. |

**Projects that don't use TCW.** `documentation-sync` also serves them, so its
pointers open the `tcw-configure` skill's `docs-sync.md` **as a document**. They
never ask the agent to choose `tcw-configure` from its description, which is about
TCW projects.

### D4 — What each existing skill and document loses and keeps

Every cut ends at a paragraph boundary. The plan re-reads the text that remains
for anything left pointing at text that moved, such as "both", "the same way", or
"below".

- **`tcw-taxonomy`**
  - `description`: remove "federating shared vocabulary across repos, or
    bootstrapping a taxonomy from an existing codebase" (`SKILL.md:3`).
    `when_to_use`: remove "seeding", "federating shared vocabulary across repos"
    and "bootstrapping …" (`:4`).
  - Remove "See `tcw-plugin` for the cross-skill map." (`:24-25`).
  - Replace `## Bootstrap` (`:104-107`) with one line pointing to the `tcw-setup`
    skill.
  - `## Inheritance` (`:93-102`): declaring moves out. Resolution of inherited
    terms stays, with one line pointing to the `tcw-configure` skill. The `extends`
    quick-reference row (`:119`) points there too.
  - The refusal text for a store that isn't provisioned (`:30-36`) stays.
- **`tcw-capabilities`**
  - Replace `## Bootstrap` (`SKILL.md:117-120`) with one line pointing to the
    `tcw-setup` skill.
  - `## Federation` (`:86-91`): declaring moves out; overrides and `reset` stay.
    The quick-reference row (`:133`) points to `tcw-configure`.
  - The refusal text (`:18-25`) stays.
- **`tcw-work`**
  - `SKILL.md`:
    - Delete "`tcw-plugin` maps the skills." (`:19-20`).
    - `:55` points to `hooks.md` for how bindings run, and to the `tcw-configure`
      skill for declaring them.
    - The body is exactly 60 lines today. Deleting that sentence frees the room
      the new pointer needs, and the body stays at or under 60.
  - `references/hooks.md`:
    - loses `:1-19`, `:38-41`, `:97-98`, and opens with one line pointing to
      `tcw-configure`;
    - keeps the roles, kinds and `when:` table (`:21-36`), "The three verbs"
      (`:43-66`), "What runs" (`:68-84`), and "Two limits" (`:86-95`).
  - `references/transitions.md`: at `:11` and `:23`, the named keys gain "(set
    with the `tcw-configure` skill)". Nothing else changes, because there is no
    how-to-set text to remove.
  - `references/commands.md`:
    - loses `:93-100`, `:156-162` and `:173-191`, and keeps a one-line pointer at
      each place;
    - keeps `:102-109`, and the resolution behavior at `:164-171`.
  - `references/lifecycle/default/README.md:51` says `hooks.md` "has the binding
    shapes and the conditions". The shapes move and the conditions stay, so the
    line names both documents.
- **`documentation-sync`**
  - `description` (`SKILL.md:3`): reword "Use when a project declares
    documentation entries — in `tcw-config.yaml` …" into a usage trigger, such as
    "Use when a project has documentation entries — from `tcw work docs`, or a
    `## Documentation Sync` section — and a change may have fired one". The
    reworded sentence does not contain "declare".
  - `:15`, `:29`, and the table row at `:98`: point to the `tcw-configure` skill's
    `docs-sync.md`, as a document.
  - `references/release-notes-and-changelogs.md:5` ("read `setup.md`") gets the
    same change.
- **`tcw-config.yaml`**
  - Add a documentation entry:
    - `path: skills/tcw-configure/references/<document>.md`
    - `trigger: Configuration-Key-Change`, a trigger this project defines
    - description: "How to declare or change each configuration setting. Update
      the matching document whenever a key in `tcw-config.yaml`, a component
      config file, `docs/work/dod.yaml`, or a `TCW_PROJECT_<ID>`-style variable is
      added, removed, or changes meaning."
  - The `Skill-Driven-Component` description (`:34-38`) gains: "How to configure
    a component goes to `tcw-configure`, not to the component's skill."

### D5 — The skill map is deleted

`skills/tcw-plugin/SKILL.md:12-60` isn't moved anywhere, because everything it
says is already said by a skill that stays:

| What the map says | Already said at |
| --- | --- |
| `Vocabulary → Features → Capabilities → Work` | `skills/tcw-work/SKILL.md:17`, `skills/tcw-taxonomy/SKILL.md:20` |
| Capabilities point loosely at `Subject`, strongly at `Feature` | `skills/tcw-capabilities/SKILL.md:27` |
| The axes point forward | `skills/tcw-taxonomy/SKILL.md:23-24` |
| `tcw-work` runs the capability check | `skills/tcw-work/SKILL.md:18-19` |
| `tcw-report` vs `tcw-triage-issues` | both skills' `description` |
| Which axis skill handles which request | each axis skill's `description` |

Retargeted case B5 (D6) measures whether the descriptions still route an
orientation question.

### D6 — Evals

`tests/test_eval_coverage.py` fails unless every shipped skill is named by a case
or listed in `EXCLUSIONS`.

**1. A predicate that sees only tool calls.** `transcript_contains` and
`transcript_absent` search all transcript text (`evals/grade.py:84-106`). That
includes skill bodies the agent loaded, so a skill that merely mentions a path
could fake a routing result.

- Add two predicates:
  - `tool_input_contains`: some tool call's *input* contains the substring;
  - `tool_input_absent`: no tool call's input contains it.
- Each needs a grader in `evals/grade.py`, a declaration in `evals/evals.json`'s
  `predicates`, and passing and failing grading tests. The existing test
  `test_every_declared_predicate_has_a_grader` keeps declarations and graders
  matched.
- The D3 rule (pointers in words, never paths) keeps skill text from satisfying
  these checks by accident.

**2. Fix `files_changed_exactly`** (revision note 11).

- **Today** it compares `HEAD~1` with `HEAD` (`evals/grade.py:338-343`), not the
  seeded state described at `evals/evals.json:158-163`.
- **After:**
  - `seed()` records the seeded commit in the manifest (`seeded_head`), and
    `run_evals.py` carries it into the run entry.
  - The check compares that commit with the working tree, and includes untracked,
    non-ignored files.
  - Re-check B10's expected file list against the fixed behavior.
- **Tests** build a real git repository in a temporary directory, because the
  committed grading fixtures (`tests/fixtures/eval_grading/*/fixture`) have no
  `.git`. Each gets one case that must pass and one that must fail, including
  "uncommitted edit" and "extra file".

**3. Case changes.**

1. **B5 is retargeted.** It becomes `skill: cross-axis`,
   `invokes: ["tcw-taxonomy", "tcw-capabilities"]`, keeping its prompt and
   assertions.
2. **New `tcw-configure` case, phrased "set up", on the existing fixture.**
   - **Prompt:** set up documentation tracking for a file that exists in the
     fixture but has no entry under the requested trigger. The plan picks the
     file; the fixture's entries are at `evals/seed_fixture.py:243-253`. Using an
     existing file means the procedure has no reason to create one.
   - **Assertions:**
     - `tool_input_contains` `tcw-configure/references/docs-sync.md`;
     - `tool_input_absent` `tcw-setup/references/`;
     - `files_changed_exactly` `["tcw-config.yaml"]`;
     - `validate_exit_zero`.
3. **New `tcw-setup` case: initialize a fresh repository**, on a new `bare`
   fixture (a git repository with code and no `tcw-config.yaml`).
   - **Assertions:**
     - `tool_input_contains` `tcw-setup/references/project.md`;
     - `tool_input_absent` `tcw-configure/references/`;
     - `validate_exit_zero`.
   - **What the fixture needs:**
     - `seed()` takes a variant name (`customized`, `control`, `bare`), not a
       true/false flag.
     - `run_evals.variant_for` (`:113-119`) returns that name, and a case's new
       optional `fixture` key overrides it.
     - The bare manifest supplies empty `nonces` and `stage_items`, because
       `run_one` reads both (`evals/run_evals.py:195-196`).
     - `tests/test_eval_runner.py:48-59` asserts on the new return values.
     - `tests/test_eval_fixture.py` covers `bare`.
     - `evals/evals.json`'s schema block documents `fixture` and updates its case
       id range.
4. **B4 and B8 each gain `tool_input_absent` `tcw-setup/references/`.** B8 ends
   "Set it up."
5. **A1–A4 and A8 invoke `tcw-work-stage`** instead of the deleted per-stage skills
   (`evals/evals.json:171`, `:207`, `:243`, `:279`, `:402`). Their prompts already
   name the stage ("Work the spec stage for {item}."), so the prompts and
   assertions are unchanged. `EXCLUSIONS["tcw-work-stage-request"]`
   (`evals/coverage.py:35-38`) goes, because the skill it excludes no longer
   exists.
6. **B7 invokes `tcw-extras-triage-issues`** (`evals/evals.json:653-654`), **B6
   invokes `tcw-extras-report`** (`:625-626`), and
   `EXCLUSIONS["autonomous-work"]` (`evals/coverage.py:39`) is re-keyed to
   `tcw-extras-autonomous-work`.
7. **The four command skills are listed in `EXCLUSIONS`**, each with the reason
   "composes `tcw-work` stage documents that axis A measures, and has no case of
   its own yet". The run-the-evals item's note records this as a gap to consider.

**4. Coverage bookkeeping** (`evals/coverage.py`). `PARTIAL` records what is not
measured:

- `tcw-setup`:
  - install/repair stays unmeasured, because faking a broken install is unsafe
    (`:53-56`);
  - `taxonomy.md` and `capabilities.md` ask the user questions, the same reason
    `request` is treated as interactive;
  - provisioning needs a remote.
- `tcw-configure`: only `docs-sync.md` is measured.

The `tcw-plugin` entry goes.

**5. Lasting guards.**

- A deleted-names test, following `DELETED` at
  `tests/test_skill_lifecycle_parity.py:47,254`. It rejects, as whole names
  (so `tcw-extras-autonomous-work` does not match `autonomous-work`):
  `tcw-plugin`, `tcw-taxonomy-init`, `tcw-capabilities-init`,
  `tcw-docs-sync-setup`, the five `tcw-work-stage-<stage>` names,
  `autonomous-work`, `tcw-triage-issues`, `tcw-report`, `tcw-plan-work`,
  `tcw-drive-work-to-completion`, `tcw-verify-work`, `tcw-process-inbox`,
  `tcw-work-search`, `tcw-audit-work-backlog`, `tcw-consolidate-plans` and
  `tcw-cut-version`. It scans `skills/`, the manifests, `README.md`,
  `docs/guide/` and `docs/lifecycle/`, and also asserts that `commands/` does not
  exist.
- The router tests in `tests/test_skill_lifecycle_parity.py`, extended to both new
  skills: body at most 60 lines, and every file in the skill's `references/`
  linked from its `SKILL.md`.
- A test that no file under `skills/` contains `tcw-setup/references/` or
  `tcw-configure/references/` outside the owning skill. This holds the D3 rule.

### D7 — Other files

| File | Change |
| --- | --- |
| `commands/tcw-taxonomy-init.md`, `commands/tcw-capabilities-init.md`, `commands/tcw-docs-sync-setup.md` | Deleted. |
| `scripts/session_bootstrap.sh:9`, `:45` | Comments name `tcw-setup` and `install.md`. |
| `README.md:217`, `:227` | `tcw-plugin` → `tcw-setup`. |
| `README.md:352` | The two slash commands → asking for the `tcw-setup` skill. |
| `README.md:430-432` | "Fifteen skills … Nine carry a distinct procedure; the other six all compose one lifecycle stage" → fifteen skills in three groups: eight core skills (one of which composes a lifecycle stage), four command skills, and three extras. |
| `README.md:438-446` | The `tcw-plugin` row → rows for `tcw-setup` and `tcw-configure`; `tcw-triage-issues` and `autonomous-work` rows renamed, under an "Extras" note saying `tcw-extras-*` skills are optional. |
| `README.md:451-461` | "Reading a lifecycle stage" describes one skill, `tcw-work-stage`. |
| `README.md:465-472` | The "slash commands" paragraph becomes a short description of the four `tcw-commands-*` skills and the three `tcw-extras-*` skills. |
| `docs/guide/work.md:212`, `:465`, `:475` | Slash-command mentions become the skill to ask for: `tcw-extras-triage-issues`, and the `tcw-work` skill for auditing and consolidating. |
| `skills/tcw-work/references/lifecycle/stage-inbox.md:11`, `skills/tcw-work/references/transitions.md:117`, `:157` | `tcw-triage-issues` → `tcw-extras-triage-issues`. |
| `docs/guide/taxonomy-and-capabilities.md:59` | As `README.md:352`. |
| `.codex-plugin/plugin.json` `longDescription` | The count stays "fifteen skills", with a different set named: the `tcw-plugin` clause becomes `tcw-setup` and `tcw-configure` clauses; the per-stage skills' names are removed; the three extras are renamed; the four command skills are added. |
| `tests/test_documentation_sync_wiring.py` | `SKILL_FILES` (`:13-19`) drops `setup.md`. `COMMAND_ROUTES`' `tcw-docs-sync-setup` entry (`:23-26`) goes. The docstring at `:109-115` and the test at `:127-134` read the `tcw-configure` skill's `docs-sync.md`. |
| `tests/test_documentation_config.py:137` | Docstring names the moved document. |
| `tests/test_plugin_manifests.py:4` | Docstring names `tcw-setup`. |
| `evals/*`, `tests/test_eval_*.py`, `tests/test_skill_lifecycle_parity.py` | Per D6 and D8. |
| `tcw-config.yaml` | Per D4. |
| `docs/taxonomy/…`, `docs/capabilities/…` | Per **Capability changes**: `tcw taxonomy add`, `tcw capabilities add`, `set` and `rm`, plus body text in `description.md` and `relatesTo` in `meta.yaml`. |
| `docs/changelogs/upcoming.md`, `docs/release-notes/upcoming.md` | Removed commands and skill, the two new skills, deleted capability paths and their successors, new taxonomy entries, the eval predicate and fixture changes. |
| Open work items (Risks) | A one-line note on each. |

### D8 — The per-stage skills are deleted, and two skills become extras

**Deleting the per-stage skills** (revision note 13).

- **Delete** `skills/tcw-work-stage-request/`, `-spec/`, `-plan/`, `-implement/`,
  `-verify/`. `tcw-work-stage` already reaches all seven stages and takes the
  stage id (`skills/tcw-work-stage/SKILL.md:3-5`), so no capability is lost.
- **Remove the per-stage machinery from `tests/test_skill_lifecycle_parity.py`**
  (`:305-375`):
  - `NO_PER_STAGE_SKILL`, `PER_STAGE_IDS`, `PER_STAGE_SKILLS`;
  - `test_the_per_stage_skills_are_exactly_the_stages_that_get_one`;
  - `test_a_per_stage_skill_takes_the_item_alone`.

  The `@composing` tests keep running against the generic skill alone, and the
  section's comment is rewritten to say one document composes a stage.
- **Evals:** D6.3 items 5 and 6.
- **Capability:** `work/run-a-lifecycle-stage`'s paragraph at
  `description.md:104-115` is reworded (Capability changes).
- **Not changed:** `tests/test_plugin_manifests.py:76-127` uses
  `tcw-work-stage-spec` in a synthetic example of the name-prefix problem. It is
  test data about name matching, not a reference to a shipped skill, so it stays.
  AC 4 excludes that file.

**The `tcw-extras-` prefix** (revision note 14).

- **A convention, recorded where readers look.** The README skills section says
  `tcw-extras-*` skills are optional, built for one way of working, and not needed
  to use TCW.
- **`autonomous-work` → `tcw-extras-autonomous-work`:**
  - `git mv skills/autonomous-work skills/tcw-extras-autonomous-work`;
  - its `name:` field is updated.
- **`tcw-triage-issues` → `tcw-extras-triage-issues`:**
  - `git mv` the skill directory;
  - update `name:` and the skill's references to its own name.
- **`tcw-report` → `tcw-extras-report`:**
  - `git mv` the skill directory and update `name:`;
  - rename it in `skills/tcw-extras-triage-issues/SKILL.md:3-4`, the README,
    the Codex manifest, and eval case B6.
- **Every other reference is renamed** (D7): the README, `docs/guide/work.md`, two
  `tcw-work` references, the Codex manifest, `evals/evals.json` B7, and
  `evals/coverage.py`.
- **Harness.** All three are reachable by invoking the skill, under Claude and
  Codex alike.

### D9 — Slash commands are removed

Every command is either deleted, because a skill already carries everything it
says, or turned into a skill. Each deletion was checked against the skill it
points to (revision note 15):

| Command | Fate | What the command says beyond "use the skill", and where that already lives |
| --- | --- | --- |
| `tcw-taxonomy-init`, `tcw-capabilities-init`, `tcw-docs-sync-setup` | Deleted | Setup documents move into `tcw-setup` and `tcw-configure` (D3). |
| `tcw-cut-version` | Deleted | "Use the project's own version-cut process first" → `skills/documentation-sync/references/cut-version.md:14`; "ask before pushing" → `:86`. |
| `tcw-post-mortem` | Deleted; the skill keeps its name | "Delegable to the read-only agent; Codex runs it inline" → `skills/tcw-work/references/lifecycle/stage-postmortem.md:21-24`; "never changes status" → `skills/tcw-post-mortem/SKILL.md:73`. |
| `tcw-triage-issues` | Deleted | "Not TCW's repository; that is the report skill" → `skills/tcw-triage-issues/SKILL.md:3-4`; "approve every reply one at a time" → `:196-197`, `:252`. |
| `tcw-work-search` | Deleted | The whole procedure is `skills/tcw-work/references/procedures/search.md` ("under any harness, this document is the procedure", `:8`), including "read-only" (`:10-11`) and reading the search description (`:3-5`). |
| `tcw-audit-work-backlog` | Deleted | `procedures/audit-backlog.md` is the whole procedure (`:3-6`). |
| `tcw-consolidate-plans` | Deleted | `procedures/consolidate-plans.md` is the whole procedure (`:3-7`). The command's `disable-model-invocation: true` is replaced by the procedure's own "Start only when asked" rule (`:11-14`). That rule is a judgment, not an enforced block, which is the same guarantee Codex users have today. |
| `tcw-plan-work` | → `skills/tcw-commands-plan-work/SKILL.md` | Its request → plan range, one commit per artifact, and "stop at `plan.md`" appear nowhere else. |
| `tcw-drive-work-to-completion` | → `skills/tcw-commands-drive-work-to-completion/SKILL.md` | Current stage → `complete`, "ask sequential or subagents", "stop at verify and never complete silently", closeout checklist. |
| `tcw-verify-work` | → `skills/tcw-commands-verify-work/SKILL.md` | Assess, stop for the user, `submit` first, `refined-outcome.md` or `rework.md`, reconcile capabilities. |
| `tcw-process-inbox` | → `skills/tcw-commands-process-inbox/SKILL.md` | Every inbox entry → accepted item → the `request` stage on its intake. |

**Turning a command into a skill:**

- `git mv commands/<name>.md skills/tcw-commands-<rest>/SKILL.md`, so history
  follows the file.
- **Frontmatter:** `name:`, the command's `description:` kept, a `when_to_use:`,
  and `allowed-tools` taken from `skills/tcw-work/SKILL.md:5`.
- **Body:**
  - Paths relative to `tcw-work` (`references/lifecycle/stage-request.md`) name
    "the `tcw-work` skill's" document.
  - `$ARGUMENTS` is removed, because the item is named in the request.
  - Cross-references between commands (`/tcw-drive-work-to-completion`) name the
    skill.

**References to deleted commands:**

- **`skills/tcw-work/references/procedures/search.md:7-8`, `audit-backlog.md:5`,
  `consolidate-plans.md:6`:** "Claude users reach it as `/tcw-…`" becomes "Ask the
  `tcw-work` skill for it".
- **`skills/tcw-work/SKILL.md`:** `when_to_use` gains "searching the board,
  auditing the backlog, or consolidating external planning documents", so a
  request like "`/tcw-work` search for items about X, newest first" reaches those
  procedures.
- **`skills/tcw-work/references/commands.md:135-140`** ("Slash commands (Claude
  only)") names the four `tcw-commands-*` skills instead. `:42-43`'s table rows
  keep pointing at the procedures.
- **`skills/tcw-work/references/lifecycle/stage-verify.md:36`:** drop
  "`/tcw-cut-version` is the Claude shortcut to the same thing".
- **`skills/tcw-extras-autonomous-work/SKILL.md:8`:** `/tcw-drive-work-to-completion`
  becomes the `tcw-commands-drive-work-to-completion` skill.
- **`docs/lifecycle/harness.md:18`** becomes: "This plugin ships no slash
  commands. Every entry point is a skill, which both harnesses can invoke."
- **`tests/test_documentation_sync_wiring.py:21-26`, `:97-104`:** `COMMAND_ROUTES`
  and `test_commands_route_into_the_skill` are deleted. Their purpose (a command
  must not be the only route) no longer applies.
- **`.claude-plugin/plugin.json:21`:** remove the `commands` key.

### Abstraction and harness checks

- **Abstraction litmus test.** No store operation is added or changed here.
  Capabilities are deleted with `tcw capabilities rm`, which is its own item and
  passes the test there.
- **Harness.** Every procedure is reachable by invoking a skill. D2 forbids
  depending on arguments or on context injection.

## Acceptance criteria

Checked from the repository root. **`<base>`** means the last commit before this
item's first implementation commit, which is the commit that last touched this
item's `plan.md`.

1. `ls skills` lists exactly: `documentation-sync tcw-capabilities tcw-configure
   tcw-commands-drive-work-to-completion tcw-commands-plan-work
   tcw-commands-process-inbox tcw-commands-verify-work tcw-extras-autonomous-work
   tcw-extras-report tcw-extras-triage-issues tcw-post-mortem tcw-setup
   tcw-taxonomy tcw-work tcw-work-stage`. `commands/` does not exist, and
   `.claude-plugin/plugin.json` has no `commands` key.
2. `ls skills/tcw-setup/references` lists exactly `capabilities.md install.md
   project.md taxonomy.md`. `ls skills/tcw-configure/references` lists exactly
   `docs-sync.md projects.md stores.md tracker.md work.md`.
3. None of these exist:
   - `skills/tcw-plugin/`
   - `skills/tcw-taxonomy/references/`
   - `skills/tcw-capabilities/references/`
   - `skills/documentation-sync/references/setup.md`
   - `commands/`
4. This prints nothing:
   `git grep -nP 'tcw-plugin|tcw-taxonomy-init|tcw-capabilities-init|tcw-docs-sync-setup|tcw-work-stage-(request|spec|plan|implement|verify)|(?<![-\w])autonomous-work|tcw-triage-issues|(?<![-\w])tcw-report|tcw-(plan-work|drive-work-to-completion|verify-work|process-inbox|work-search|audit-work-backlog|consolidate-plans|cut-version)' -- . ':!docs/work' ':!docs/changelogs' ':!docs/release-notes' ':!tests/test_skill_lifecycle_parity.py' ':!tests/test_plugin_manifests.py'`
5. This prints nothing:
   `git grep -nE 'references/(init|setup)\.md|[^/]setup\.md' -- skills tests`
6. For each of `skills/tcw-setup/SKILL.md` and `skills/tcw-configure/SKILL.md`:
   - the body is at most 60 lines (counted as in
     `tests/test_skill_lifecycle_parity.py:280-282`);
   - it links every file in its own `references/`, and every relative link
     resolves;
   - it contains neither `$ARGUMENTS` nor `` !` ``;
   - it contains the literal "the `tcw-configure` skill" (in `tcw-setup`) or "the
     `tcw-setup` skill" (in `tcw-configure`).
7. `skills/tcw-setup/SKILL.md` has a routing row naming "the `tcw-configure`
   skill" for each of these: documentation entries, lifecycle bindings,
   Definition of Done, tracker, store locations, and connected or inherited
   projects.
8. Compared case-insensitively:
   - `tcw-setup`'s `description` contains `missing`, `broken`, `stale`,
     `taxonomy`, `capabilities`;
   - `tcw-configure`'s `description` contains `lifecycle`, `definition of done`,
     `documentation`, `tracker`, `store`, `connected`, `set up`.
9. Compared case-insensitively:
   - `skills/tcw-taxonomy/SKILL.md`'s `description` and `when_to_use` contain none
     of `bootstrap`, `seed`, `federat`;
   - `skills/documentation-sync/SKILL.md`'s `description` does not contain
     `declare`.
10. Skill pointers:
    - `skills/tcw-taxonomy/SKILL.md` and `skills/tcw-capabilities/SKILL.md` each
      contain "the `tcw-setup` skill" and no `## Bootstrap` heading.
    - `skills/tcw-work/SKILL.md`, `skills/tcw-taxonomy/SKILL.md`,
      `skills/tcw-capabilities/SKILL.md`, `skills/documentation-sync/SKILL.md`,
      and `skills/tcw-work/references/hooks.md` each contain "the `tcw-configure`
      skill".
11. **Moved text arrived whole.**
    - **Renames.** For each of these, some commit in `<base>..HEAD` lists it as
      `R100` in `git show --name-status --find-renames <commit>`:
      - `skills/tcw-taxonomy/references/init.md` →
        `skills/tcw-setup/references/taxonomy.md`
      - `skills/tcw-capabilities/references/init.md` →
        `skills/tcw-setup/references/capabilities.md`
      - `skills/documentation-sync/references/setup.md` →
        `skills/tcw-configure/references/docs-sync.md`
    - **Partial moves.** For each source range below, taken as it stood at
      `<base>`: strip leading `#` characters and surrounding whitespace from every
      non-blank line. Each stripped line must appear as a substring of the
      destination document, **or** be listed in `outcome.md` under "Moved lines
      changed", with the reason.
      - `skills/tcw-plugin/SKILL.md:62-115` → `tcw-setup/references/install.md`
      - `skills/tcw-work/references/hooks.md:1-19`, `:38-41`, `:97-98` →
        `tcw-configure/references/work.md`
      - `skills/tcw-work/references/commands.md:93-100` →
        `tcw-configure/references/tracker.md`
      - `skills/tcw-work/references/commands.md:156-162` →
        `tcw-configure/references/stores.md`
      - `skills/tcw-work/references/commands.md:173-191` →
        `tcw-configure/references/projects.md`
12. Required content:
    - `skills/tcw-configure/references/work.md` contains `work.lifecycle`,
      `timeout`, `output-cap`, `dod.yaml`, `work.retain`,
      `work.auto-commit-transitions`, `work.trunk-branch`,
      `work.publish-transitions`.
    - `stores.md` contains `work.path`, `work.repository`, `--work-path`, and
      `does not move`.
    - `projects.md` contains `connected-projects`, `parent`, `children`,
      `TCW_PROJECT_`, and `extends`.
    - `tracker.md` contains `work.tracker`.
13. `skills/tcw-work/references/hooks.md`:
    - still contains `| Role`, `tcw work stage gate`, and "`tcw serve` runs no
      hooks";
    - no longer contains `# Lifecycle bindings` as its first line.

    `skills/tcw-work/references/lifecycle/default/README.md` contains
    `tcw-configure`.
14. No file under `skills/` outside `skills/tcw-setup/` contains
    `tcw-setup/references/`. No file under `skills/` outside
    `skills/tcw-configure/` contains `tcw-configure/references/`. The test from
    D6.5 enforces this.
15. **Taxonomy.**
    - `tcw taxonomy show skill` exits 0.
    - For every row of the Taxonomy table, `tcw taxonomy show <Feature path>`
      exits 0, prints `kind: Feature`, and prints a `vocabulary:` line containing
      every term in that row.
    - `tcw taxonomy check` exits 0.
16. **Capabilities, at verify.**
    - For each of the thirteen skills whose behavior already ships `<s>`,
      `tcw capabilities show skills/<s>` prints `**Status:** Supported` and a
      `**Feature:**` line equal to its Feature path.
    - `skills/tcw-setup` and `skills/tcw-configure` print `**Status:** Missing`,
      their Feature line, and `**Planning doc:**` naming this item.
    - `tcw capabilities show <path>` exits non-zero for each of the nine deleted
      paths.
    - `tcw capabilities show plugin/bootstrap-the-cli` does not print
      `tcw-plugin`, and `tcw capabilities show work/run-a-lifecycle-stage` does not
      print `tcw-work-stage-spec`.
    - `tcw capabilities check` prints `capabilities OK`.
17. **Capabilities, after `tcw work complete`.** `skills/tcw-setup` and
    `skills/tcw-configure` print `**Status:** Supported`. The completion gate
    enforces this.
18. **Evals.**
    - `evals/evals.json` has no case whose `skill` or `invokes` is `tcw-plugin`.
    - B5's `skill` is `cross-axis`.
    - No case's `invokes` names a `tcw-work-stage-<stage>` skill; A1–A4 and A8
      invoke `tcw-work-stage`. B7 invokes `tcw-extras-triage-issues`, and B6
      invokes `tcw-extras-report`.
    - `EXCLUSIONS` has the four `tcw-commands-*` skills, each with a reason.
    - `EXCLUSIONS` has no `tcw-work-stage-request` or `autonomous-work` key, and
      has `tcw-extras-autonomous-work`.
    - One case's `invokes` is `tcw-setup`, and one case's is `tcw-configure`.
    - B4 and B8 each assert `tool_input_absent` `tcw-setup/references/`.
    - `PARTIAL` has keys `tcw-setup` and `tcw-configure`, and not `tcw-plugin`.
    - `tests/` contains a failing-transcript grading test for
      `tool_input_contains` and `tool_input_absent`, and a failing-fixture test for
      `files_changed_exactly` with an uncommitted edit.
19. `tcw work docs` lists an entry whose path starts
    `skills/tcw-configure/references/`.
20. Bare `pytest` passes (how CI runs it), and `tcw validate` exits 0.

## Risks

- **Routing is a judgment until a paid run.** D1, D4 and ACs 7–9 remove every
  setup or configuration trigger found in a usage skill's description, and D6's
  cases test the weakest boundary. Whether agents actually route correctly is
  measured only when the eval run happens.
- **Text is split across skills.** An agent in `tcw-work` reading
  `tcw work lifecycle` output still has the roles, kinds and `when:` definitions
  (`hooks.md` keeps them). For anything declarative it follows a pointer. D4's
  paragraph-boundary rule and re-read guard against leftover references like
  "both" and "below".
- **Folding four capabilities into `skills/tcw-work`** makes one long body. ACs
  check status and links, not body completeness, so that is left to review
  against the four deleted bodies as they stood at `<base>`.
- **Dependency.** `2026-09-14-delete-a-capability-with-tcw-capabilities-rm` must
  complete first and define how a work item records a deletion. If it chooses
  something other than a `capabilities.yaml` key, the Capability changes block
  follows it.
- **Open items that add configuration keys or edit moved text.** Each gets a
  one-line note saying where its configuration text now goes. Whichever of the
  two lands second places that text in `tcw-configure`.
  - `2026-09-12-configure-an-external-tracker-and-read-its-tickets` (active). Its
    tracker text is on `main`, and this item moves `commands.md:93-100`, so
    implement after it completes, or rebase onto its final text.
  - `2026-09-12-claim-an-external-tracker-ticket-and-bind-it-to-a-work-item`,
    `2026-09-12-synchronize-the-work-lifecycle-outward-to-the-tracker`,
    `2026-09-12-refuse-local-work-that-no-claimed-tracker-ticket-authorizes`, and
    `2026-09-12-surface-an-item-s-tracker-binding-in-the-board-the-projection-and-the-web-app`
    add tracker keys.
  - `2026-08-18-serve-version-cut-instructions-from-tcw-config-yaml-instead-of-the-agent-guide`
    adds `work.versioning`.
  - `2026-09-10-let-a-node-declare-its-own-work-item-state-fields` and
    `2026-09-10-record-a-work-item-s-branch-and-let-a-node-declare-its-own-state-fields`
    add configuration.
- **Open items whose referenced files or capabilities change.**
  - `2026-09-01-fan-the-backlog-audit-out-across-every-connected-work-root`: its
    capability delta should name `skills/tcw-work`.
  - `2026-09-11-run-the-eval-harness-and-act-on-what-it-finds`: this item lands
    first; the note lists the new predicates, cases and fixture.
  - `2026-09-11-refine-the-plugin-skills-and-lifecycle-prompts-against-the-eval-findings`:
    it will refine the restructured skills.
  - `2026-08-18-report-the-missing-skill-caveat-from-tcw-work-lifecycle-rather-than-the-skill`:
    it quotes a caveat now at `hooks.md:88`, which stays but moves line.
  - `2026-08-12-separate-the-agent-plugin-from-the-python-cli-source`: its
    `plan.md` names `tcw-plugin` paths.
- **Revision notes 13–15 are unreviewed.** They came after both review rounds.
  The deletions and renames are mechanical, and D8 and ACs 1, 4 and 18 check them.
  But the eval retargeting of A1–A4 and A8 changes what axis A measures: the
  generic skill with two arguments instead of a per-stage skill with one. The
  run-the-evals item's note should say so.
- **Muscle memory.** Every slash command, the per-stage skill names, and
  `tcw-report` stop working. That is acceptable, because nobody but the requester
  uses TCW yet (revision notes 3, 14 and 15).
  - Under Claude the four core workflows are still one invocation away, as
    `/tcw:tcw-commands-plan-work` and so on.
- **`disable-model-invocation` is lost for consolidate-plans.** The procedure's
  "Start only when asked" rule replaces it (D9), and nothing enforces that rule.
- **Size.** Scope is several times the first estimate, and `state.yaml` still says
  `effort: medium`. Re-estimating is a plan-stage task.

## Notes

- **Reviewers' open points, now settled.**
  - `tcw taxonomy add --parent` accepts a Feature as parent (tested in round two).
  - The eval routes were chosen: the requester accepted round one's
    recommendation.
- **Judgment, flagged:** `id` and `work.tags` stay out of `tcw-configure`
  (Non-goals).
- **Assumption:** that `tcw-plugin` is mostly opened when the CLI is broken. The
  design doesn't depend on it.
- **Search for other places to change** (repository-wide, excluding history):
  - `git grep` for the four removed names and for `references/(init|setup|hooks).md`
    and bare `setup.md`.
  - Configuration keys: every `get("…")` on configuration in `tcw/store/fs.py`,
    `tcw/store/base.py`, `tcw/store/project.py` and `tcw/validate.py`, plus the
    component config files that `extends` writes, and every skill document naming
    a key.
  - Open items: `tcw work list --status backlog` and `--status active`, searched
    for configuration, tracker, tag and skill changes.
