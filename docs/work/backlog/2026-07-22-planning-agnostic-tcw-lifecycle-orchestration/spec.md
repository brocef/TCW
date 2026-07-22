# Specification

## Capability changes

- Add the `configurable-work-lifecycle` taxonomy Feature and the
  `lifecycle-checkpoint` vocabulary needed to describe the contract.
- Expand `plugin/work-lifecycle` so users can map ordered agent skills to TCW
  checkpoints without changing TCW's artifact or status model.
- Add a capability for auditing one skill or the complete configured workflow
  for TCW compatibility.
- Extend worktree closeout so an integration skill may merge locally or complete
  a merged pull request before TCW closes the item.

These are planned ledger changes only. Taxonomy and capability records are not
created or modified during this planning checkpoint.

## Problem

TCW currently provides one methodology-neutral agent lifecycle. Teams may
already use skills that define brainstorming, planning, execution, review,
verification, or branch-finishing methods. Replacing TCW's lifecycle with those
skills would lose its durable state and evidence contract, while embedding
specific third-party workflows in TCW would couple the product to a methodology.

TCW needs a compatibility layer that keeps ownership boundaries explicit:

- TCW owns durable work state, required evidence, destination artifacts,
  lifecycle transitions, capability reconciliation, and completion gates.
- Configured skills own how an agent performs the work within a checkpoint.

## Goals

- Define nine stable checkpoint contracts: `request`, `spec`, `plan`, `start`,
  `implement`, `review`, `verify`, `integrate`, and `complete`.
- Preserve the five existing lifecycle artifacts:
  `initial-request.md`, `spec.md`, `plan.md`, `outcome.md`, and
  `refined-outcome.md`.
- Let each node configure zero or more ordered, opaque skill references per
  checkpoint.
- Let users inspect the effective contract for a local or qualified work item.
- Validate configuration structure deterministically while leaving installed
  skill resolution to agent preflight.
- Give agents a fixed prompt envelope for invoking mapped skills without
  surrendering TCW-owned operations.
- Audit candidate skills and complete configured workflows for compatibility.
- Support completion after an integration skill has already merged the work.

## Non-goals

- New work statuses, artifact types, approval documents, or per-stage progress
  state.
- Custom prompt bodies or built-in methodology presets.
- Resolving harness-installed skills inside the Python CLI.
- Inheriting lifecycle configuration across connected projects.
- Making TDD, subagents, parallel execution, or worktrees TCW requirements.
- Automatically selecting a release version, publishing, or pushing.

## Current state

- `WorkStore` and `FsWorkStore` are the abstract model and shipped filesystem
  adapter boundary; new policy behavior must pass the storage-abstraction
  litmus test.
- `tcw-config.yaml` already contains node configuration, and validators already
  exercise preservation and graph behavior around that file.
- `plugin/work-lifecycle` documents planning and execution through the fixed
  artifact spine, including optional bounded plan-stage documents.
- `tcw work complete` currently auto-merges branches created by
  `tcw work start --worktree`, then evaluates capability gates and cleans up.
- `commands/tcw-plan-work.md`, `commands/tcw-drive-work-to-completion.md`, and
  `skills/tcw-work/references/` are the existing orchestration surfaces.
- Claude and Codex plugin manifests package the relevant commands and skills.

## Lifecycle policy model

Add a storage-neutral `LifecyclePolicy` model and a
`WorkStore.lifecycle_policy()` operation. The fixed checkpoint IDs and their
contracts belong to the model. The filesystem adapter reads node-local policy
from this shape:

```yaml
work:
  lifecycle:
    skills:
      spec:
        - superpowers:brainstorming
      plan:
        - superpowers:writing-plans
      implement:
        - superpowers:subagent-driven-development
      review:
        - superpowers:requesting-code-review
      verify:
        - superpowers:verification-before-completion
      integrate:
        - superpowers:finishing-a-development-branch
```

Each value is a list of non-blank strings. Declaration order is significant.
Omitted checkpoints have empty skill lists and therefore use TCW's generic
guidance. Configuration is local to the resolved item's node; a qualified
descendant work reference uses the descendant node's policy.

`tcw validate` rejects:

- checkpoint keys outside the fixed set;
- a non-mapping `work.lifecycle` or `skills` value;
- checkpoint values that are not lists;
- non-string or blank references;
- duplicate references within one checkpoint.

Validation must not reorder configured references or alter unrelated
`tcw-config.yaml` keys.

## Lifecycle inspection

Add read-only `tcw work lifecycle [work-ref] [--json]`. Without a work reference,
it reports the local node policy. With a local or qualified reference, it
resolves the item's owning node and reports:

- all fixed checkpoint IDs in lifecycle order;
- the objective for each checkpoint;
- allowed input artifacts;
- required output or evidence;
- TCW-owned destination paths;
- configured skills in declaration order.

Human output should be scannable and JSON output should be stable enough for
agent tooling and tests. The command never executes a skill or changes state.

## Agent orchestration contract

Update the `tcw-work` skill and lifecycle references so every mapped skill is
invoked with a fixed envelope containing:

- the current work-item reference;
- the checkpoint objective;
- allowed input artifacts;
- required output or evidence;
- TCW-owned destination paths;
- an ownership rule stating that only TCW performs checkpoint commits, `start`,
  capability reconciliation, and `complete`.

Before invoking a configured reference, the agent checks that the skill is
available. A missing configured skill fails closed and is reported to the user.
Unmapped checkpoints continue through TCW's methodology-neutral guidance.

Evidence placement remains bounded:

- `request`, `spec`, and `plan` produce their named artifacts.
- `start` establishes readiness and performs the TCW transition.
- `implement` produces `outcome.md`.
- `review` and `verify` append evidence to `outcome.md` or
  `refined-outcome.md`.
- `integrate` records the chosen merge, pull-request, or keep-branch outcome in
  `refined-outcome.md`.
- `complete` performs documentation, capability, resolution, and version gates.

## Already-integrated worktree completion

Add `tcw work complete --already-integrated` for work items originally started
with a TCW-created worktree. It must:

- require the normal explicit confirmation and resolution;
- skip TCW's automatic work-branch merge;
- evaluate completion, capability, and definition-of-done gates against the
  primary checkout;
- tolerate a worktree or branch that an integration method already removed;
- attempt safe cleanup of any remaining TCW-created worktree state.

Default completion retains the existing auto-merge behavior. Creating a pull
request or keeping a branch does not make an item complete: it stays active. If
the pull request later merges, the agent resumes closeout with
`--already-integrated`.

## Lifecycle compatibility audit

Add a thin `tcw-lifecycle-audit` skill and a Claude command:

`/tcw-audit-lifecycle-skill [skill-ref]`

With an argument, it audits one candidate skill. Without an argument, it audits
the configured workflow and checkpoint handoffs. This remains an AI workflow,
not a `tcw` executable subcommand.

Report one of `compatible`, `conditional`, or `incompatible`, with evidence for:

- artifact-path overrideability;
- checkpoint fit;
- required subskills and availability;
- hard-coded handoffs;
- approval gates;
- transition ownership and completion claims;
- branch integration and cleanup behavior;
- destructive actions.

The full-workflow audit also detects gaps or incompatible assumptions between
adjacent configured checkpoints. Superpowers may be documented and fixture-
tested as an example, but must not become a maintained preset.

## Acceptance criteria

- Valid policy configuration round-trips in declared order and unrelated config
  remains unchanged.
- Invalid policy shapes, checkpoint names, references, and duplicates fail
  validation with actionable messages.
- Human and JSON lifecycle output expose the same fixed contracts and effective
  mappings.
- A qualified descendant item uses its own node's lifecycle policy.
- Agent guidance handles mapped, unmapped, and unavailable skills according to
  the ownership and fail-closed rules.
- The compatibility audit classifies representative individual skills and
  workflow gaps, including Superpowers-style fixed paths and handoffs.
- Existing worktree completion continues to auto-merge by default.
- `--already-integrated` skips merging, preserves all normal gates, tolerates
  prior cleanup, and safely cleans up what remains.
- README, commands, skills, manifests, taxonomy, capabilities, release notes,
  and changelog accurately describe the shipped behavior.

## Risks and dependencies

- A skill can claim configurability while retaining hidden fixed paths or
  handoffs; the audit must report evidence and conditions rather than assuming
  compatibility.
- Prompt ownership could blur if a mapped skill attempts commits or lifecycle
  transitions; the envelope and audit must explicitly guard those boundaries.
- Already-integrated completion must not mistake an unmerged branch for
  integrated work. Its documented precondition and primary-checkout gates are
  essential.
- Plugin packaging tests must cover both new skill and command surfaces so a
  local implementation is not omitted from distribution.

## External references

- [Superpowers workflow](https://github.com/obra/superpowers)
- [Superpowers brainstorming contract](https://github.com/obra/superpowers/blob/main/skills/brainstorming/SKILL.md)
- [Superpowers branch-finishing choices](https://github.com/obra/superpowers/blob/main/skills/finishing-a-development-branch/SKILL.md)
