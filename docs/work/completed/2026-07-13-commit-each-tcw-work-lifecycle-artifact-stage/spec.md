# Commit each TCW work lifecycle artifact stage

## Problem

The lifecycle guidance requires a commit at the transition from planning to
implementation, but it does not explicitly require commits after the individual
request, spec, plan, outcome, and refined-outcome stages. Agents therefore leave
durable work artifacts uncommitted until reminded or batch them into a later
commit, weakening the work item's resumability and stage history.

## Goals

- Make a narrow git commit an explicit completion condition for every lifecycle
  artifact stage.
- Require the commit immediately after the stage artifact and related TCW work
  metadata are written or materially updated, before starting the next stage.
- Cover task and epic lifecycles as well as the planning and completion prompt
  wrappers.
- Preserve the separate `tcw work start` transition commit before code changes.
- Tell agents to exclude unrelated working-tree changes from stage commits.

## Non-goals

- Add or change a `tcw` CLI command.
- Enforce commit ranges in the store or CLI.
- Prescribe exact commit-message text.
- Require empty or no-op commits when a stage artifact did not change.
- Change the user-verification gate before work-item completion.

## Current state

- `skills/tcw-work/SKILL.md` describes the artifact spine and only explicitly
  commits the `tcw work start` transition.
- `skills/tcw-work/references/lifecycle.md` repeats the implementation-boundary
  commit but has no per-stage commit rule.
- `skills/tcw-work/references/task-lifecycle.md` defines all five artifact stages.
- `skills/tcw-work/references/epic-lifecycle.md` defines the same artifacts with
  epic-specific meanings.
- `commands/tcw-plan-work.md` and
  `commands/tcw-drive-work-to-completion.md` can run multiple stages in one turn
  without explicitly checkpointing each stage.

## Proposed behavior

Completing a lifecycle stage means:

1. Write or materially update that stage's artifact.
2. Include TCW work files changed as part of the same stage, such as
   `state.yaml`, `capabilities.yaml`, attachments, or an epic reconcile rollup.
3. Validate the stage as appropriate and inspect the intended diff.
4. Commit only those stage changes before proceeding to the next stage.

The rule applies to `initial-request.md`, `spec.md`, `plan.md`, `outcome.md`, and
`refined-outcome.md`. A single invocation that produces several artifacts must
therefore produce several ordered commits. Existing artifacts do not require a
new commit merely because an agent reads them, and unchanged stages do not
require empty commits.

`tcw work start <slug>` remains its own implementation-boundary checkpoint. It
must be committed after planning and before any implementation edits; it should
not be folded into the plan-stage commit because the status transition is the
first implementation commit.

## Acceptance criteria

- The thin `tcw-work` router states the always-relevant per-stage commit rule.
- The common lifecycle dispatcher defines the checkpoint semantics once.
- Task lifecycle instructions explicitly checkpoint each artifact stage.
- Epic lifecycle instructions explicitly checkpoint its planning,
  coordination/outcome, and refinement artifacts.
- Both lifecycle prompt wrappers explicitly preserve separate, ordered commits
  when they execute multiple stages.
- Guidance says to stage only related TCW work files and avoid empty commits.
- Existing start/complete and user-verification behavior remains intact.

## Risks

- Overly repetitive instructions could bloat the progressive-disclosure router;
  keep the invariant concise in the router and put operational detail in the
  lifecycle references.
- Ambiguous wording could cause the `tcw work start` move to be folded into the
  plan commit; explicitly preserve it as a separate following commit.
- Broad `git add` guidance could capture unrelated user changes; require narrow
  staging and diff inspection.

## Capability changes

None. This is agent-process guidance and does not alter user-facing TCW
behavior, so no capabilities ledger entry is added or changed.
