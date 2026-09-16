# Which skills a project may override, and why

Every `SKILL.md` in this folder carries `dynamic_skill: true` or
`dynamic_skill: false` in its frontmatter. This document is what that key
means, the two rules that decide its value, and the verdict for every skill,
reference document and agent TCW ships.

The key is for people. Neither Claude Code nor Codex acts on it.
`tests/test_dynamic_skill_marker.py` fails when a shipped document has no row
below, or when a skill's key disagrees with its row.

## What `dynamic_skill` means

- **`true`** — what the skill tells an agent is, or is intended to be, text the
  project using TCW can replace. TCW's own wording ships as the default, so a
  project that configures nothing gets exactly that wording.
- **`false`** — the text is TCW's, and a project changes it only with a pull
  request or a fork.

Some skills marked `true` still ship fixed prose: the mechanism that lets a
project replace a procedure's text, and the conversion of each skill to use it,
are separate pieces of work. Until a skill is converted, `true` records the
intent.

## The two rules

They are separate questions, asked in order. **Rule 2 is checked first**, because
it is cheaper and settles some documents without any argument about authority.

**Rule 2 — payload.** A document carrying no procedure of its own has nothing to
override, whatever Rule 1 would say about its subject. A skill whose body only
names a range of lifecycle stages and hands each one to `work-stage` is the
example: the procedure lives in the stage instructions, which a project can
already replace, and there is no text left in the skill to configure.

**Rule 1 — authority.** TCW owns the *shape* of what is produced: the three axes'
data model, the artifacts, the transitions, the configuration surface, and TCW's
own upstream processes. The project owns the *conduct* that produces it — which
tools, which advisors, which review, which QA, which git workflow.

Two consequences:

- **A mixed document keeps its rules fixed.** When a document a project may
  override also holds a rule protecting the board or an artifact — "search for
  an existing item before filing a new one" — converting it keeps that rule in
  TCW's fixed text and moves only the conduct. Otherwise an override becomes a
  way to switch the rule off.
- **Each document is judged on its own.** A reference document usually shares
  its skill's verdict, but does not inherit it; the table says where they differ.

## Why a project cannot add a procedure of its own

A project replaces the text of a procedure TCW defines. It cannot declare a new
procedure id.

- **Nothing would ever read it.** A procedure id is useful because a shipped
  skill asks for it by name, at a known moment. An id a project invented has no
  skill asking for it.
- **A project already has places for its own procedures**: a skill of its own,
  its agent guide (`CLAUDE.md`, `AGENTS.md`), or a `prompt` binding on a
  lifecycle stage.
- **A closed set of ids catches mistakes.** Because the ids are TCW's, `tcw
  validate` can refuse a misspelled one instead of silently ignoring a binding
  that will never be used.

## Verdicts

| Verdict | Means | `dynamic_skill` |
| --- | --- | --- |
| fixed (Rule 1) | Carries a procedure, but its subject is TCW's shape | `false` |
| fixed (Rule 2) | Carries no procedure of its own | `false` |
| fixed (accelerator) | An agent definition; see "Agents" below | not a skill |
| overridable | Carries conduct a project may replace | `true` |
| composes already | Its instructions already come from project configuration | `true` |

Documents are named by owner and by path within the owner.

| Owner | Document | Verdict | Reason |
| --- | --- | --- | --- |
| `taxonomy` | `SKILL.md` | fixed (Rule 1) | Describes the taxonomy axis; using TCW means adhering to its data model |
| `capabilities` | `SKILL.md` | fixed (Rule 1) | Describes the capabilities axis; using TCW means adhering to its data model |
| `work` | `SKILL.md` | fixed (Rule 1) | Describes the work axis — stages, artifacts, transitions; using TCW means adhering to them |
| `configure` | `SKILL.md` | fixed (Rule 1) | The configuration surface is how the `tcw` CLI works |
| `configure` | `references/*.md` | fixed (Rule 1) | Each describes configuration keys and what they do — the configuration surface |
| `extras-report` | `SKILL.md` | fixed (Rule 1) | How to report to TCW is TCW's own upstream process, for its maintainers to decide |
| `setup` | `SKILL.md` | fixed (Rule 1) | Installing and repairing the CLI is TCW's authority |
| `setup` | `references/install.md` | fixed (Rule 1) | Installing the CLI |
| `setup` | `references/project.md` | fixed (Rule 1) | `tcw init` and provisioning a project's stores |
| `setup` | `references/taxonomy.md` | fixed (Rule 1) | Seeds the taxonomy, whose entry kinds are the axis's data model. It also describes how to survey a codebase, which is conduct, but it runs once while a project is being set up, before the project has any configuration an override could come from |
| `setup` | `references/capabilities.md` | fixed (Rule 1) | Same as `references/taxonomy.md`, for the capabilities ledger and its statuses |
| `commands-process-inbox` | `SKILL.md` | fixed (Rule 2) | Runs the `inbox` and `request` stages through `work-stage`; the procedure is the stages' |
| `commands-plan-work` | `SKILL.md` | fixed (Rule 2) | Runs `request`, `spec` and `plan` through `work-stage`; the procedure is the stages' |
| `commands-drive-work-to-completion` | `SKILL.md` | fixed (Rule 2) | Runs every stage through `verify` via `work-stage`; the procedure is the stages' |
| `commands-verify-work` | `SKILL.md` | fixed (Rule 2) | Runs `verify` through `work-stage`; the procedure is the stage's |
| `work-stage` | `SKILL.md` | composes already | A template around injected commands; the stage instructions it delivers come from `tcw work stage prompt`, which a project extends or replaces under `work.lifecycle.stages.<id>.prompt`. The file holds no procedure to replace |
| `extras-autonomous-work` | `SKILL.md` | overridable | Which advisors to consult, how to review, how to close out and when to cut a version are conduct |
| `extras-triage-issues` | `SKILL.md` | overridable | How a project sweeps and answers its own issue tracker is conduct |
| `documentation-sync` | `SKILL.md` | overridable | Deciding which documents a change must update is the project's documentation practice |
| `documentation-sync` | `references/cut-version.md` | overridable | How a version is cut is the project's; the document's own first step already defers to a project's version-cut process |
| `documentation-sync` | `references/release-notes-and-changelogs.md` | overridable | The file layout it describes is the project's own documentation, opt-in by its own words, not a TCW artifact |
| `post-mortem` | `SKILL.md` | overridable | How to investigate a miss is conduct; the stage ladder it reasons over stays TCW's |
| `work-create` | `SKILL.md` | overridable | How an idea is filed is conduct; the rule that the board is searched first stays fixed (see `references/find-overlap.md`) |
| `work-create` | `references/find-overlap.md` | fixed (Rule 1) | Does not travel with its skill. It defines the search for existing work and its four relations — `covers`, `partly covers`, `blocks`, `related` — which decide the item fields the skill writes (`blocked_by`, an amendment, a reference). That is a board rule; a project replacing it could define "duplicate" out of existence |
| `work` | `references/procedures/*.md` | overridable | Auditing the backlog, consolidating plans, decomposing, delegating and searching the board are conduct |
| `work` | `references/lifecycle/stage-*.md` | fixed (Rule 1) | Each is a stage's contract — its inputs, its artifact, which steps are gated. The conduct half of a stage is its prompt, which composes already, and `work-stage` delivers the two together |
| `work` | `references/commands.md` | fixed (Rule 1) | The CLI's verbs and flags |
| `work` | `references/transitions.md` | fixed (Rule 1) | Transitions |
| `work` | `references/hooks.md` | fixed (Rule 1) | How lifecycle bindings resolve and run — the configuration surface |
| `work` | `references/tags.md` | fixed (Rule 1) | The tag registry's model |
| `work` | `references/epic-deltas.md` | fixed (Rule 1) | What each artifact means for an epic, and the relations between an epic and its children — data model |
| `work` | `references/cross-node-deltas.md` | fixed (Rule 1) | Relations between projects, `delegate` and `escalate` — data model |
| `agents` | `backlog-auditor.md` | fixed (accelerator) | Restates the per-item checks of the `audit-backlog.md` procedure |
| `agents` | `post-mortem.md` | fixed (accelerator) | Restates the `post-mortem` skill |
| `agents` | `verifier.md` | fixed (accelerator) | Carries assessment steps of its own beyond the `verify` stage; see "Agents" |

### Agents

An agent definition is Claude Code packaging — Codex never reads `agents/` — and
it runs only when a skill or stage chooses to dispatch it. Every document it
serves stands alone without it. So the project's choice lives at the dispatch,
not in the agent: a project wanting a different assessor or investigator names
its own agent in the text that dispatches one, and that text is either
overridable or composes already. An override written into an agent file would
reach Claude only.

Two consequences for whoever converts a document an agent restates:

- `backlog-auditor.md` restates `audit-backlog.md`, and `post-mortem.md`
  restates the `post-mortem` skill. Once either source can be replaced, the
  agent must stop carrying its own copy of the default, or a project's
  replacement is silently skipped whenever the agent is dispatched.
- `verifier.md` does not strictly pass Rule 2 — its steps go beyond the
  `verify` stage's — and is fixed on the reasoning above, not on Rule 2.

## Adding a skill, reference document or agent

1. Rule 2: does it carry a procedure of its own? If not, `fixed (Rule 2)`.
2. Rule 1: is its subject TCW's shape, or the project's conduct?
3. Add a row above with a reason specific enough to disagree with.
4. For a skill, add `dynamic_skill` to its frontmatter with the value its verdict
   gives, followed by the comment pointing here.
