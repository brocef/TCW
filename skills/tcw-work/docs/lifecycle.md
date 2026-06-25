# TCW work lifecycle

Use this lifecycle when planning a new request, planning an existing work item, driving a work item to verification, or resuming work whose next stage is unclear. TCW's durable unit is the work item folder; write lifecycle artifacts beside `content.md` so the item can move through `backlog`, `active`, and `completed` without losing context.

For small changes, offer to compress stages that would add ceremony without reducing risk. Compression means shorter artifacts and fewer research passes, not an untracked change. Preserve enough written context for another agent to resume safely.

## 1. Request ingestion -> `initial-request.md`

Input can be either:

- a chat request that has not yet been captured as a TCW item;
- an existing TCW work item folder whose request is still a sketch;
- a transient `docs/work/inbox/` request created by TCW's `delegate` or `escalate` commands, or dropped there directly by a user.

If the user provides the request only in chat, create a backlog item with `tcw work new "<title>"` and use its folder as the artifact home. If processing `docs/work/inbox/`, convert it into a backlog item, write the durable `initial-request.md`, then remove the source inbox doc during this stage. The inbox doc is only raw intake; it is not load-bearing after ingestion.

Discuss the request enough to remove ambiguity and capture the broad strokes. Only basic research should be needed here. Write `initial-request.md` in the work item folder with:

- the user's requested outcome;
- known constraints and non-goals;
- open questions that remain acceptable for spec planning;
- any user decisions already made.

## 2. Request processing -> `spec.md`

Input: `initial-request.md`.

Do the deeper discovery pass. Determine feasibility, scope, urgency, interactions with related work items, and how the current project works. For product work, run the tcw-capabilities planning gate before settling the technical shape. When useful, sketch UI flows, API shapes, data contracts, or migration paths.

Write `spec.md` with:

- `## Capability changes` as the first content section when there is a product delta;
- problem, goals, non-goals, constraints, and affected surfaces;
- current-state findings with file references where relevant;
- proposed behavior and acceptance criteria;
- risks, dependencies, and related work items.

## 3. Spec processing -> `plan.md`

Input: `spec.md`.

Translate the spec into an implementation plan. Deep-dive the repository, dependencies, or sub-projects enough that the plan can be executed without rediscovering the main design. Break the work into phases and call out which phases can run in parallel.

Write `plan.md` with:

- ordered phases and concrete tasks;
- parallelization opportunities and dependencies;
- expected file/module touch points;
- verification commands;
- explicit documentation-sync tasks for triggers that are expected to fire.

When planning is complete and implementation is about to begin, run `tcw work start <slug>` before the first code edit. Commit that status change before implementation changes. Use `--worktree` when isolation is useful; in that flow the primary checkout carries status transitions and the work branch carries implementation edits.

## 4. Implementation -> `outcome.md`

Input: `plan.md`.

Before implementation, ask whether the user wants sequential execution or subagent parallelization when the plan has genuinely parallel phases. Implement the plan, keeping status and capability changes in step. During and after implementation, write `outcome.md`.

Start `outcome.md` with a brief result summary, such as:

- `Work completed successfully.`
- `Plan partially implemented; remaining work is blocked.`
- `Implementation changed direction after verification revealed ...`

Then record:

- what changed;
- verification performed and results;
- deviations from `plan.md`;
- natural-language follow-up notes or deferred issues.

Follow-up notes are not automatically TCW items. Creating follow-up work items is a closeout decision for the user.

## 5. Verification and refinement -> `refined-outcome.md`

Input: `outcome.md`.

Stop for user verification. Do not silently complete the item after implementation. Discuss the result, the verification evidence, and the follow-up notes. If the user requests tweaks, make them and remain in this stage until they give explicit approval to close out the current item.

Write `refined-outcome.md` with:

- the user's verification decision;
- refinements made after the initial implementation;
- key decisions about deferred work;
- final verification evidence;
- closeout choices selected by the user.

## Closeout decisions

After verification/refinement, ask the user to decide:

- completion route: local merge target, PR, or leave branch/worktree as-is;
- documentation updates still needed;
- whether natural-language follow-ups should become new TCW backlog items;
- version bump: major, minor, patch, or no version bump.

Before `tcw work complete`, reconcile capabilities for product changes and evaluate Documentation Sync triggers. Then run `tcw work complete <slug> --resolution <done|wontfix|duplicate|superseded> --confirm` when the user has approved closeout.

## Command behavior

`/tcw-plan-work` runs stages 1-3. It accepts either an existing work item slug/path or a chat request that the agent turns into a new backlog item.

`/tcw-drive-work-to-completion` detects the current stage from the item status and existing artifacts, runs all missing stages through implementation, and stops in verification/refinement for explicit user approval before completion.
