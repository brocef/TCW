# Spec: Generate a role-specific AGENTS.md from configured role definitions

## Capability changes

Planned ledger deltas. No records are written at this stage.

**New taxonomy — Vocabulary:**

| Term | Meaning |
| --- | --- |
| `agent-guide` | The instruction file an AI coding agent reads on entering a project (`AGENTS.md`, `CLAUDE.md`, and their per-harness equivalents). |
| `agent-guide/role` | A named audience whose guide differs — the identity a person claims when generating theirs. |
| `agent-guide/fragment` | A named, reusable chunk of guide text, declared once and placed by any number of role templates. |
| `agent-guide/template` | The Markdown skeleton for one role: prose plus `{{fragment}}` placeholders. |
| `agent-guide/target` | One destination a rendered guide is written to. |

**New taxonomy — Feature:** `configurable-agent-guide` — "Composing a project's
agent instruction file from named fragments per role, so one repository serves
several audiences without any of them editing a shared file." `vocabulary:`
the five terms above; `relatesTo:` `configurable-work-lifecycle`, which it
deliberately mirrors.

**New capability group `docs/capabilities/agents/`**, Status `Supported` on
completion:

| Capability | As a user, I can… |
| --- | --- |
| `declare-agent-guide-roles` | …declare in `tcw-config.yaml` which roles my project has, which template each renders, and which YAML files supply the fragments. |
| `generate-my-agent-guide` | …run one command during repo setup, say which role I am, and get `AGENTS.md` and `CLAUDE.md` written for that role. |
| `share-guide-text-between-roles` | …write a chunk of guide text once and place it in every role's template by name, so shared content is never duplicated. |
| `derive-guide-text-from-a-script` | …have a fragment produced by a script of mine, so guide content derived from the project (its task-runner scripts, say) cannot go stale. |
| `remember-which-role-i-am` | …have my answer remembered per checkout so I never retype it, and change it with one command. |
| `override-guide-fragments-locally` | …override a fragment in an untracked file of my own, adding standing instructions without editing shared config. |
| `choose-where-the-guide-is-written` | …name the files the guide is written to, and get the known Cursor, Copilot and Gemini paths without spelling them out. |

**Amended:** `docs/capabilities/cli/validate-a-node` — `tcw validate` gains the
agent-guide configuration in its pass. Wording change only; the capability's
identity is unchanged.

## Problem

An agent guide is a single file at a fixed path, and a repository has one of
them. Everyone who clones the repository gets the same instructions.

That is wrong whenever a repository is worked by people in different roles. The
requester's case is three: an engineer who does full-stack work, a UI/UX
engineer who must not touch the backend and must stub API calls in prototypes,
and a product designer who needs all of that plus "communicate without technical
jargon." One file cannot say all three things. Worse, it cannot say two
*contradictory* things — "build the backend" and "never build the backend" — so
the shared file degrades into the intersection, which is the instructions nobody
actually needed.

TCW already solved the structurally identical problem one layer down. A
lifecycle stage's instructions are not a fixed string: `work.lifecycle` in
`tcw-config.yaml` binds text to each stage, and `resolve_prompts`
(`tcw/work/resolve.py:383`) composes TCW's own built-in with the project's, from
inline text (`blob:`), a file (`file:`), or a script (`generate:`) —
`PROMPT_KINDS` at `tcw/store/base.py:629`. The project supplies methodology; TCW
supplies the contract. The agent guide has no equivalent, so every project's
guide is hand-maintained prose at one path.

Two consequences beyond the requester's case, both visible in this repository:

- **Shared content gets duplicated or lost.** Any two audiences share most of a
  guide — how to run the tests, what the project is. With one file there is
  nothing to share *with*; with N hand-written files there is nothing stopping
  them drifting.
- **The guide is a known-fragile integration point.** Tooling locates sections
  in it *by heading name*. `skills/documentation-sync/SKILL.md:13` falls back to
  a `## Documentation Sync` section, and
  `skills/documentation-sync/references/cut-version.md:14` looks for a
  `## Versioning` section. `docs/migration-guide-0.21.X-to-1.0.0.md` records this
  as lesson #1 of TCW's own migration: "Find out what reads your agent guide
  before you empty it." Anything that changes how the guide is produced has to
  keep those headings produced.

## Goals

1. A project declares its roles, its guide fragments, and its output targets as
   **node configuration** in `tcw-config.yaml`, checked by `tcw validate` — the
   same class of thing `work.lifecycle` and `work.documentation` already are.
2. Guide text is composed from **named fragments placed by a per-role
   template**, so content shared between roles is declared once.
3. A fragment's text may be written inline, read from a file, or produced by a
   script — the three sources a lifecycle prompt binding already has.
4. One command renders the guide for a role and writes it to every configured
   target.
5. The role a person claims is **remembered per checkout** and is not shared
   state.
6. The command works with no terminal attached, so an agent under either harness
   can run it (`docs/lifecycle/harness.md`).
7. TCW's own agent guide is produced this way.

## Non-goals

- **Detecting that a generated guide is stale** against changed config or
  fragments. Deliberately deferred; the generated file carries a provenance
  header saying how to regenerate it, and that is all.
- **Per-target content.** One render is written to every target. A target whose
  harness needs different text — Cursor `.mdc` frontmatter, say — is not served.
- **Format translation** for third-party harnesses. Target presets are path
  aliases and nothing more.
- **Role-aware behavior anywhere else in TCW.** No `when: {role: …}` on
  lifecycle bindings, no role-filtered board. The persisted role must be shaped
  so this is possible later; nothing may consume it now.
- **Editing roles, fragments or templates through `tcw serve`.**
- **Recursive fragment expansion.** A fragment's own text is not rescanned.
- **Moving TCW's `## Versioning` prose into configuration.** That is the
  standing backlog item
  [2026-08-18-serve-version-cut-instructions-from-tcw-config-yaml-instead-of-the-agent-guide](tcw://W/2026-08-18-serve-version-cut-instructions-from-tcw-config-yaml-instead-of-the-agent-guide);
  this item must not pre-empt it, only avoid breaking it.

## Design

### Where this sits, and why it is not a store

A new top-level command group `tcw agents`, registered like the other three:
`tcw/cli.py:34` lists the built component modules and `build_parser`
(`tcw/cli.py:218`) calls each one's `add_subparser`. The group follows
`tcw/work/cli.py:33-37`'s module contract — `NAME`, `SUBCOMMANDS`,
`DEFAULT_SUBCOMMAND`, `add_subparser`.

**It adds no store, and the prime directive is why.** The litmus test asks
whether a non-filesystem store could implement an operation. Here there is no
store operation to implement: role definitions are node *configuration*, exactly
as `work.lifecycle` and `work.documentation` are — parsed from `tcw-config.yaml`,
never read through a `WorkStore`. The rendered guide is a working-tree file, in
the same category as the git worktree `tcw work start --worktree` creates: an
artifact the filesystem adapter produces, not a modeled object. A tracker-backed
node reads its roles from the same config and writes the same file. Nothing
here belongs in the abstract store interface, and nothing here may be reached
through one.

The persisted role is checkout-local state for the same reason: it identifies
*this person on this machine*, which a shared store has no notion of. It must
not be written into the work store, and no store method may return it.

**Naming.** `tcw agents` does not collide with the repository's `agents/`
directory (Claude subagent definitions) — different namespace, and the group is
named for what it produces.

### Configuration

A new top-level `agents:` key, sibling to `id:` and `work:`:

```yaml
agents:
    fragments:
        - docs/agents/common.yaml
        - docs/agents/engineering.yaml
    overlay: .tcw/agents-overlay.yaml
    default-role: engineer
    targets: [agents, claude]
    roles:
        engineer:
            template: docs/agents/engineer.md
        ui-ux:
            template: docs/agents/ui-ux.md
        product:
            template: docs/agents/product.md
```

- **`roles`** — a mapping of role name to `{template: <node-relative path>}`.
  Required, non-empty. Role names are matched exactly; `tcw agents roles` lists
  them.
- **`fragments`** — an ordered list of node-relative YAML files. Optional only
  in the sense that a project may place all its text inline in templates; a
  template referencing any fragment needs at least one.
- **`overlay`** — one node-relative YAML path allowed to override declared
  fragments. Optional; defaults to `.tcw/agents-overlay.yaml`. Its absence is
  never an error.
- **`default-role`** — the role used when no terminal is attached and nothing
  else resolved. Optional, must name a declared role.
- **`targets`** — see below. Optional; defaults to `[agents, claude]`.

Every path is resolved through the same confinement `_confined`
(`tcw/work/resolve.py:107`) applies to a `file:` binding — resolved with
symlinks followed, refused if it lands outside the node root.

### Fragment files

A fragment file is a YAML mapping of fragment name to fragment value:

```yaml
preamble: Preamble text here
project-commands:
    file: docs/agents/fragments/commands.md
release-process:
    generate: python scripts/render_release_fragment.py
```

Three value forms, and **a bare string means `blob`**. That is a deliberate
divergence from `_parse_binding` (`tcw/store/base.py:1018-1076`), which rejects a
bare string in a lifecycle binding list rather than guessing at its kind. The
reason it guesses there is that a bare string in a *list* could be a command, a
file, or a skill — three readings, no way to choose. In a fragment mapping the
key already names the thing and the position admits exactly one reading: the
fragment's text. A fragment map is mostly prose, and requiring `blob:` on every
entry would make the common case worse to serve a disambiguation that does not
apply. Explicit `{blob: …}`, `{file: …}` and `{generate: …}` are all accepted;
any other key is an error naming the offender.

`file:` and `generate:` reuse the existing machinery rather than reimplementing
it — `_read_file` and `run_generate` via `_resolve_one`
(`tcw/work/resolve.py:124`, `tcw/work/generate.py:96`, `tcw/work/resolve.py:183`),
with `LifecyclePolicy`'s timeout and output cap (`tcw/store/base.py:808-809`). A
`generate:` fragment receives no work item — there is none — so the JSON on its
stdin carries `"item": null`, which `hook_payload` already produces
(`tcw/work/resolve.py:146-172`). It gets `TCW_NODE_ROOT` and `TCW_HOOK_*`, plus
`TCW_AGENTS_ROLE` naming the role being rendered.

**Duplicate fragment keys across declared files are an error**, naming both
files and the key. The overlay is the single exception: a key it defines
replaces the declared one, and the generated file's provenance header names
every fragment the overlay supplied, so an override is never invisible in the
output it changed.

### Templates and substitution

A template is a Markdown file. `{{fragment-name}}` is replaced by that
fragment's resolved text. Double braces match the existing
`{{tcw:documentation}}` / `{{tcw:body}}` convention (`tcw/work/resolve.py:215`,
`:291`) and survive code fences, JSON and shell brace expansion in fragment
content without an escape rule.

- **Single pass.** Substituted text is not rescanned. Recursion would need cycle
  detection and would silently expand a `{{…}}` that a fragment mentions as
  prose — which the fragments documenting *this feature* will.
- **An unknown fragment name is a hard error**, naming the token, the template,
  and the declared fragment names. A guide shipped with a literal `{{foo}}` in
  it is a broken instruction to an agent, not a cosmetic defect.
- **Continuation lines are indented to the token's column**, exactly as
  `substitute_documentation` (`tcw/work/resolve.py:237`) already does, so a
  multi-line fragment placed inside a list item renders as part of that item.
- **A declared fragment no template references** is reported by `tcw validate`,
  not by `generate`. It is almost always a typo, and validate is the pass that
  exists to find those.

### Role resolution

In order, first hit wins:

1. `--role <name>`
2. `TCW_AGENTS_ROLE`
3. the persisted role, `.tcw/role`
4. an interactive prompt — **only when stdin is a terminal**
5. `agents.default-role`
6. failure: exit non-zero, naming every declared role and `--role`

Steps 1 and 4 persist the answer to `.tcw/role` unless `--no-save` is given;
`tcw agents role <name>` sets it directly and `tcw agents role` prints it.

**Step 4 is the first interactive prompt in the CLI** — nothing in `tcw` calls
`input()` today. The guard is the terminal check, and it matters more than it
looks: `tcw/stdin.py:3-8` documents that a non-terminal stdin is not the same as
a pipe carrying data, and a blocking read on an inherited descriptor is how an
automated caller gets stranded rather than failed. So the prompt is reached only
on a real terminal, and a CI runner, a hook, or an agent session falls through to
`default-role` or to the error. This is what makes the command satisfy
`docs/lifecycle/harness.md`: a Codex agent and a Claude agent both reach the same
outcome, and neither hangs.

`tcw agents generate` reads no piped intake and must not be added to the set of
commands that do (`tcw/stdin.py:22-25` — that module owns file descriptor 0).

### Targets

`targets` is a list whose entries are either a **preset name** or a mapping
`{path: <node-relative>, mode: file|link}`. Presets are path aliases only:

| Preset | Path | Mode |
| --- | --- | --- |
| `agents` | `AGENTS.md` | `file` |
| `claude` | `CLAUDE.md` | `link` |
| `gemini` | `GEMINI.md` | `link` |
| `copilot` | `.github/copilot-instructions.md` | `file` |
| `cursor` | `.cursor/rules/project.mdc` | `file` |

The first `file` target is the **primary**; a `link` target is a relative
symlink to it. A configuration whose first entry is a `link` is rejected —
there would be nothing to link to.

**A symlink that cannot be created falls back to a copy**, and the command says
which it did. Symlinks need developer mode on Windows and are unsupported on
some filesystems; failing the whole generate over `CLAUDE.md` would be worse
than writing two identical files. Parent directories are created as needed.

Every target is gitignored via `ensure_ignored` (`tcw/store/fs.py:592`), which
appends only the lines the file lacks and leaves a rule the user deleted on
purpose deleted. `.tcw/` is gitignored the same way.

### The generated file

Each target opens with a provenance header:

```markdown
<!-- Generated by `tcw agents generate` for role: engineer. Do not edit —
     edit docs/agents/*.yaml and regenerate. Overlay fragments applied: none. -->
```

No timestamp and no content hash: the file is gitignored, so churn buys nothing,
and a byte-identical re-render is what makes `--dry-run` comparable to what is
on disk.

### Commands

| Command | Does |
| --- | --- |
| `tcw agents generate [--role R] [--no-save] [--dry-run]` | Render and write every target. `--dry-run` writes nothing and reports what would change. |
| `tcw agents show [--role R]` | Print the rendered guide to stdout. Writes nothing, persists nothing. |
| `tcw agents roles` | List declared roles, marking the persisted one and the default. |
| `tcw agents role [<name>]` | Print or set the persisted role. |

### Validation

`tcw validate` gains a node-configuration pass for `agents:`, run when the whole
node is validated and not when a single path or target is
(`tcw/validate.py:_components_to_check` selects by store tree, and `agents` has
no tree). It mirrors how `lifecycle_problems` and `documentation_problems` run
only for node-wide checks (`tcw/store/fs.py:4080-4086`), and reports, naming the
offender each time: a malformed shape; a role whose `template` is missing or
resolves outside the node; a fragment file that is missing, unreadable, or not a
mapping; an unknown value key; a duplicate fragment key across declared files; a
`default-role` naming no declared role; an unknown target preset; a `targets`
list whose first entry is a `link`; a template token naming no fragment; and a
declared fragment no template uses.

Parsing follows the established contract: a pure parser returning
`(value, problems)` that never raises and never touches the filesystem, with
path existence checked separately by the caller — the split
`parse_lifecycle_policy` and `lifecycle_problems` already use
(`tcw/store/fs.py:3990-4001`).

### This repository's own migration

TCW declares two roles, both rendering from shared fragments:

- **`contributor`** (the `default-role`) — everything the current `AGENTS.md`
  says except the release procedure.
- **`maintainer`** — the same, plus the version-cut procedure.

`AGENTS.md` and its `CLAUDE.md` symlink stop being tracked and become generated
output. The sections move into fragment files under `docs/agents/`.

**The heading contract survives the move.** Two skills locate sections in the
guide by name — `## Documentation Sync`
(`skills/documentation-sync/SKILL.md:13`) and `## Versioning`
(`skills/documentation-sync/references/cut-version.md:14`) — so **both headings
must appear in every role's rendered guide**, including `contributor`. This is
the migration guide's lesson #1 applied to itself, and it is an acceptance
criterion rather than a note.

**A fresh clone has no guide until the command runs.** So
`scripts/remote_session_setup.sh` — already wired to `SessionStart` in
`.claude/settings.json`, idempotent, silent on success — runs
`tcw agents generate`, and the manual path documented for Codex and local shells
gains the same step.

**Two tests read `REPO / "AGENTS.md"` directly and must be retargeted** to the
tracked fragment sources, which are the reviewable artifact once the guide is
generated: `tests/test_repo_lifecycle.py:110` (asserts the documentation-entry
triggers are not listed in the guide) and
`tests/test_documentation_sync_wiring.py:30` (scans for dangling references to
an absorbed plugin).

**A gitignored guide leaves one test's scope.**
`tests/test_documented_cli_surface.py` covers "every Markdown file git knows
about — tracked or merely untracked and not ignored", so a gitignored `AGENTS.md`
is no longer scanned for `tcw` verbs that do not exist. The tracked fragments and
templates under `docs/agents/` are scanned in its place, and because that test
derives its scope by exclusion, they are covered the moment the files exist with
no edit to the test.

### Integration-point sweep

The migration guide requires grepping for what reads the guide before emptying
it. Repo-wide, `AGENTS.md` and `CLAUDE.md` are read from four live sites, all
named above: two skill documents (by heading), and two tests (by path).
`scripts/cut_version.py:11` mentions CLAUDE.md in a comment only and reads
nothing. Matches under `docs/plan/`, `docs/work/`, `docs/changelogs/` and
`docs/migration-guide-*.md` are archival prose that describes past states and is
excluded from `test_documented_cli_surface.py` for the same reason.

## Acceptance criteria

1. `tcw agents` appears in `tcw --help`; `tcw agents generate|show|roles|role`
   each parse and run.
2. A node whose config declares two roles sharing a `{{preamble}}` fragment
   renders both guides with byte-identical preamble text, from one declaration.
3. `tcw agents generate --role <r>` writes every configured target; with default
   `targets`, `AGENTS.md` is a regular file and `CLAUDE.md` is a symlink to it.
4. On a filesystem where symlink creation fails, `CLAUDE.md` is written as a
   copy with content identical to `AGENTS.md`, the command exits 0, and its
   output says a copy was written.
5. A fragment declared as a bare string, as `{blob: …}`, as `{file: …}`, and as
   `{generate: …}` all render; the `generate:` script receives JSON on stdin
   whose `item` is `null` and has `TCW_AGENTS_ROLE` set to the role being
   rendered.
6. A `generate:` fragment exceeding the configured timeout or output cap fails
   the command, and **no target file is written or modified** — matching
   `run_generate`'s "nothing was used" contract (`tcw/work/generate.py:176-189`).
7. A template naming an undeclared fragment fails `tcw agents generate` with a
   non-zero exit, naming the token and the template; no target is written.
8. A fragment whose text contains `{{other-fragment}}` renders that text
   literally — one substitution pass, no recursion.
9. A multi-line fragment placed on an indented line renders with every
   continuation line at the token's column.
10. The same fragment key in two declared fragment files is reported by
    `tcw validate` and fails `tcw agents generate`, naming the key and both
    files.
11. The same key in the overlay file overrides the declared one, the command
    succeeds, and the provenance header names that fragment as overlay-supplied.
12. With no `--role`, no `TCW_AGENTS_ROLE`, no `.tcw/role`, no terminal on
    stdin, and a `default-role` declared, the command renders the default role
    and exits 0. With no `default-role` it exits non-zero, naming every declared
    role, and writes nothing.
13. `tcw agents generate --role <r>` followed by `tcw agents role` prints `<r>`;
    a subsequent `tcw agents generate` with no arguments renders `<r>` without
    reading stdin. `--no-save` leaves `.tcw/role` unchanged.
14. After a generate, `.gitignore` contains rules covering every target and
    `.tcw/`, and `git status --porcelain` reports no untracked guide files.
15. `tcw agents generate --dry-run` writes nothing, and running it twice against
    an up-to-date tree reports no changes both times.
16. `tcw validate` on a node with each of the malformed configurations listed
    under **Validation** reports that problem, naming the offender; on a
    well-formed one it reports none.
17. A path in `agents.fragments`, a role `template`, or a fragment `file:` that
    resolves outside the node root — including through a symlink inside it — is
    refused, matching `_confined`'s existing behavior.
18. This repository's `tcw-config.yaml` declares `contributor` and `maintainer`;
    `tcw agents show --role contributor` and `--role maintainer` each contain
    `## Documentation Sync` and `## Versioning`.
19. `AGENTS.md` and `CLAUDE.md` are absent from `git ls-files`, and matched by
    `.gitignore`.
20. `scripts/remote_session_setup.sh --force` leaves a generated `AGENTS.md` on
    disk, and running it twice produces byte-identical output.
21. The full suite passes, including `tests/test_repo_lifecycle.py` and
    `tests/test_documentation_sync_wiring.py` retargeted to `docs/agents/`.

## Risks

1. **The heading contract breaks silently.** `documentation-sync` finds
   `## Documentation Sync` and `## Versioning` by name; a role template that
   omits either disables the gate with no error anywhere. Criterion 18 pins it
   for this repo, but the mechanism lets any adopting project make the same
   mistake and TCW cannot detect it — TCW does not know which headings a
   project's tooling greps for. Mitigation is documentation: the README section
   must carry lesson #1 from the migration guide, and this repo's own templates
   stand as the worked example.
2. **A setup command that runs the repository's scripts.** `generate:` fragments
   execute shell, under the trust model at `tcw/work/hooks.py:11-14` —
   `tcw-config.yaml` is the user's own file and runs as they do. That model is
   unchanged, but the *moment* it applies is new and worse: existing `generate:`
   hooks fire during a lifecycle stage, whereas this fires from a setup command
   a new contributor runs on a freshly cloned repository, before reading any of
   it. The README must say so where it introduces `generate:` fragments, in the
   same breath as introducing them.
3. **A fresh clone or a CI job has no guide.** Anything reading `AGENTS.md`
   before `tcw agents generate` runs finds nothing. `default-role` plus the
   session-setup script covers the paths this repo has; an adopting project that
   wires neither gets a silently guide-less agent. The failure mode is quiet,
   which is the worst kind — worth a README warning beside `default-role`.
4. **Third-party harness paths drift.** `.cursor/rules/project.mdc`,
   `.github/copilot-instructions.md` and `GEMINI.md` are other vendors'
   conventions on other vendors' release schedules, and baking them into a
   preset table dates the release that ships it. Contained by keeping presets
   *path aliases only* — no format translation, no frontmatter — so a wrong
   preset costs a config line to work around, and by the mapping form accepting
   any path.
5. **One render for every target.** A harness needing frontmatter or a different
   format is not served, and `cursor` is the preset most likely to hit this.
   Named as a non-goal rather than half-solved.
6. **The generated guide leaves the CLI-surface test's scope.** Handled by
   retargeting to `docs/agents/`, but the guarantee is now indirect: text is
   checked where it is authored rather than where it is read, so a defect
   introduced by *composition* — a token expanding into a stale command name —
   would not be caught. The single-pass, no-recursion rule keeps composition
   simple enough that this is a small gap, not an open one.
7. **Two audiences, two moving parts, one file.** Splitting this repo's guide
   into two roles doubles what a change to shared prose has to be checked
   against. Two roles is the smallest number that dogfoods the feature honestly;
   more would be invented.

## Notes

- **No reference material was offered** — the request records "asked; none
  provided" and names the codebase as the reference. Everything cited above was
  read in this pass.
- **Sibling sweep.** This is a feature, not a defect report, so the repo-wide
  sweep the stage requires was run as the migration guide's own integration-point
  grep: every live reader of `AGENTS.md`/`CLAUDE.md` in the repository. Four
  sites found, all named under **Integration-point sweep**, all addressed.
- **Assumption, unverified.** The Cursor, Copilot and Gemini instruction paths in
  the preset table are from general knowledge, not checked against those
  vendors' current documentation in this pass. Risk 4 is why that is tolerable —
  they are aliases, not contracts — but the implementation should confirm each
  before shipping the table, and drop any it cannot confirm.
- **Interaction with a standing backlog item.**
  [2026-08-18-serve-version-cut-instructions-from-tcw-config-yaml-instead-of-the-agent-guide](tcw://W/2026-08-18-serve-version-cut-instructions-from-tcw-config-yaml-instead-of-the-agent-guide)
  proposes moving the `## Versioning` prose out of the guide into configuration.
  It is not a blocker in either direction, and the two are complementary: if it
  lands first, criterion 18's `## Versioning` requirement is relaxed by that
  item, not by this one. Neither should be planned as though the other has
  landed.
- **Deliberately not reused.** `Condition` (`tcw/store/base.py:635`) matches on a
  `WorkItem`'s tags and type. There is no work item here, and `matches` returns
  `False` for `None` by design, so `when:` is not offered on a fragment. Role
  selection *is* the condition, and adding a second conditioning mechanism beside
  it would give two answers to "which text applies".
