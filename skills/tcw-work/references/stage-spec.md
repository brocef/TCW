# Stage: spec

## Purpose

Deciding what to build. `tcw work stage spec <slug>` prints the methodology;
this document carries only what the CLI cannot.

## Inputs

The item's body — `initial-request.md` when the `request` stage has written
one, `intake.md` otherwise. See `commands.md` § The body surface.

## Produce

`spec.md`. An epic's spec replaces the **Design** section with the child
boundaries and their ordering constraints — see
[`epic-deltas.md`](epic-deltas.md).

## Steps

1. On a product delta, the ledger check the prompt requires is discharged by a
   sub-skill. **REQUIRED SUB-SKILL: Use tcw-capabilities.** — agent `[judgment]`
2. **Delegable.** `Inputs` above is the subagent's context brief and `Produce`
   its return contract; the coordinating session re-reads the artifact and
   checks the required sections before moving on. See
   [`delegation.md`](delegation.md). — agent `[judgment]`
3. Too large for one item: [`decompose.md`](decompose.md) for nested pieces,
   [`epic-deltas.md`](epic-deltas.md) for independently scheduled ones. — agent
   `[judgment]`
