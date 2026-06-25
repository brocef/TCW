---
description: Plan a TCW work item from either an existing item or the user's chat request, producing the lifecycle planning artifacts in the work item folder.
---

Use the `tcw-work` skill. Read `skills/tcw-work/docs/lifecycle.md` and run stages
1-3:

1. Request ingestion -> `initial-request.md`
2. Request processing -> `spec.md`
3. Spec processing -> `plan.md`

Input may be an existing TCW work item slug/path or a request written directly in
chat. If the user provides only chat text, create the initial backlog item with
`tcw work new "<title>"` and write all artifacts inside that item's folder.

For small changes, offer to compress unnecessary planning detail, but keep enough
artifact context for another agent to resume safely. Stop before implementation;
do not run `tcw work start` unless the user explicitly pivots from planning into
implementation.
