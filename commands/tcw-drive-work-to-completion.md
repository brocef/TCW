---
description: Drive a TCW work item through every remaining lifecycle stage up to user verification, then close out only after explicit approval.
---

Use the `tcw-work` skill. Read `skills/tcw-work/docs/lifecycle.md` and detect the
current stage from the item status and existing artifacts:

- missing `initial-request.md` -> start at request ingestion;
- missing `spec.md` -> continue with request processing;
- missing `plan.md` -> continue with spec processing;
- missing `outcome.md` -> start/continue implementation;
- missing or stale `refined-outcome.md` -> stop for verification and refinement.

Run all remaining stages through implementation. Before implementation begins, run
`tcw work start <slug>` if the item is not active and ask whether to execute
sequentially or parallelize genuinely independent phases with subagents.

Do not silently complete the item after implementation. Stop in verification and
refinement until the user explicitly approves closeout. At closeout, confirm merge
or PR route, documentation updates, follow-up TCW item creation, and version bump
choice before running `tcw work complete <slug> --resolution ... --confirm`.
