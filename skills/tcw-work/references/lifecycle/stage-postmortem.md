# Stage: postmortem

## Purpose

Locating the earliest catchable miss.
Get your instructions on how to produce the output by running
`tcw work stage begin postmortem <slug>`.

## Inputs

`refined-outcome.md`, `rework.md`, `outcome.md`, `plan.md`, `spec.md`, and the
body the item started from — `initial-request.md`, or the `intake.md` beneath it
when the `request` stage never ran.

## Produce

`post-mortem.md`.

## Steps

1. **Delegable to a read-only subagent**, and cheaply so: the stage reads the
   whole artifact spine and writes one file. Under Claude the `tcw-post-mortem`
   agent exists for it; under Codex, a `.codex/agents/` definition or an inline
   run. See [`delegation.md`](../procedures/delegation.md). — agent `[judgment]`
