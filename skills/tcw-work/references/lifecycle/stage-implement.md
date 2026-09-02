# Stage: implement

## Purpose

Building it.
Get your instructions on how to produce the output by running
`tcw work stage implement <slug>`.

## Inputs

`spec.md`, `plan.md`, and `rework.md` when a verification rejected an earlier
pass.

## Produce

`outcome.md` — and the code, which is not a lifecycle artifact.

## Steps

1. `tcw work start <slug>` is `[gated]` rather than advice: it refuses on an
   unresolved blocker or an inactive initiative epic, and commits the move
   itself. — agent `[gated]`
2. On a capability change, contradiction detection is discharged by a sub-skill.
   **REQUIRED SUB-SKILL: Use tcw-capabilities.** — agent `[judgment]`
3. To discharge the prompt's Documentation Sync completion gate:
   invoke the `documentation-sync` skill. **REQUIRED SUB-SKILL: Use
   documentation-sync.** — agent `[judgment]`
4. **Delegable, and this is where it pays**: the coordinating session ends up
   holding `outcome.md` rather than an entire diff. See
   [`delegation.md`](../procedures/delegation.md). — agent `[judgment]`
