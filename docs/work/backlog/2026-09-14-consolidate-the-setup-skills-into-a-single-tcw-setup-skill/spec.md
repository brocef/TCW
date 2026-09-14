# Spec — Consolidate the setup skills into a single tcw-setup skill

## Capability changes

Planned ledger changes only; nothing is written to the ledger at this stage.

```yaml
new:
    - plugin/set-up-or-reconfigure-tcw
changed:
    - plugin/bootstrap-the-cli
    - taxonomy/bootstrap-the-taxonomy
    - capabilities/bootstrap-the-capabilities
```

- **New — `plugin/set-up-or-reconfigure-tcw`.** "As a user, I ask my agent to
  set up or change the configuration of any part of TCW — installing the CLI,
  setting up a repository, starting a taxonomy or capabilities ledger, binding my
  own instructions to lifecycle stages, declaring documentation entries — and one
  skill, `tcw-setup`, takes me to the right instructions, under Claude and Codex
  alike." Seeded `Missing` at planning, flipped at completion.
- **Changed — `plugin/bootstrap-the-cli`** (`cap-17ca61`). Its description names
  "the `tcw-plugin` setup" and "the `tcw-plugin` skill"; both become `tcw-setup`.
  The behavior it describes does not change.
- **Changed — `taxonomy/bootstrap-the-taxonomy`** (`cap-3dffc1`) and
  **`capabilities/bootstrap-the-capabilities`** (`cap-559231`). Both open "I run
  `/tcw-taxonomy-init`" / "`/tcw-capabilities-init`". Those commands are deleted,
  so each is reworded to "I ask my agent to set up …, and the `tcw-setup` skill
  …". The four-step procedure they describe does not change.

Checked and **not** affected: `plugin/install-as-a-plugin` (names no skill),
`work/configure-the-work-lifecycle`, `work/customize-the-definition-of-done`,
`work/declare-which-documents-track-which-changes`, and
`work/read-the-documentation-gate-for-a-change` — they describe what the
configuration does, not which skill explains it. `tcw capabilities check` is
clean today.

**Taxonomy.** `tcw taxonomy search` for `skill`, `plugin`, and `setup` finds
nothing but the `configurable-work-lifecycle` Feature, which this item does not
change. No Vocabulary or Feature entry is added or changed.

## Problem

Setup material is spread across four skills and three slash commands, and
nothing about the names says which skills are for setting TCW up and which are
for using it:

| Setup material | Where it lives today |
| --- | --- |
| Installing or repairing the `tcw` CLI | `skills/tcw-plugin/SKILL.md:62-115` |
| Starting a taxonomy | `commands/tcw-taxonomy-init.md:5` → `skills/tcw-taxonomy/references/init.md` (61 lines) |
| Starting a capabilities ledger | `commands/tcw-capabilities-init.md:5` → `skills/tcw-capabilities/references/init.md` (32 lines) |
| Declaring documentation entries | `commands/tcw-docs-sync-setup.md:7` → `skills/documentation-sync/references/setup.md` (62 lines) |
| Binding instructions to lifecycle stages | `skills/tcw-work/references/hooks.md:1-41` |
| `tcw init`, `tcw provision`, where the stores live | No setup document. Only refusal-handling text in usage skills (`skills/tcw-taxonomy/SKILL.md:30-36`, `skills/tcw-capabilities/SKILL.md:17-24`) and `skills/tcw-work/references/commands.md:150-210` |

Four concrete consequences:

1. **Setup requests go to usage skills.** `tcw-taxonomy`'s `description` and
   `when_to_use` both list "bootstrapping a taxonomy from an existing codebase"
   (`skills/tcw-taxonomy/SKILL.md:3-4`). A setup request therefore loads the
   whole taxonomy usage skill just to follow a pointer to `references/init.md`
   (`:104-107`).
2. **Two ways to do one thing.** Each setup procedure can be reached through a
   slash command or through a usage skill's pointer. Codex has no slash commands,
   so a Codex user only has the second way.
3. **`tcw-plugin` is two unrelated things in one skill.** Its first half is a
   map of the other skills (`skills/tcw-plugin/SKILL.md:12-60`). Its second half
   is CLI installation (`:62-115`). Its name describes neither.
4. **Nothing explains setting up a repository.** How to run `tcw init` and
   `tcw provision`, and where the stores live, is only explained at the moment a
   command refuses.

## Goals

1. Exactly **one** skill, `tcw-setup`, is the place for setting up TCW and for
   changing its configuration later.
2. `tcw-setup/SKILL.md` only routes. It says which reference document covers
   which situation, and the reference documents hold the instructions.
3. The usage skills keep their names. They stop presenting themselves as setup
   skills, and each keeps a single line pointing to `tcw-setup`.
4. There is one way into each setup procedure, and it works the same under
   Claude and Codex.
5. The spread-out setup material is moved, not rewritten. Procedures that work
   today keep working.

## Non-goals

- Renaming or restructuring any usage skill beyond removing its setup material:
  `tcw-work`, `tcw-taxonomy`, `tcw-capabilities`, `documentation-sync`, the six
  `tcw-work-stage*` skills.
- The skills that are neither setup nor ordinary usage: `tcw-report`,
  `tcw-triage-issues`, `tcw-post-mortem`, `autonomous-work`.
- Any change to the `tcw` CLI, including what `tcw init` prints.
- Keeping stub commands or a stub `tcw-plugin` under the old names. The requester
  decided nobody else uses TCW yet.
- Rewriting history: completed work items under `docs/work/`, and changelogs and
  release notes of past versions, keep the names they were written with.
- Setup instructions for the external tracker (Jira). That configuration is being
  built right now by the active item
  `2026-08-04-supplement-filesystem-tcw-work-with-an-external-tracker-bridge`.
  Whichever of the two items lands second places its setup text in `tcw-setup`
  (see Risks).
- Separating the plugin from the Python source
  (`2026-08-12-separate-the-agent-plugin-from-the-python-cli-source`), and
  refining skills against eval results
  (`2026-09-11-refine-the-plugin-skills-and-lifecycle-prompts-against-the-eval-findings`).
- The work-item tag vocabulary (`skills/tcw-work/references/tags.md`). Tags are
  chosen while filing work, so that document stays with `tcw-work`.

## Design

### The skill set after this change

`skills/` still holds **fifteen** skills. `tcw-plugin` is removed and `tcw-setup`
is added, so the count stays the same and the Codex manifest keeps saying
"fifteen skills". The grouping below is for the reader only; it is not a folder
structure.

| Group | Skill | Change |
| --- | --- | --- |
| **Setting up** | `tcw-setup` | **new** — replaces `tcw-plugin` and absorbs the setup documents below |
| **Using TCW** | `tcw-work` | loses the configuration half of `references/hooks.md`; points to `tcw-setup` |
| | `tcw-taxonomy` | loses `references/init.md` and "bootstrapping" from its description; points to `tcw-setup` |
| | `tcw-capabilities` | loses `references/init.md`; points to `tcw-setup` |
| | `documentation-sync` | loses `references/setup.md`; points to `tcw-setup` |
| | `tcw-work-stage` | unchanged |
| | `tcw-work-stage-request` | unchanged |
| | `tcw-work-stage-spec` | unchanged |
| | `tcw-work-stage-plan` | unchanged |
| | `tcw-work-stage-implement` | unchanged |
| | `tcw-work-stage-verify` | unchanged |
| | `tcw-triage-issues` | unchanged |
| | `tcw-post-mortem` | unchanged |
| | `autonomous-work` | unchanged |
| **Reporting to TCW** | `tcw-report` | unchanged |
| *(removed)* | ~~`tcw-plugin`~~ | install half → `tcw-setup`; skill map deleted |

The resulting tree:

```
skills/
  autonomous-work/
  documentation-sync/
    SKILL.md
    references/
      cut-version.md
      release-notes-and-changelogs.md
  tcw-capabilities/
    SKILL.md
  tcw-post-mortem/
  tcw-report/
  tcw-setup/                     # new
    SKILL.md                     # routing only
    references/
      install.md                 # CLI and plugin, once per machine; missing or stale CLI
      project.md                 # tcw init / provision / validate; where stores live
      taxonomy.md                # starting a taxonomy
      capabilities.md            # starting a capabilities ledger
      work.md                    # lifecycle bindings; Definition of Done
      docs-sync.md               # documentation entries
  tcw-taxonomy/
    SKILL.md
  tcw-triage-issues/
  tcw-work/                      # references/ otherwise unchanged
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

### D1 — One skill, not `tcw-setup` plus `tcw-config`

The requester allowed configuration changes to go in `tcw-setup` only if they do
not greatly increase its size. They don't, for two reasons:

- **The configuration material and the setup material are the same documents.**
  Declaring documentation entries (`documentation-sync/references/setup.md`)
  covers both first-time setup and later changes. Lifecycle bindings
  (`hooks.md:1-41`) and the Definition of Done file are written the same way
  whether it's day one or month six. A `tcw-config` skill would route to the
  same reference documents as `tcw-setup`.
- **Only `SKILL.md` and the description are loaded up front.** Reference documents
  are read only when the router sends the model to one. Covering configuration
  changes adds a clause to the description and nothing to the router table,
  because every row already covers both.

**The size test, pinned:** the body of `tcw-setup/SKILL.md` (everything after
the closing `---` of the frontmatter) is at most **60 lines**. That is the same
budget and the same counting rule `tests/test_skill_lifecycle_parity.py:50,276-285`
applies to `tcw-work`. If the implementation cannot fit in that budget, that is
the signal for `tcw-config`. Splitting would then be a spec change taken back to
the requester, not something the plan or the implementation decides alone.

### D2 — `tcw-setup/SKILL.md` routes and nothing else

The body holds:

- A short statement of what the skill is for.
- **A routing table** with columns *situation* → *document*: one row per
  reference document, with the situation described in the user's words ("`tcw`
  is not found, or `tcw --version` fails", "set up a new repository", "start a
  taxonomy for existing code", …).
- One rule on order for first-time setup: install, then project, then taxonomy
  before capabilities. That ordering exists today at
  `skills/tcw-capabilities/references/init.md:7-9`.

The body holds **no** procedure steps.

**Frontmatter:**

- `name: tcw-setup`.
- The `description` names three situations: first-time setup of any part, changing
  TCW's configuration later, and a `tcw` that is missing, broken, or stale. The
  third must stay explicit. It is the trigger `tcw-plugin` carries today
  (`skills/tcw-plugin/SKILL.md:3-4`), and in practice it is the most common
  reason that skill gets opened: the `SessionStart` hook
  (`hooks/hooks.json`, `scripts/session_bootstrap.sh`) handles the ordinary case.
- `when_to_use` is filled in, as on the other skills.
- `allowed-tools` (the Claude list of tool calls a skill may make without asking)
  is the **union** of the lists on the skills whose material moves:
  `skills/tcw-plugin/SKILL.md:5`, plus `Read, Grep, Glob` from
  `skills/tcw-taxonomy/SKILL.md:5`. Nothing is added beyond that union, so this
  change grants no new permissions.
- `compatibility`, `metadata`, and `license` carry over from
  `skills/tcw-plugin/SKILL.md:6-9`.

**Harness rule.** Under Claude the skill can be invoked with a hint
(`/tcw:tcw-setup taxonomy`). Skill arguments are Claude-only, so that is a
convenience, never the route. The routing table must let a model pick the right
document from the user's request alone. The body must not depend on
`$ARGUMENTS` or on dynamic context injection (`` !`cmd` ``, which runs a command
and inserts its output into the skill under Claude only).

### D3 — Where each reference document comes from

| New document | Source | How |
| --- | --- | --- |
| `install.md` | `skills/tcw-plugin/SKILL.md:62-115` | **Moved.** Only wording that names the old skill changes. |
| `project.md` | *(none)* | **New, short.** `tcw init` and the per-component `init`s (`README.md:336-351`), `tcw provision`, and `tcw validate` as the closing check. Also how `taxonomy.path` / `capabilities.path` / `work.path` and a `repository` block choose where each store lives. For store behavior at runtime it points to `tcw-work`'s `commands.md`, which keeps that content (§ D4). |
| `taxonomy.md` | `skills/tcw-taxonomy/references/init.md` | **Moved** (`git mv`). |
| `capabilities.md` | `skills/tcw-capabilities/references/init.md` | **Moved** (`git mv`). Line 9's "point the user at `/tcw-taxonomy-init`" becomes a pointer to `taxonomy.md`. |
| `work.md` | `skills/tcw-work/references/hooks.md:1-41` and `:97-98`; how to set `docs/work/dod.yaml` | **Moved** (binding shape, roles, kinds, `when:`, and the trust note). The Definition of Done setting is **new text**: today it is one clause at `skills/tcw-work/references/transitions.md:112`, which stays. |
| `docs-sync.md` | `skills/documentation-sync/references/setup.md` | **Moved** (`git mv`). Its "see `SKILL.md`'s Trigger Reference" pointers (`:34`, `:37`) name the `documentation-sync` skill explicitly, because they now cross from one skill to another. |

A pointer from one skill to another names the **skill** and the document ("the
`tcw-setup` skill's `references/taxonomy.md`"), matching how commands already
refer to skill files (`commands/tcw-taxonomy-init.md:5`).

### D4 — What each usage skill loses and keeps

- **`tcw-taxonomy`**:
  - Remove "bootstrapping a taxonomy from an existing codebase" from `description`
    and `when_to_use` (`SKILL.md:3-4`), so setup requests route to `tcw-setup`.
  - Remove "See `tcw-plugin` for the cross-skill map." (`:24-25`).
  - Replace the `## Bootstrap` section (`:104-107`) with one line pointing to
    `tcw-setup`.
  - The refusal text for unprovisioned stores (`:30-36`) **stays**: it is what an
    agent needs when a command refuses during use.
- **`tcw-capabilities`**:
  - Replace `## Bootstrap` (`SKILL.md:117-120`) with one line pointing to
    `tcw-setup`.
  - The refusal text at `:17-24` stays.
- **`tcw-work`**:
  - Delete "`tcw-plugin` maps the skills." (`SKILL.md:19-20`).
  - `:55` keeps its pointer to `hooks.md` for what bindings do at runtime, and
    adds a pointer to `tcw-setup` for declaring them.
  - `references/hooks.md` keeps "The three verbs" (`:43-66`), "What runs, and what
    does not" (`:68-84`), and "Two limits worth knowing" (`:86-95`). All of those
    describe behavior an agent meets while running a stage.
  - The body stays within its existing 60-line budget.
- **`documentation-sync`**:
  - The three references to `references/setup.md` (`SKILL.md:15`, `:29`, and the
    table row at `:98`) point to `tcw-setup`'s `docs-sync.md` instead.
  - The skill otherwise stays whole, because it also serves projects that don't
    use TCW. The same plugin ships both skills, so `tcw-setup` is always present
    wherever `documentation-sync` is.

### D5 — The skill map is deleted

`skills/tcw-plugin/SKILL.md:12-60` is not moved anywhere. Everything in it is
already said by a skill that stays:

| What the map says | Already said at |
| --- | --- |
| The order `Vocabulary → Features → Capabilities → Work` | `skills/tcw-work/SKILL.md:17`, `skills/tcw-taxonomy/SKILL.md:20` |
| Capabilities point loosely at a `Subject`, strongly at a `Feature` | `skills/tcw-capabilities/SKILL.md:27` |
| The axes point forward; taxonomy never points back | `skills/tcw-taxonomy/SKILL.md:23-24` |
| `tcw-work` runs the capability gate for product changes | `skills/tcw-work/SKILL.md:18-19` |
| `tcw-report` sends feedback to TCW; `tcw-triage-issues` reads the user's own issues | both skills' `description` fields |
| Which axis skill to use for which kind of request | each axis skill's `description`; `tcw-taxonomy` and `tcw-capabilities` also name their neighbours (`:3`) |

### D6 — Everything else that names the removed things

| File | Change |
| --- | --- |
| `commands/tcw-taxonomy-init.md`, `commands/tcw-capabilities-init.md`, `commands/tcw-docs-sync-setup.md` | Deleted. |
| `scripts/session_bootstrap.sh:9`, `:45` | The comments name `tcw-setup` and its `install.md`. |
| `README.md:217`, `:227` | `tcw-plugin` → `tcw-setup`. |
| `README.md:352` | Replace the two slash commands with asking for the `tcw-setup` skill. |
| `README.md:440` | The table row becomes `tcw-setup`: "Sets TCW up and changes its configuration: the CLI, a repository, taxonomy, capabilities, lifecycle, documentation entries". |
| `README.md:470-471` | Drop the three commands from the list. |
| `docs/guide/taxonomy-and-capabilities.md:59` | As `README.md:352`. |
| `.codex-plugin/plugin.json` `longDescription` | "tcw-plugin for installing and repairing the CLI" → "tcw-setup for setting TCW up, changing its configuration, and repairing the CLI". The count stays "fifteen skills". |
| `tests/test_documentation_sync_wiring.py:13-19`, `:23-26` | `SKILL_FILES` drops `references/setup.md`. The `COMMAND_ROUTES` entry for `tcw-docs-sync-setup` goes; the `tcw-cut-version` entry stays. |
| `tests/test_plugin_manifests.py:4` | The docstring names `tcw-setup`. |
| `evals/evals.json` case `B5` | Removed. It measured the skill map (`evals/evals.json:592-622`), which no longer exists. |
| `evals/coverage.py:46-57` | The `PARTIAL` entry moves to `tcw-setup`, with the reason rewritten: the install/repair route stays deliberately unmeasured, for the reason already given there. |
| `evals/evals.json` — new case | A `tcw-setup` case with `with-skill` and `no-skill` arms, so `tests/test_eval_coverage.py` still finds every shipped skill covered. It measures one mechanical route: "set up documentation entries for demo-app so the README tracks public API changes". It asserts that `tcw work docs --json` reports `source: config` with a `README.md` entry, and that `tcw validate` exits 0. Each assertion is mutation-checked (deliberately broken to confirm it goes red) before it is trusted, as `CLAUDE.md` § Measuring the skill layer requires. Running the eval (which costs money) is not part of this item. |
| `docs/capabilities/…` | The three changed capabilities and one new one, per **Capability changes**. |
| `docs/changelogs/upcoming.md`, `docs/release-notes/upcoming.md` | Record the removed commands and skill, and the new skill. |

### Abstraction and harness checks

- **Abstraction litmus test.** No store operation is added, changed, or removed.
  This item only reorganizes agent-facing documents, so the test has nothing to
  act on.
- **Harness.** Every setup procedure becomes reachable by invoking a skill, which
  both Claude and Codex can do. Deleting the three slash commands removes a
  Claude-only way in without removing any capability from either harness. D2
  forbids depending on arguments or on context injection.

## Acceptance criteria

Each is checked from the repository root after implementation.

1. `ls skills` lists exactly: `autonomous-work documentation-sync
   tcw-capabilities tcw-post-mortem tcw-report tcw-setup tcw-taxonomy
   tcw-triage-issues tcw-work tcw-work-stage tcw-work-stage-implement
   tcw-work-stage-plan tcw-work-stage-request tcw-work-stage-spec
   tcw-work-stage-verify`.
2. `ls skills/tcw-setup/references` lists exactly: `capabilities.md docs-sync.md
   install.md project.md taxonomy.md work.md`.
3. None of these exist: `skills/tcw-plugin/`,
   `skills/tcw-taxonomy/references/init.md`,
   `skills/tcw-capabilities/references/init.md`,
   `skills/documentation-sync/references/setup.md`,
   `commands/tcw-taxonomy-init.md`, `commands/tcw-capabilities-init.md`,
   `commands/tcw-docs-sync-setup.md`.
4. `git grep -nE 'tcw-plugin|tcw-taxonomy-init|tcw-capabilities-init|tcw-docs-sync-setup' -- . ':!docs/work' ':!docs/changelogs' ':!docs/release-notes'`
   prints nothing. `docs/changelogs/upcoming.md` and
   `docs/release-notes/upcoming.md` name each of the four as removed.
5. The body of `skills/tcw-setup/SKILL.md`, counted as in
   `tests/test_skill_lifecycle_parity.py:280-282`, is at most 60 lines. It links
   each of the six reference documents, and every relative link in it resolves to
   a file.
6. `skills/tcw-setup/SKILL.md` contains neither `$ARGUMENTS` nor `` !` ``.
7. The `description` of `skills/tcw-setup/SKILL.md`, compared case-insensitively,
   contains each of `missing`, `stale`, `taxonomy`, `capabilities`,
   `lifecycle`, `documentation`, and `configuration`.
8. Neither `description` nor `when_to_use` in `skills/tcw-taxonomy/SKILL.md`
   contains `bootstrap`, compared case-insensitively.
9. Each of `skills/tcw-work/SKILL.md`, `skills/tcw-taxonomy/SKILL.md`,
   `skills/tcw-capabilities/SKILL.md`, and `skills/documentation-sync/SKILL.md`
   contains `tcw-setup`. None contains a `## Bootstrap` heading.
10. `git log --follow --oneline` on each of `skills/tcw-setup/references/taxonomy.md`,
    `capabilities.md`, and `docs-sync.md` reaches commits made before this item.
    That is, git detects each as a rename, not as a delete plus a new file.
11. `skills/tcw-setup/references/install.md` contains the rule for a developer's
    editable install (`dir_info.editable`) and `pipx install tcw-cli`.
    `skills/tcw-setup/references/work.md` contains the `blob:`, `file:`,
    `generate:`, `builtin:`, and `skill:` kinds, and `dod.yaml`.
12. `skills/tcw-work/references/hooks.md` still contains
    `tcw work stage gate` and "`tcw serve` runs no hooks". It no longer contains
    the `| Role` roles table.
13. Bare `pytest` (not `python -m pytest`, which is how CI runs it) passes.
14. `tcw validate` exits 0, and `tcw capabilities check` prints `capabilities OK`.
15. `evals/evals.json` has no case whose `skill` or `invokes` is `tcw-plugin`,
    and has one whose `invokes` is `tcw-setup`. `evals/coverage.py` `PARTIAL` has
    no `tcw-plugin` key.
16. `tcw capabilities show` on `plugin/bootstrap-the-cli`,
    `taxonomy/bootstrap-the-taxonomy`, and
    `capabilities/bootstrap-the-capabilities` prints none of the four removed
    names. `plugin/set-up-or-reconfigure-tcw` exists, with `Status: Supported`
    at completion.

## Risks

- **Setup requests still land in usage skills.** If a usage skill's
  description keeps describing setup, the model keeps choosing it. AC 8 covers
  the one description that does so today. A reviewer should read the other axis
  descriptions for the same problem.
- **A Codex user reaches the router with no hint.** D2 and AC 6 make the table,
  not an argument, carry the routing. Whether the table is clear enough is a
  judgment only a reviewer, or an eval run, can make.
- **Other open work items cite files that move.**
  - `2026-08-18-report-the-missing-skill-caveat-from-tcw-work-lifecycle-rather-than-the-skill`
    quotes `skills/tcw-work/references/hooks.md:83`. That text stays in
    `hooks.md`, but its line number shifts.
  - `2026-08-12-separate-the-agent-plugin-from-the-python-cli-source` names
    `skills/tcw-plugin/…` throughout its `plan.md`. Those paths were already
    stale (its `references/` tree was deleted in v2.0.3,
    `docs/changelogs/v2.0.3.md:150-152`), and this item makes them more so.
  - Implementation adds a one-line note to each of those items rather than
    rewriting their documents.
- **The external tracker item adds configuration at the same time.** The active
  bridge item is adding Jira configuration. If it lands first, this item routes
  to its setup text. If this item lands first, that item's setup text goes into
  `tcw-setup`, and a note on the bridge item says so.
- **The new eval case costs setup work.** It needs a fixture and mutation-checked
  assertions (D6). The cheaper option is an `EXCLUSIONS` entry in
  `evals/coverage.py`, but that coverage gate treats an exclusion as a deliberate
  decision not to measure, and the documentation-entries route can be measured
  mechanically. This is flagged for the requester to confirm in Notes.
- **Material lost in moving.** AC 10 and AC 11 check that the moved documents
  arrive whole and keep their history. The Definition of Done text in `work.md`
  and all of `project.md` are new writing, and get reviewed as such.

## Notes

- **For the requester to confirm:** a new eval case for `tcw-setup` (D6) versus
  an exclusion. The spec chooses the case.
- **Assumption, not verified:** that `tcw-plugin` is "mostly" opened when the
  CLI is broken. It rests on the skill's own description and on the automatic
  install covering the ordinary case; no usage data was checked. The design does
  not depend on it — the broken-CLI trigger stays either way.
- **Sweep for sibling cases.** The search for the removed names covered the
  whole repository (AC 4's command, plus the manifests, hooks, scripts, tests,
  evals, capability ledger, and taxonomy). It was narrowed only to exclude
  history (`docs/work/`, and changelogs and release notes of past versions),
  which is a non-goal.
