# Implementation plan

## Phase 1: Establish the shared invariant

1. Update `skills/tcw-work/SKILL.md` with a concise, always-visible rule that
   each materially changed lifecycle artifact is committed before the next
   stage begins.
2. Expand `skills/tcw-work/references/lifecycle.md` with the operational
   checkpoint sequence: validate, inspect, narrowly stage related TCW work
   files, commit, and avoid empty commits.
3. Preserve `tcw work start` as a distinct status-transition commit following
   the plan-stage commit.

## Phase 2: Apply the invariant to each lifecycle

1. Update `skills/tcw-work/references/task-lifecycle.md` so the request, spec,
   plan, outcome, and refined-outcome sections each end with a commit
   checkpoint.
2. Update `skills/tcw-work/references/epic-lifecycle.md` so epic intake,
   overview spec, coordination plan, reconciled outcome, and refined outcome
   follow the same rule.
3. Ensure epic reconcile-generated work-file changes are included only when
   they belong to the current lifecycle stage.

## Phase 3: Align the prompt wrappers

1. Update `commands/tcw-plan-work.md` to require separate ordered commits when
   it produces `initial-request.md`, `spec.md`, and `plan.md` in one invocation.
2. Update `commands/tcw-drive-work-to-completion.md` to preserve the checkpoint
   rule across every missing stage it executes.

## Phase 4: Documentation Sync

1. Update `README.md` because the public agent workflow changes, adding the
   stage-commit behavior to the `tcw-work` lifecycle summary.
2. Update `docs/release-notes/upcoming.md` because installed plugin users will
   observe the improved lifecycle behavior.
3. Do not update `docs/changelogs/upcoming.md`: this work changes instructions
   only and does not trigger `[Any-Code-Change]`.
4. Confirm that `skills/tcw-work/SKILL.md`, the required
   `[Skill-Driven-Component]` document, remains aligned with all detailed
   lifecycle references.

## Phase 5: Verification and closeout

1. Search all lifecycle and wrapper files for every artifact stage and confirm
   each path reaches explicit commit guidance.
2. Run `git diff --check`.
3. Run `tcw validate` to verify the node and work-item documents.
4. Write and commit `outcome.md` after implementation and verification.
5. Stop for user verification before writing and committing
   `refined-outcome.md` or completing the item.

## Parallelization

The edits are small and tightly coupled, so sequential execution is clearer
than subagent parallelization.
