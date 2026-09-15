# Spec — Drop the `tcw-` prefix from the plugin's skill and agent names

## Capability changes

**Changed — 15.** Every capability under `skills/` except `skills/documentation-sync`
is renamed to its path minus the `tcw-` prefix, and its body is reworded where it
names the skill:

| today | after |
| ----- | ----- |
| `skills/tcw-work` | `skills/work` |
| `skills/tcw-work-stage` | `skills/work-stage` |
| `skills/tcw-work-create` | `skills/work-create` |
| `skills/tcw-capabilities` | `skills/capabilities` |
| `skills/tcw-taxonomy` | `skills/taxonomy` |
| `skills/tcw-setup` | `skills/setup` |
| `skills/tcw-configure` | `skills/configure` |
| `skills/tcw-post-mortem` | `skills/post-mortem` |
| `skills/tcw-commands-plan-work` | `skills/commands-plan-work` |
| `skills/tcw-commands-drive-work-to-completion` | `skills/commands-drive-work-to-completion` |
| `skills/tcw-commands-verify-work` | `skills/commands-verify-work` |
| `skills/tcw-commands-process-inbox` | `skills/commands-process-inbox` |
| `skills/tcw-extras-autonomous-work` | `skills/extras-autonomous-work` |
| `skills/tcw-extras-triage-issues` | `skills/extras-triage-issues` |
| `skills/tcw-extras-report` | `skills/extras-report` |

**New — none. Removed — none.** Each renamed entry keeps `Status: Supported`, its
`Subject`, its `Planning doc` pointer and its body; what changes is the path it is
addressed by, its `Feature` pointer, and the name its prose quotes. `tcw capabilities`
has no rename verb (`tcw capabilities --help`: `init, list, show, path, add, set, reset,
rm, search, extends, check, drift`), so each is re-created and the old one removed —
see **Design 4**, and **Risks** for what that costs.

`skills/documentation-sync` (`cap-301436`) is unchanged: it already carries no prefix
and is the shape the other fifteen are moving to.

The 15 matching taxonomy Features are renamed alongside them (**Design 3**). Taxonomy
entries are not capabilities and are listed here only because the two move together.

The three subagents have no capability in the ledger — `tcw capabilities list` returns
nothing under `agents` or for `backlog-auditor` / `verifier`. Renaming them is therefore
a change with no ledger delta. That gap is pre-existing and is left alone (**Non-goals**).

## Problem

Every skill this plugin ships is addressed through the plugin's own namespace, and
then repeats it. `skills/tcw-work/SKILL.md:2` declares `name: tcw-work`, so Claude
invokes it as `/tcw:tcw-work` and Codex as `$tcw:tcw-work`. Fifteen of the sixteen
shipped skills are like this; the fifteenth, `skills/documentation-sync/SKILL.md:2`,
declares `name: documentation-sync` and is invoked as `/tcw:documentation-sync`.

The plugin id is not in doubt at the point of use: `.claude-plugin/plugin.json`
sets `"name": "tcw"` and `"skills": "./skills/"`, and `.codex-plugin/plugin.json`
does the same, so the host has already qualified the name before the skill's own
name is read. The prefix therefore adds four characters and a stutter and
distinguishes nothing.

The same doubling reaches the three subagents. `agents/tcw-verifier.md:2` declares
`name: tcw-verifier`, and `agents/tcw-post-mortem.md:2` declares `name:
tcw-post-mortem` — which is also the name of the skill at
`skills/tcw-post-mortem/SKILL.md:2`. After the skills are renamed and the agents are
not, the pair reads `tcw:post-mortem` (skill) beside `tcw:tcw-post-mortem` (agent):
the request's own complaint, preserved in the one place it is most confusing.

TCW names each skill twice more, in its own two other axes, and there the prefix is
redundant for a second reason — every entry in TCW's taxonomy and ledger is TCW's:

- a Feature per skill, `docs/taxonomy/tcw-work-skill/` through
  `docs/taxonomy/tcw-extras-report-skill/`, which `docs/capabilities/skills/tcw-work/meta.yaml:5`
  points at as `Feature: tcw-work-skill`;
- a capability per skill, the sixteen folders under `docs/capabilities/skills/`.

Both already show the intended shape once. `docs/taxonomy/documentation-sync-skill/meta.yaml:1`
reads `name: TCW Documentation Sync Skill` over the slug `documentation-sync-skill` —
the display name identifies the project, the slug does not repeat it. The other
fifteen Features carry the prefix in the slug as well
(`docs/taxonomy/tcw-commands-plan-work-skill/meta.yaml:1`, `name: TCW Plan Work Command Skill`).
So the fix is not a new convention; it is applying the one `documentation-sync`
already follows to the other fifteen.

Nothing about this is load-bearing in the CLI. Skill names reach `tcw` only as opaque
`skill:` binding refs (`tcw/store/base.py:961`, `BINDING_KINDS`; resolved at
`tcw/work/resolve.py:193` and `tcw/work/hooks.py:88`), and no real project binds one —
the only `skill:` bindings in this workspace are the invented fixture values under
`tests/fixtures/lifecycle_baseline/` (`skill: x`, `skill: tdd`,
`skill: superpowers:brainstorming`). The whole of `tcw/` mentions a skill by name in
one docstring, `tcw/work/templates.py:7`. This is a plugin, docs, test and eval-harness
change, not a CLI behavior change.

What it is not free of is references. Roughly 100 live files name a skill, among them:

- `tcw-config.yaml:40`, whose documentation entry `path` is literally
  `skills/tcw-configure/references/<document>.md` — a **configured path**, not prose,
  and the one place the rename changes configuration rather than text;
- `.codex-plugin/plugin.json`, whose `longDescription` enumerates all sixteen skills
  by name in prose, guarded by `tests/test_plugin_manifests.py:93`, which reads the
  names from the `skills/` directory and asserts the description both counts and names
  every one of them;
- `evals/coverage.py:34` and `:52`, whose `EXCLUSIONS` and `PARTIAL` maps are **keyed
  by skill directory name** and compared against that same glob at `:78`, so a rename
  that misses them turns live entries into dead keys;
- `evals/evals.json`, where cases carry `"skill"` and `"invokes"` values naming skills;
- the skill bodies themselves, which route to each other by name throughout
  `skills/*/SKILL.md` and `skills/tcw-work/references/**`;
- `README.md:587-629`, which tables and describes every skill and the three agents;
- the suites that hardcode names or paths — `tests/test_skill_lifecycle_parity.py:26-27`
  (`skills/tcw-work/SKILL.md`, `skills/tcw-work/references`), `:315`
  (`skills/tcw-work-stage/SKILL.md`), `:433`, `tests/test_skill_path_pointers.py:17`
  (parametrized over `"tcw-setup"`, `"tcw-configure"`), and others.

And one guard that should exist does not. `tests/test_plugin_manifests.py:131`
checks that each `SKILL.md` *has* `name` and `description` frontmatter, but never that
`name` equals the directory it sits in. A rename that moves the directory and leaves
the frontmatter behind passes the whole suite today.

## Goals

1. No skill this plugin ships carries the plugin's own id in its name, so
   `/tcw:commands-plan-work` and `$tcw:commands-plan-work` are how the plan-work skill
   is invoked.
2. The same for the three subagents, so no `tcw:tcw-…` address survives anywhere.
3. TCW's taxonomy Features and capability entries name the skills that actually ship.
4. The invariant is pinned by a test, so the prefix cannot come back by accident and a
   directory rename can no longer drift from its frontmatter.
5. The rename touches nothing else that begins with `tcw-`.
6. The historical record keeps saying what it said.

## Non-goals

- **The `commands-` and `extras-` groupings stay.** Stripping them too was offered and
  declined; they group the families in a listing.
- **`documentation-sync` does not change** — it is already the target shape.
- **No compatibility alias for the old names.** Neither harness offers a skill-alias
  mechanism, so an alias would mean shipping fifteen stub skills that exist to be
  wrong; the old names simply stop resolving. See **Risks**.
- **No `mv` / rename verb is added to `tcw capabilities` or `tcw taxonomy`.** Adding
  one is a CLI surface change with its own storage-abstraction question, and it is
  filed rather than folded in (**Notes**).
- **`tcw taxonomy rm`'s behavior is not changed.** It deletes nested terms silently and
  only warns on dangling `relatesTo` (already filed as
  `docs/work/inbox/tcw-taxonomy-rm-deletes-nested-terms-without-a-word.md`). This spec
  works within it — the fifteen skill Features are flat, not nested — rather than
  fixing it.
- **No capability is created for the three subagents.** They have none today; adding
  them is a ledger-completeness question, not this rename.
- **Downstream repositories are not edited.** `proposit-orchestration`,
  `proposit-app` and `proposit-core` name TCW skills in `AGENTS.md` prose and in
  `tcw-config.yaml` documentation *descriptions*, but none binds a skill in a
  lifecycle hook, so none breaks. Their prose goes stale and is theirs to update.
- **No skill's content, routing or behavior changes** beyond the names it uses.

## Design

Seven rules. Each says what changes and what must not.

### 1. Skills

The 15 prefixed directories under `skills/` are renamed to the directory name minus
the leading `tcw-`, and each `SKILL.md`'s frontmatter `name:` is set to the new
directory name. `skills/documentation-sync/` is untouched.

`skills/tcw-work` → `skills/work`, `tcw-work-stage` → `work-stage`,
`tcw-work-create` → `work-create`,
`tcw-capabilities` → `capabilities`, `tcw-taxonomy` → `taxonomy`, `tcw-setup` →
`setup`, `tcw-configure` → `configure`, `tcw-post-mortem` → `post-mortem`, the four
`tcw-commands-*` → `commands-*`, the three `tcw-extras-*` → `extras-*`.

Directories move with `git mv`, so `references/` subtrees follow and history is
preserved. These are plugin source files, not a TCW store — no store operation is
involved (see **Abstraction litmus test**).

### 2. Agents

`agents/tcw-backlog-auditor.md` → `agents/backlog-auditor.md`,
`agents/tcw-verifier.md` → `agents/verifier.md`,
`agents/tcw-post-mortem.md` → `agents/post-mortem.md`, each with its frontmatter
`name:` set to the new basename. No manifest lists them — `.claude-plugin/plugin.json`
carries no `agents` key and Claude auto-loads `agents/`, which
`tests/test_plugin_manifests.py` records at its `test_claude_agents_key_is_md_files_not_a_directory`
— so nothing outside the files themselves and their references needs to change.

### 3. Taxonomy Features

The 15 prefixed Feature slugs lose the prefix: `tcw-work-skill` → `work-skill`,
… , `tcw-extras-report-skill` → `extras-report-skill`. **Display names are not
touched**: `name: TCW Work Skill` stays, matching `documentation-sync-skill`, which
already pairs a "TCW …" display name with an unprefixed slug.

There is no rename verb, so each is re-created through the CLI and the old one removed:

```
tcw taxonomy add "<display name>" --kind feature -s <new-slug> --vocab <each vocab ref>   # body piped from the old description.md
# hand-edit relatesTo in the new meta.yaml — the tcw-taxonomy skill's own route for that field
tcw taxonomy rm <old-slug>                                                                 # only after rule 4 has re-pointed the capability
```

`relatesTo` and `vocabulary` are carried over verbatim (e.g. `work-skill` keeps
`relatesTo: [work-inbox]` and `vocabulary: [skill, work-item, work-item/transition]`).
All 15 are flat top-level entries, so `tcw taxonomy rm`'s silent-nested-delete
behavior cannot bite.

### 4. Capabilities

The 15 prefixed capability paths under `skills/` lose the prefix. Same absence of a
rename verb, so per entry:

```
tcw capabilities add skills/<new> "<existing name>"
# copy the old description.md body into the new folder, rewriting the skill names it quotes
tcw capabilities set skills/<new> --status Supported \
    --field Feature=<new-feature-slug> --field Subject=skill \
    --field "Planning doc=<existing value>"
tcw capabilities rm skills/<old>
```

Metadata goes through `set` and deletion through `rm`, as the `tcw-capabilities`
skill requires ("Never hand-edit capability metadata when `set` applies, and never
delete a capability folder by hand", `skills/tcw-capabilities/SKILL.md:13`). The
`description.md` body has no command — no verb writes it — so it is authored
directly, which that rule does not cover.

**Ordering, across rules 3 and 4.** For each skill: add the new Feature, add the new
capability pointing at it, remove the old capability, then remove the old Feature.
Removing a Feature while a capability still points at it leaves `tcw taxonomy check`
failing after a command that reported success.

### 5. Live references follow

Every reference in a live file is updated to the new name. This covers, at minimum:
the 16 `SKILL.md` bodies and everything under `skills/*/references/`; `README.md`;
`docs/guide/work.md` and `docs/guide/taxonomy-and-capabilities.md`;
`docs/lifecycle/implementation.md`; `.codex-plugin/plugin.json`'s `longDescription`;
`tcw-config.yaml` — both its `path: skills/tcw-configure/references/<document>.md`
(line 40) and the skill names inside the `Skill-Driven-Component` description;
`evals/coverage.py`, `evals/evals.json`, `evals/grade.py`, `evals/assets/gen_requirement.py`;
`scripts/session_bootstrap.sh`; `tcw/work/templates.py:7`; the capability bodies under
`docs/capabilities/**`; `tests/**`; and `tests/cli/scenarios/11-scaffold-and-artifact-templates.md`.

### 6. `tcw-` that is not a skill or agent name does not change

A blind `s/tcw-//g` would corrupt the repository. These 14 tokens share the prefix and
are **not** names being renamed. Counted as whole words over the tree, excluding
`.git/`, `eval-runs/`, `tcw_cli.egg-info/` and every `work/` board directory (this
item's own artifacts name several of them, so the board would make the baseline move
under its own feet). "Whole word" here is a regex word boundary on each side, which
treats `-` as a boundary — so `tcw-ref` is counted inside `data-tcw-ref` and
`tcw-storage-folders` inside `cli/locate-tcw-storage-folders`. That is a looser test
than the substitution rule below uses, and deliberately so: it over-counts rather than
missing an occurrence the rename might have eaten:

| token | count | what it is | where it lives |
| ----- | ----: | ---------- | -------------- |
| `tcw-config` | 443 | `tcw-config.yaml`, the per-node configuration file | everywhere |
| `tcw-cli` | 100 | the PyPI distribution name | `scripts/`, `README.md`, `pyproject.toml` |
| `tcw-unhosted` | 14 | web state class | `web/client/src/`, `tcw/serve/dist/` |
| `tcw-inert` | 11 | web state class | `web/client/src/`, `tcw/serve/dist/` |
| `tcw-event` | 9 | tracker progress event kind | `tcw/tracker/progress.py`, `tests/`, `skills/work/references/commands.md` |
| `tcw-project-badge` | 8 | CSS class | `web/client/src/`, `tcw/serve/dist/` |
| `tcw-sr-only` | 5 | CSS class | `web/client/src/`, `tcw/serve/dist/` |
| `tcw-ref` | 4 | web identifier | `web/client/src/` |
| `tcw-sidecar-token` | 3 | request header | `web/server/src/`, `tcw/serve/dist/` |
| `tcw-serve` | 3 | inside the `web` capability's metadata | `docs/capabilities/web/meta.yaml` |
| `tcw-storage-folders` | 2 | tail of the capability path `cli/locate-tcw-storage-folders` | `docs/capabilities/cli/` |

Two more share the prefix and appear **only** in changelogs and release notes, so
rule 7 already protects them and they are listed here so nobody reads their absence
as an oversight: `tcw-doctor` (21) and `tcw-init` (10), both retired command names.
`tcw-plugin` (28) is the same case — and is already in
`tests/test_skill_lifecycle_parity.py`'s `DELETED_NAMES`, which is where retired names
are recorded (see rule 8).

Note that `tcw/serve/dist/` is committed build output carrying several of the web
identifiers. It is regenerated, never hand-edited, and nothing in this item touches it.

Renames are applied per known name — 15 skills and 3 agents, each substituted by its
full old name — never by stripping the prefix wherever it appears.

### 7. Historical records are not rewritten

Left byte-identical: `docs/changelogs/v*.md`, `docs/release-notes/v*.md` (the
`upcoming.md` in each is current, not historical, and does change),
`docs/migration-guide-0.21.X-to-1.0.0.md`, `docs/plan/**`, and every lifecycle
artifact under `docs/work/**` other than this item's own. They name skills that were
called that at the time. Several already name skills that no longer exist at all
(`tcw-plan-work`, `tcw-triage-issues`, `tcw-report` — the pre-restructure names),
which is the precedent.

### 8. The invariants get guards

Three changes, two new assertions and one extension of a guard that already exists
for precisely this.

**8a — the existing retired-name guard learns the 18 names.**
`tests/test_skill_lifecycle_parity.py:503` holds `DELETED_NAMES`, a tuple of skill and
command names that were removed or renamed, and `:526`'s
`test_no_live_route_names_a_removed_skill_or_command` asserts no file under
`LIVE_ROUTES` still names one — "a live document still naming one sends a reader to
something that is not there". That is this item's rule 5, already built and already
green for the previous restructure's casualties (`tcw-plan-work`, `tcw-triage-issues`,
`tcw-report`, …). The 15 old skill names and 3 old agent names are appended to it.

Its whole-name matching already handles the one collision that matters: the pattern
`(?<![-\w])tcw-work(?![-\w])` does not fire inside `tcw-work-stage`, so both can be
listed.

`LIVE_ROUTES` is currently `("skills", ".claude-plugin", ".codex-plugin", "README.md",
"docs/guide", "docs/lifecycle")` — it does not reach `agents/`, `tcw-config.yaml`,
`evals/` or `tests/`, all of which this rename touches. `agents/` and `tcw-config.yaml`
are added, since both are shipped surfaces that now name skills. `evals/` and `tests/`
are left out: they legitimately quote retired names (this very tuple is in `tests/`),
so adding them would make the guard fight itself. Criterion 9's wider grep is what
covers them, one time, at implementation.

Adding `agents/` and `tcw-config.yaml` subjects them to every *existing* entry in
`DELETED_NAMES` too. Checked: neither carries one today, so widening `LIVE_ROUTES` is
green before the renames start and any failure it reports afterwards is this item's.

**8b — a name matches the thing it names.** For every `skills/*/SKILL.md` and every
`agents/*.md`, the frontmatter `name` equals its directory or file basename. Nothing
checks this today: `tests/test_plugin_manifests.py:131` checks only that `name` and
`description` are *present*, which is exactly what would let this rename move a
directory and leave its frontmatter behind, with the suite green.

**8c — a name does not repeat its namespace.** No shipped skill or agent name begins
with the plugin id followed by `-`, with the id read from `.claude-plugin/plugin.json`
rather than hardcoded. Stated as the general rule, it keeps holding if the plugin is
ever renamed, and it is what stops the prefix creeping back one skill at a time.

All three must be mutation-checked before they are trusted, per `AGENTS.md`: break
what each claims to observe, confirm it goes red, and read why.

## Abstraction litmus test

**No operation is added or changed.** The `tcw` CLI's command surface, its store
interface, and its models are untouched by this item; `tcw/` sees one docstring edit
(rule 5, `tcw/work/templates.py:7`).

Two places where the question could arise, and why each is answered already:

- **Renaming a capability or a Feature.** Performed through operations that already
  exist and already pass the test — `add`, `set` and `rm` are model operations any
  store can implement. A rename *verb* would also pass it (a tracker can re-key an
  issue), which is precisely why its absence is a gap worth filing rather than a
  reason to reach around the interface. What is refused here is the shortcut: moving
  a store folder with `git mv` and editing `meta.yaml` by hand would be a filesystem
  trick with no analog in a Jira-backed store, and it is what rules 3 and 4 exist to
  avoid.
- **Renaming a skill or an agent directory.** `skills/` and `agents/` are plugin
  source shipped to Claude and Codex, not a TCW store; no store resolves a path inside
  them. `git mv` there is an ordinary source move and raises no abstraction question.

**Harness compatibility.** The rename is symmetric: both harnesses read the same
`SKILL.md` frontmatter and the same directory names, and each is given the same new
name. No requirement moves onto a Claude-only mechanism. The `agents/` directory is
Claude-specific packaging, and the two skills those agents accelerate
(`skills/tcw-work`'s audit route, `skills/tcw-post-mortem`) already stand alone
without them; renaming the files does not change that.

## Acceptance criteria

1. `ls skills/` lists exactly 16 directories and none begins with `tcw-`.
2. For every `skills/*/SKILL.md`, the frontmatter `name` equals the parent directory
   name; `skills/documentation-sync/SKILL.md` still reads `name: documentation-sync`.
3. `ls agents/` lists exactly 3 files — `backlog-auditor.md`, `verifier.md`,
   `post-mortem.md` — and each one's frontmatter `name` equals its basename.
4. Design 8's guards are mutation-checked, each shown red for the right reason:
   8b fails when a skill directory is renamed without its frontmatter; 8c fails when
   any shipped skill or agent name is given a `tcw-` prefix; 8a fails when a live-route
   file is made to name one of the 18 old names. Demonstrated, not asserted.
5. `tcw taxonomy list` shows exactly 16 Features whose slug ends `-skill`, none
   beginning `tcw-`, one per shipped skill; each keeps its `TCW …` display name, its
   `relatesTo`, and its `vocabulary` list from before the rename.
6. `tcw capabilities list` shows exactly 16 paths under `skills/`, none beginning
   `skills/tcw-`, one per shipped skill; each is `Supported`, carries `Subject: skill`,
   its original `Planning doc` value, and a `Feature` naming its renamed Feature.
7. `tcw taxonomy check`, `tcw capabilities check` and `tcw validate` each exit 0.
   (All three print OK on the tree today.)
8. `python -m pytest` is green, at no fewer than the 3367 passed / 2 skipped measured
   on this tree before the change.
9. No live file names a renamed skill or agent by its old name. Two checks, because
   the guard's reach is narrower than the tree: `test_no_live_route_names_a_removed_skill_or_command`
   passes with all 18 names in `DELETED_NAMES` and `agents/` + `tcw-config.yaml` in
   `LIVE_ROUTES`; and a one-time grep for the 18 names over everything else, excluding
   the paths rule 7 protects and the `DELETED_NAMES` tuple itself, returns nothing.
10. Every token in rule 6's table occurs exactly as often after the change as its
    count there, measured the same way (whole-word, excluding `.git/`, `eval-runs/`,
    `tcw_cli.egg-info/` and `work/`). `web/`'s CSS class names and the `tcw-cli`
    distribution name are untouched.
11. `git diff --stat` against the pre-change tree touches no file under
    `docs/changelogs/v*.md`, `docs/release-notes/v*.md`, `docs/plan/`,
    `docs/migration-guide-0.21.X-to-1.0.0.md`, or `docs/work/` outside this item's own
    folder.
12. `.codex-plugin/plugin.json`'s description still says "sixteen skills" and names all
    sixteen by their new names — i.e. `tests/test_plugin_manifests.py:93` passes
    without being weakened.
13. `evals/coverage.py`'s `EXCLUSIONS` and `PARTIAL` keys all name shipped skills, and
    `tests/test_eval_coverage.py` passes (it is what reports a skill with no eval case).
14. `python -m evals.run_evals --axis a --dry-run` resolves every arm and spawns
    nothing, with no unresolved skill name.
15. `tcw work docs` for this item shows every fired trigger addressed:
    `README.md`, `docs/release-notes/upcoming.md`, `docs/changelogs/upcoming.md`,
    `skills/<component>/SKILL.md`, and — because `tcw-config.yaml:40`'s configured
    `path` value itself changes — `skills/configure/references/<document>.md`.
16. `docs/release-notes/upcoming.md` states the rename as a breaking change and gives
    the old-name → new-name mapping for all 18 names, so a user whose muscle memory
    stops working can find it.

### Coverage

Rules are the Design's eight. `n/a` cells give the line that makes them so.

| # | 1 skills | 2 agents | 3 features | 4 capabilities | 5 references | 6 exclusions | 7 history | 8 guard |
| - | -------- | -------- | ---------- | -------------- | ------------ | ------------ | --------- | ------- |
| 1 | `test_no_shipped_name_repeats_the_plugin_id` | n/a — `agents/` is not `skills/*/SKILL.md` (`tests/test_plugin_manifests.py:130`) | n/a — taxonomy is not in `skills/` (`docs/taxonomy/`) | n/a — ledger is not in `skills/` (`docs/capabilities/`) | n/a — counts directories, reads no body | n/a — no listed token is a skill dir (Design 6) | n/a — no history under `skills/` | 8c |
| 2 | `test_skill_frontmatter_name_matches_its_directory` | n/a — same glob bound as row 1 | n/a | n/a | n/a — frontmatter only | n/a | n/a | 8b |
| 3 | n/a — `agents/` only | `test_agent_frontmatter_name_matches_its_file` | n/a | n/a | n/a | n/a | n/a | 8b, 8c |
| 4 | mutation check, skills arm | mutation check, agents arm | n/a — guard reads plugin source, not stores | n/a — same | n/a | n/a — id read from `plugin.json`, not a token list | n/a | all three mutation checks |
| 5 | n/a — Features are not skills | n/a | `tcw taxonomy list` + `tcw taxonomy check` | ref target checked by row 6's `Feature` | n/a — store state, not prose | n/a | n/a | n/a — not test-guarded, CLI-checked |
| 6 | n/a | n/a | `Feature` field resolves | `tcw capabilities list` + `tcw capabilities check` | n/a | n/a | n/a | n/a |
| 7 | indirectly — a stale `skill:`-free tree still validates | n/a | `tcw taxonomy check` | `tcw capabilities check` | `tcw validate` reads `tcw-config.yaml:40`'s path | n/a | n/a | n/a |
| 8 | `test_skill_*` suites | n/a — no agent suite exists today | n/a — no taxonomy-content suite | `tests/test_capabilities_rm.py` | `tests/test_skill_path_pointers.py`, `test_skill_lifecycle_parity.py`, `test_documentation_sync_wiring.py`, `test_shipped_prompts.py` | n/a — suite asserts no token counts | n/a — suite reads no history | 8a, 8b and 8c all run here |
| 9 | covered | covered by `agents/` in `LIVE_ROUTES` | covered by the grep half (`docs/` is outside `LIVE_ROUTES`) | same | the criterion *is* rule 5 | grep is per-name, so a listed token cannot match | grep excludes rule 7's paths | 8a is the guard half |
| 10 | n/a | n/a | n/a | n/a | n/a | the criterion *is* rule 6 | n/a | n/a |
| 11 | n/a | n/a | n/a | n/a | n/a | n/a | the criterion *is* rule 7 | n/a |
| 12 | names read from `skills/` glob (`tests/test_plugin_manifests.py:106`) | n/a — description enumerates skills only | n/a | n/a | `.codex-plugin/plugin.json` | n/a | n/a | n/a |
| 13 | keys compared to `skills/` glob (`evals/coverage.py:78`) | n/a | n/a | n/a | `evals/coverage.py:34,52` | n/a | n/a | n/a |
| 14 | arms name skills | n/a | n/a | n/a | `evals/evals.json` | n/a | n/a | n/a |
| 15 | `skills/<component>/SKILL.md` trigger | n/a — no agent documentation entry (`tcw-config.yaml:14-46`) | n/a | n/a | `Configuration-Key-Change` fires on `tcw-config.yaml:40` | n/a | `upcoming.md` is current, not history (rule 7) | n/a |
| 16 | all 15 in the mapping | all 3 in the mapping | n/a — not user-invoked | n/a — not user-invoked | release note is itself a reference | n/a | n/a | n/a |

## Risks

- **Breaking change with no deprecation path.** `/tcw:tcw-work` stops resolving the
  moment a user updates the plugin, and neither harness has a skill-alias mechanism to
  soften it. Mitigated only by the release note (criterion 16). The blast radius is
  small — the names are typed by humans and matched by this repo's own tests; nothing
  in `tcw-config.yaml` anywhere in this workspace binds one — but it is real, and it
  argues for landing the rename in one version rather than spreading it.
- **Capability and Feature ids are regenerated.** The command route is `add` + `rm`,
  so `skills/tcw-work`'s `cap-f533ba` does not survive as `skills/work`'s id. Nothing
  reads those ids today — `grep -rn cap-f533ba` finds only its own `meta.yaml` — so the
  loss is currently invisible, but it is a real discontinuity in ledger identity and
  the reason a `mv` verb would be better than this procedure (**Notes**).
- **A half-applied rename is silent before rule 8 lands.** Renaming a directory and
  leaving `SKILL.md`'s `name:` behind passes the whole suite today
  (`tests/test_plugin_manifests.py:131` checks presence, not agreement). Order the work
  so 8b and 8c exist before, or in the same commit as, the renames they cover —
  otherwise the largest mechanical edit in the item is the one running without a net.
  8a is the opposite case and must come *after* the renames, since it asserts the old
  names are gone.
- **`tcw taxonomy rm` reports success while leaving `check` failing.** It only warns on
  a dangling `relatesTo` (`docs/work/inbox/tcw-taxonomy-rm-deletes-nested-terms-without-a-word.md`).
  The ordering in Design 4 is what avoids it; run `tcw taxonomy check` after each
  removal rather than once at the end, so a mistake is attributable.
- **A prefix-stripping search-and-replace corrupts the tree.** `tcw-config` alone is
  486 occurrences and `tcw-sr-only` is a CSS class. Rule 6 exists for this; the risk is
  that the volume of edits (~100 files) invites exactly the shortcut that breaks it.
- **The eval harness is data, not code, and fails quietly.** A missed skill name in
  `evals/evals.json` shows up as an eval arm that never matches, which grading reports
  as a skill not invoked — indistinguishable from a real finding. Criterion 14's
  `--dry-run` is what catches it before a paid run does.
- **Downstream prose goes stale immediately.** Three repositories in this workspace
  name TCW skills in their `AGENTS.md`. Nothing breaks — none binds a skill — but a
  reader following `the tcw-work skill` will not find it. Out of scope by decision;
  worth a line in the release note so their owners know.

## Notes

- **Follow-up to file, not to fold in:** `tcw capabilities mv` / `tcw taxonomy mv`.
  This item is the second time a rename has had to be done as `add` + `rm` (the first
  being the skill restructure recorded in `Planning doc:
  2026-09-14-consolidate-the-setup-skills-into-a-single-tcw-setup-skill`, which is why
  fifteen of the sixteen skill capabilities carry that pointer, `skills/tcw-work-create`
  being the one added since). It passes the
  abstraction litmus test — re-keying an entry is something a tracker-backed store can
  do — so it belongs in the model, and it would have made rules 3 and 4 two commands
  instead of a procedure. It is not folded in here because it changes the CLI surface
  and needs its own spec, and because this rename does not block on it.
- **Re-measured at `implement`, and the counts moved.** This spec was written against
  fifteen shipped skills; `skills/tcw-work-create` landed afterwards, making sixteen
  shipped and fifteen to rename, so every count above reads one higher than it did and
  the renamed-name total is eighteen rather than seventeen. `tcw-work-create` also joins
  `tcw-work-stage` as a name beginning with `tcw-work`, which the whole-name
  substitution rule already covers. Rule 6's `tcw-config` and `tcw-cli` counts rose to
  443 and 100 with the v2.3.0 release notes, and criterion 8's suite baseline is 3367,
  not 3360 — both verified before any edit in this item.
- **Assumption, unverified:** that Claude and Codex both key a plugin skill on the
  directory name with the frontmatter `name` required to agree, rather than resolving
  on frontmatter alone. The repository is consistent with either reading — all sixteen
  skills currently agree — so the rename changes both, which is correct under both
  readings. Design 8's first assertion turns the assumption into a pinned invariant
  regardless of which is true.
- The 15 taxonomy Features are flat, top-level entries (`docs/taxonomy/tcw-*-skill/`
  with no children), checked against `find docs/taxonomy -maxdepth 2 -type d`. That is
  what makes `tcw taxonomy rm`'s silent nested-delete irrelevant here; it would not be
  if a Feature ever gained children.
