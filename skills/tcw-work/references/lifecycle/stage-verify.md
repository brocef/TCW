# Stage: verify

## Purpose

Getting the user's decision.
Get your instructions on how to produce the output by running
`tcw work stage begin verify <slug>`.

## Inputs

`spec.md`, `outcome.md`, and the diff between them.

## Produce

`refined-outcome.md` or `rework.md`.

## Steps

1. **The assess half is delegable; the decide half is not.** Reading the diff
   against the criteria and running the checks goes to a read-only subagent —
   the `tcw-verifier` agent exists for it under Claude, and
   [`delegation.md`](../procedures/delegation.md) has the rules. Codex has no `agents/`
   directory, so run it inline there; nothing about the stage depends on the
   agent. — agent `[judgment]`
2. **Presenting the assessment and stopping for the decision** is the half no
   subagent can take and no command enforces. — user `[judgment]`
3. Capability reconciliation before closeout is discharged by a sub-skill.
   **REQUIRED SUB-SKILL: Use tcw-capabilities.** — agent `[judgment]`
4. `tcw work submit` and `tcw work rework` are `[gated]`, not conventions.
   — agent `[gated]`
5. The version cut the prompt says to offer: the menu is major / minor / patch,
   or keep the current version and update the changelog files in place, or —
   when the last tag was cut locally and never pushed — fold this work into that
   unpublished version rather than stacking a second one on it.
   `documentation-sync`'s `references/cut-version.md` runs it, and
   `/tcw-cut-version` is the Claude shortcut to the same thing. — user
   `[judgment]`
