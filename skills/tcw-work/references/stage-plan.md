# Stage: plan

## Purpose

Decide *how*, in ordered steps someone else could follow. The plan is where
sequencing risk is discovered — before it is discovered by a half-finished
implementation.

## Inputs

`initial-request.md`, `spec.md`.

Repository discovery is unrestricted.

## Produce

`plan.md`, in the item's folder.

Required: ordered tasks, each with what it changes and how it is verified; the
**Documentation Sync** evaluation (a named task per entry whose trigger will
fire); and a **Verification** section covering anything the suite cannot check.

For an epic, `plan.md` is a coordination plan: child boundaries, delegation
commands, dependency order, and rollup checkpoints. See `epic-deltas.md`.

Optional `## Notes`.

`plan.md` may declare a bounded DAG of stage documents when selective loading
materially reduces context. Read the manifest first, then only the relevant
stage. Dependency order there is guidance, not a lifecycle gate.

## Steps

1. Run `tcw work lifecycle --stage plan` and honor any binding it reports.
   — agent `[judgment]`
2. Order tasks so the suite is green at every commit boundary. A task that leaves
   the tree broken for the next one is two tasks. — agent `[judgment]`
3. Put the riskiest change where it is *isolated*, not where it is convenient —
   typically after its infrastructure exists and with its tests already written.
   — agent `[judgment]`
4. Before finalizing, invoke the `documentation-sync` skill to evaluate every
   entry in `AGENTS.md`,
   and name a task for each trigger expected to fire. **REQUIRED SUB-SKILL: Use
   documentation-sync.** — agent `[judgment]`
5. Record dependencies between items as blockers, not prose:
   `tcw work edit <slug> --blocked-by <ref>`. A blocker is `[gated]` — `start`
   refuses past it — while a sentence in a plan is not. — agent `[gated]`
6. Commit `plan.md` on its own, before `start`. — agent `[judgment]`

This stage is **delegable**.

## Exit

**Well:** each task names what it changes and what proves it, and the ordering
has a stated reason.

**Badly:**

- *Planning reveals the spec is wrong.* Return to `spec` and fix it. Do not plan
  around a spec you no longer believe.
- *A task cannot be verified.* Say so in the task rather than inventing a test
  that would pass either way.
- *The work is too large.* Better to find it here than at `implement`. Decompose.
