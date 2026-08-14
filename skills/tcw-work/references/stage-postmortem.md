# Stage: postmortem

## Purpose

Locating the earliest catchable miss. `tcw work stage postmortem <slug>` prints
the methodology; this document carries only what the CLI cannot.

## Inputs

`refined-outcome.md`, `rework.md`, `outcome.md`, `plan.md`, `spec.md`,
`initial-request.md`.

## Produce

`post-mortem.md`.

## Steps

1. **Delegable to a read-only subagent**, and cheaply so: the stage reads the
   whole artifact spine and writes one file. Under Claude the `tcw-post-mortem`
   agent exists for it; under Codex, a `.codex/agents/` definition or an inline
   run. See [`delegation.md`](delegation.md). — agent `[judgment]`
