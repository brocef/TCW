---
description: Plan a TCW work item from an existing item or the user's chat request, producing the lifecycle planning artifacts in the work item folder.
---

Use the `tcw-work` skill. This command covers the stage range **`request` →
`plan`**.

Read `skills/tcw-work/SKILL.md`, find the first missing artifact, and run the
stages from there through `plan.md`, loading **only** each stage's own document:

- `references/stage-request.md` → `initial-request.md`
- `references/stage-spec.md` → `spec.md`
- `references/stage-plan.md` → `plan.md`

For a `type: epic` item, also read `references/epic-deltas.md` — the same three
stages, with an overview spec and a coordination plan.

Each artifact is a separate checkpoint: write it, inspect the diff, stage
narrowly, and commit before starting the next stage. Do not batch several stages
into one commit, and do not create empty commits for artifacts that were already
complete. TCW commits status transitions itself; do not commit those by hand.

Stop at `plan.md`. Do not run `tcw work start` or write any code — that is
`/tcw-drive-work-to-completion`. Ask the user to review the plan first.

$ARGUMENTS
