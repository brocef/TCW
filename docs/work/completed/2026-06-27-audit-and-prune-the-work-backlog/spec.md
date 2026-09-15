# Spec — Audit and prune the work backlog

## Capability changes

- **New:** `work/audit-work-backlog#audit-and-prune-the-work-backlog` remains
  `Missing` until this item lands.

## Problem

The backlog can collect old, vague, misplaced, duplicate, or already-completed
items. TCW gives those items durable state, but there is no command that helps a
user periodically review whether backlog entries are still relevant and
actionable.

## Goals

- Add an audit command that reviews backlog items in board order.
- Produce a structured report with evidence and recommended actions.
- Include the user's requested checks: stale/completed, outdated references, and
  wrong-repo placement.
- Add practical pruning checks for duplicates, scope/actionability, blocked
  items, and capability drift.

## Non-goals

- Do not silently move, complete, drop, or rewrite work items in the initial
  command.
- Do not require remote issue tracker integration.
- Do not attempt perfect semantic code archaeology; the audit should be useful
  and evidence-backed, not omniscient.

## Current-state findings

- `tcw work list --status backlog` already returns backlog items ordered by
  priority and blockers through `FsWorkStore.board(status="backlog")`.
- Work item state includes slug, title, phase, priority, blocked_by,
  capabilities, parent, and body.
- `capabilities.yaml` is intentionally read as an opaque blob by the work model,
  but existing recursion code can safely surface conforming capability deltas.
- Multi-node TCW projects are discovered through node sentinels and child-node
  helpers, so wrong-repo advice can be phrased as "move to node X" without
  hard-coding directory ancestry into the abstract model.

## Proposed behavior

Add `tcw work audit-work-backlog` with default report-only behavior. For each
visible backlog item, emit a recommendation with severity, reason, evidence, and
suggested action.

Review checks:

- **Possibly completed:** look for completed items with matching slug/title
  terms, code/docs evidence that the requested behavior exists, or a plan whose
  acceptance criteria already appear satisfied.
- **Outdated references:** check lifecycle artifacts and `content.md` for local
  path references that no longer exist, stale symbol/file references where cheap
  to verify, and terms indicating removed frameworks or architecture.
- **Wrong repo/node:** use TCW node discovery and item subject clues to recommend
  another node when the item clearly belongs elsewhere.
- **Duplicate or superseded:** compare backlog items against each other and
  completed items by slug/title/body terms and explicit references.
- **Unactionable:** flag missing or empty lifecycle artifacts, missing
  acceptance criteria, vague titles, or over-large items that should be split.
- **Blocked-without-next-action:** flag external blockers without owner/date or
  blocked items whose blocker is completed/dropped but still recorded.
- **Capability drift:** when `capabilities.yaml` exists, verify referenced
  capability files/headings still resolve and statuses still make sense for the
  proposed delta.

Suggested actions:

- `keep`
- `revise`
- `split`
- `move-to-node <node>`
- `complete-as-done`
- `complete-as-duplicate`
- `complete-as-superseded`
- `drop`

## Output shape

Start with text output that is easy to read in a terminal:

```
<slug> | <recommendation> | <severity> | <reason>
  evidence: <short evidence line>
  action: <suggested next command or manual step>
```

JSON output can be deferred unless an implementation pass finds an immediate
automation consumer.

## Acceptance criteria

- `tcw work audit-work-backlog` appears in help and command dispatch.
- The command reads backlog items in board order.
- The command does not mutate work items by default.
- The report covers stale/completed, outdated references, wrong-node placement,
  duplicate/superseded, unactionable, blocked, and capability-drift checks.
- Missing or malformed artifacts degrade to findings, not crashes.
- Tests cover clean backlog, stale/completed candidate, broken local reference,
  duplicate candidate, malformed `capabilities.yaml`, and multi-node placement
  evidence.

## Risks and dependencies

- Some checks are heuristic; output should explain evidence and confidence.
- Wrong-node detection can be noisy. Prefer "candidate node" wording unless the
  evidence is strong.
- Completing or moving items should remain a separate user/agent action until a
  future command explicitly scopes apply behavior.
