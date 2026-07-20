---
description: Review TCW backlog items for stale, outdated, misplaced, duplicate, blocked, or vague work and recommend cleanup actions.
---

Use the `tcw-work` skill. This is an AI-driven backlog review workflow, not a
`tcw` CLI subcommand.

Goal: review each backlog work item in board order and keep the backlog relevant,
actionable, and correctly located.

Start with `tcw work list --status backlog`. For each backlog item, read the
item folder with `tcw work path <slug>` and inspect `initial-request.md`,
`spec.md`, `plan.md`, `content.md`, `capabilities.yaml`, and `state.yaml` when
present.

Review for:

- **Already completed:** the work appears to have shipped or been completed
  outside the lifecycle. Recommend completing the item, usually with
  `--resolution done`, after evidence is verified.
- **Outdated:** plans or specs reference files, APIs, architecture, frameworks,
  commands, or capability entries that no longer exist or have been replaced.
- **Wrong repository / node:** the item belongs in another TCW node or should be
  split across nodes. Recommend moving, delegating, escalating, or creating
  replacement work items in the proper homes.
- **Duplicate or superseded:** another backlog, active, or completed item covers
  the same work. Recommend duplicate or superseded resolution, or merge the
  useful context into the better item.
- **Unactionable or oversized:** the item lacks acceptance criteria, has a vague
  request, has no clear next implementation step, or should be decomposed with
  `tcw work new "<subtask>" --parent <slug>`.
- **Blocked without a next action:** blockers are stale, already completed, or
  external but do not name an owner, wait condition, or follow-up.
- **Capability drift:** `capabilities.yaml` references missing capability files,
  has stale status assumptions, or no longer matches the capability ledger.
- **Tag hygiene:** the item has no tags despite matching a useful registered
  category, carries an irrelevant tag, or reveals a broadly useful category
  missing from the project registry. Inspect `tcw work tags list`; recommend
  `tcw work tags add <tag>` only for reusable categories, apply tags with
  `tcw work edit <slug> --tag <tag>`, and remove irrelevant tags with
  `tcw work edit <slug> --untag <tag>`.

For each item, produce a concise report:

```
<slug> | <recommendation> | <severity> | <reason>
  evidence: <specific evidence>
  action: <exact next step or command>
```

Do not silently mutate, drop, complete, or move items. Ask for approval before
performing cleanup actions, including tag registration or item tag changes. When
the user approves changes, use TCW commands for state transitions and tag edits
whenever a command exists, and preserve useful context in the remaining or
replacement work item.
