# Stage: plan

## Purpose

Deciding how. `tcw work stage plan <slug>` prints the methodology; this
document carries only what the CLI cannot.

## Inputs

`initial-request.md`, `spec.md`.

## Produce

`plan.md`. For an epic it is a coordination plan instead: child boundaries,
delegation commands, dependency order, and rollup checkpoints — see
[`epic-deltas.md`](epic-deltas.md).

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
3. **Delegable.** See [`delegation.md`](delegation.md). — agent `[judgment]`
