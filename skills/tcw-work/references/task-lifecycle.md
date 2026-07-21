# Task lifecycle

Use this lifecycle for standalone work items and initiative child tasks. The artifact spine is:

`initial-request.md` -> `spec.md` -> `plan.md` -> `outcome.md` -> `refined-outcome.md`

## 1. Request ingestion -> `initial-request.md`

Input can be either:

- a chat request that has not yet been captured as a TCW item;
- an existing TCW work item folder whose request is still a sketch;
- an existing TCW work item whose request is a blank scaffold awaiting population;
- a transient `docs/work/inbox/` request created by TCW's `delegate` or `escalate` commands, or dropped there directly by a user.

If the user provides the request only in chat, create a backlog item with `tcw work new "<title>"` and use its folder as the artifact home. If processing `docs/work/inbox/`, inspect it with `tcw work inbox show <entry>` and accept it with `tcw work inbox accept <entry> [--title <title>]`; acceptance generates the durable `initial-request.md` and removes the raw source only after success.

Discuss the request enough to remove ambiguity and capture the broad strokes. Only basic research should be needed here. Write `initial-request.md` with:

- the user's requested outcome;
- known constraints and non-goals;
- open questions that remain acceptable for spec planning;
- any user decisions already made.

For an initiative child task, preserve the `initiative: <epic-slug>` relation. Do not mutate the parent epic directly from the child node; report useful status and outcomes so the epic can reconcile.

Checkpoint the request stage before spec work: inspect and commit
`initial-request.md` together with the new item's related TCW metadata. Stage
only those work files.

## 2. Request processing -> `spec.md`

Input: `initial-request.md`.

Do the deeper discovery pass. Determine feasibility, scope, urgency, interactions with related work items, and how the current project works. For product work, run the tcw-capabilities planning gate before settling the technical shape. When useful, sketch UI flows, API shapes, data contracts, or migration paths.

Write `spec.md` with:

- `## Capability changes` as the first content section when there is a product delta;
- problem, goals, non-goals, constraints, and affected surfaces;
- current-state findings with file references where relevant;
- proposed behavior and acceptance criteria;
- risks, dependencies, and related work items.

Checkpoint the spec stage before plan work: inspect and commit `spec.md` and
only the related TCW work files changed while producing it.

## 3. Spec processing -> `plan.md`

Input: `spec.md`.

Translate the spec into an implementation plan. Deep-dive the repository, dependencies, or sub-projects enough that the plan can be executed without rediscovering the main design. Break the work into phases and call out which phases can run in parallel.

Write `plan.md` with:

- ordered phases and concrete tasks;
- parallelization opportunities and dependencies;
- expected file/module touch points;
- verification commands;
- explicit documentation-sync tasks for triggers that are expected to fire.

For a plan large enough that selective loading materially reduces context,
`plan.md` may instead be a concise entry point with canonical `stages`
frontmatter and Overview / Stage ordering sections. Each declared stage maps to
`plan/<id>.md` and contains non-empty Objective, Pre-stage checks,
Implementation, and Post-stage checks sections. Commit `plan.md` and every
declared stage document together as the single plan checkpoint. Do not use
stages for independent ownership or lifecycle state; use nested work items or
initiative tasks for those needs.

Checkpoint the plan stage before implementation: inspect and commit `plan.md`
and only the related TCW work files changed while producing it.

When planning is complete and implementation is about to begin, run `tcw work start <slug>` before the first code edit. Commit that status change as a separate commit after the plan-stage checkpoint and before implementation changes. If the task has `initiative: <epic-slug>`, the epic must be active first. Use `--worktree` when isolation is useful; in that flow the primary checkout carries status transitions and the work branch carries implementation edits.

## 4. Implementation -> `outcome.md`

Input: `plan.md`.

When the plan declares stages, read `plan.md` first and then only the relevant
stage document. Run its pre-stage checks before changing code and its post-stage
checks afterward. Treat dependencies as ordering guidance, not transition gates.
Record informal progress in plan or outcome prose without deriving stage status.

Before implementation, ask whether the user wants sequential execution or subagent parallelization when the plan has genuinely parallel phases. Implement the plan, keeping status and capability changes in step. During and after implementation, write `outcome.md`.

Start `outcome.md` with a brief result summary, such as:

- `Work completed successfully.`
- `Plan partially implemented; remaining work is blocked.`
- `Implementation changed direction after verification revealed ...`

Then record:

- what changed;
- verification performed and results;
- deviations from `plan.md`;
- natural-language follow-up notes or deferred issues;
- for initiative child tasks, what the parent epic should know at its next reconcile.

Follow-up notes are not automatically TCW items. Creating follow-up work items is a closeout decision for the user.

After implementation and its evidence are recorded, checkpoint the outcome
stage before verification/refinement: inspect and commit `outcome.md` with only
the related TCW work files changed during this stage. Keep unrelated
working-tree changes unstaged.

## 5. Verification and refinement -> `refined-outcome.md`

Input: `outcome.md`.

Stop for user verification. Do not silently complete the item after implementation. Discuss the result, the verification evidence, and the follow-up notes. If the user requests tweaks, make them and remain in this stage until they give explicit approval to close out the current item.

Write `refined-outcome.md` with:

- the user's verification decision;
- refinements made after the initial implementation;
- key decisions about deferred work;
- final verification evidence;
- closeout choices selected by the user.

After the user-approved refinements and final evidence are recorded, checkpoint
the refinement stage: inspect and commit `refined-outcome.md` with only its
related TCW work files before running the completion transition.

## Closeout decisions

After verification/refinement, ask the user to decide:

- completion route: local merge target, PR, or leave branch/worktree as-is;
- documentation updates still needed;
- whether natural-language follow-ups should become new TCW backlog items;
- version bump: major, minor, patch, or no version bump.

Before `tcw work complete`, reconcile capabilities for product changes and evaluate Documentation Sync triggers. Then run `tcw work complete <slug> --resolution <done|wontfix|duplicate|superseded> --confirm` when the user has approved closeout. After it succeeds, inspect and commit the completion status move and related TCW work-file changes as the final lifecycle checkpoint.
