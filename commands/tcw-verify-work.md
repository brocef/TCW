---
description: Verify a finished TCW work item with the user and record the acceptance decision.
---

Use the `tcw-work` skill. This command covers the **`verify` stage** and the
`submit` / `rework` transitions.

Read `skills/tcw-work/references/stage-verify.md`.

Assess the work against `spec.md`'s acceptance criteria — read the diff, run the
checks, form an opinion. That half is delegable to a read-only subagent
(`references/delegation.md`); the decision that follows is not.

**Present the assessment and stop for the user.** Do not decide on their behalf.
`tcw work submit <slug>` first if the item is still `active`, so its status
reflects that it is waiting.

On acceptance, write `refined-outcome.md`. On rejection, write `rework.md`,
delete `refined-outcome.md`, and run `tcw work rework <slug>` — the tool refuses
while that file is present.

Reconcile capabilities before closeout. **REQUIRED SUB-SKILL: Use
tcw-capabilities.**

$ARGUMENTS
