# Stage: plan

## Purpose

Deciding how.
Get your instructions on how to produce the output by running
`tcw work stage plan <slug>`.

## Inputs

The item's body — `initial-request.md` when the `request` stage has written
one, `intake.md` otherwise — and `spec.md`. See [`commands.md`](../commands.md) § The body
surface.

## Produce

`plan.md`. For an epic it is a coordination plan instead: child boundaries,
delegation commands, dependency order, and rollup checkpoints — see
[`epic-deltas.md`](../epic-deltas.md).

`plan.md` may also declare a bounded DAG of stage documents when selective
loading materially reduces context: read the manifest first, then only the
relevant stage. Dependency order there is guidance, not a lifecycle gate.

## Steps

1. To discharge the prompt's Documentation Sync evaluation:
   invoke the `documentation-sync` skill. **REQUIRED SUB-SKILL: Use
   documentation-sync.** — agent `[judgment]`
2. `tcw work edit <slug> --blocked-by <ref>` is why the prompt wants a blocker
   rather than a sentence: `start` refuses past one, and prose is not
   enforcement. — agent `[gated]`
3. **Delegable.** See [`delegation.md`](../procedures/delegation.md). — agent `[judgment]`
