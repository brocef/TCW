---
name: commands-plan-work
description: Plan a TCW work item from an existing item or the user's chat request, producing the lifecycle planning artifacts in the work item folder.
when_to_use: Use when a user asks to plan a TCW work item, or to turn a chat request into a planned item — running the request, spec and plan stages and stopping once plan.md is written, before any code.
allowed-tools: Bash(tcw *), Bash(git *), Read, Edit, Write
metadata:
    author: Brian Cefali
license: Apache-2.0
dynamic_skill: false # which skills a project may override, and why: ../README.md
---

Use the `work` skill. This skill covers the stage range **`request` →
`plan`**.

Read the `work` skill's `SKILL.md`, find the first missing artifact, and run the
stages from there through `plan.md`, invoking the `work-stage` skill for
**only** the stage you are running:

- `work-stage request <slug>` → `initial-request.md`
- `work-stage spec <slug>` → `spec.md`
- `work-stage plan <slug>` → `plan.md`

For a `type: epic` item, also read the `work` skill's `epic-deltas.md` — the same three
stages, with an overview spec and a coordination plan.

Planning from a chat request with no existing item: run the `work-create`
skill first, in interactive mode. The chat request answers its references and
origin questions. If it reports `already tracked`, `amended` or
`already in progress`, stop and report that. If it reports `revised`, resume
from the first missing artifact.

Each artifact is a separate checkpoint: write it, inspect the diff, stage
narrowly, and commit before starting the next stage. Do not batch several stages
into one commit, and do not create empty commits for artifacts that were already
complete. TCW commits status transitions itself; do not commit those by hand.

Stop at `plan.md`. Do not run `tcw work start` or write any code — that is
the `commands-drive-work-to-completion` skill. Ask the user to review the plan first.
