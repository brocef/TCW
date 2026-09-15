---
name: commands-verify-work
description: Verify a finished TCW work item with the user and record the acceptance decision.
when_to_use: Use when a user asks to verify, review, accept, or reject a finished TCW work item — assessing it against its spec, stopping for the user's decision, and recording it as refined-outcome.md or rework.md.
allowed-tools: Bash(tcw *), Bash(git *), Read, Edit, Write
metadata:
    author: Brian Cefali
license: Apache-2.0
---

Use the `work` skill. This skill covers the **`verify` stage** and the
`submit` / `rework` transitions.

Read the `work` skill's `stage-verify.md`.

Assess the work against `spec.md`'s acceptance criteria — read the diff, run the
checks, form an opinion. That half is delegable to a read-only subagent
(the `work` skill's `delegation.md`); the decision that follows is not.

**Present the assessment and stop for the user.** Do not decide on their behalf.
`tcw work submit <slug>` first if the item is still `active`, so its status
reflects that it is waiting.

On acceptance, write `refined-outcome.md`. On rejection, write `rework.md`,
delete `refined-outcome.md`, and run `tcw work rework <slug>` — the tool refuses
while that file is present.

Reconcile capabilities before closeout. **REQUIRED SUB-SKILL: Use
capabilities.**
