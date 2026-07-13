---
description: Plan a TCW work item from either an existing item or the user's chat request, producing the lifecycle planning artifacts in the work item folder.
---

Use the `tcw-work` skill. Read `skills/tcw-work/references/lifecycle.md`, choose the
task or epic lifecycle, and run the planning stages for that lifecycle.

For a task, this means request ingestion, request processing, and spec
processing: `initial-request.md`, `spec.md`, and `plan.md`.

For an epic, this means initiative intake, overview spec, and coordination /
delegation plan using the same artifact names.

Treat each produced artifact as a separate checkpoint. After writing or
materially updating `initial-request.md`, commit it and its related TCW work
files before creating `spec.md`; commit the spec stage before creating
`plan.md`; then commit the plan stage. Inspect each diff and stage narrowly so
unrelated changes are not included. Do not create empty commits for artifacts
that already existed unchanged.

Input may be an existing TCW work item slug/path or a request written directly in
chat. If the user provides only chat text, create the initial backlog item with
`tcw work new "<title>"` and write all artifacts inside that item's folder.

For small changes, offer to compress unnecessary planning detail, but keep enough
artifact context for another agent to resume safely. Stop before implementation;
do not run `tcw work start` unless the user explicitly pivots from planning into
implementation.
