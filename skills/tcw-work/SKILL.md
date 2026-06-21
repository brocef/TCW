---
name: tcw-work
description: Use when starting, continuing, triaging, or decomposing tcw work items — when you face a docs/work/inbox to process, are planning a change, need to start or complete an item, are resuming an active item across sessions, want to break a large item into child items (`tcw work new --parent`) so no item is too large, or are coordinating orchestrator-level work across sub-project nodes via a cross-node epic. Drives the `tcw work` CLI; does not reimplement it.
---

# Driving `tcw work`

`tcw work` is the change-tracking state machine: items move `inbox → backlog → active → completed` by changing directory; blocked is a derived overlay, not a status. This skill is the *judgment* on top of the tool. Name `tcw …` commands; never hand-edit `docs/work/` when a command exists. The capability axis is **REQUIRED SUB-SKILL: Use tcw-capabilities** at the planning and completion gates.

## Three-axis / product-first planning

Fill the item's `content.md` under `## Product changes` / `## Technical changes` / `## Meta changes` — which sections are non-empty *is* the classification. **Product-first:** if there is any product delta, run the tcw-capabilities planning gate *before* writing the technical plan.

**Write the spec and the implementation plan to files *inside the work-item folder* — `spec.md` and `plan.md`, beside `content.md`.** This is required (AGENTS.md): planning artifacts live with the item they plan, never in a scratch or separate-tree location, so they travel through the lifecycle with it and freeze in `completed/`. Don't write the spec/plan to `docs/superpowers/` or elsewhere — put them in the item folder.

## The lifecycle handshake

- **`tcw work new`** — declare the delta; for a product delta, record `Missing` capabilities (tcw-capabilities).
- **`tcw work start <slug>`** — when planning concludes and implementation begins, move the item to active. **This transition is the first implementation commit** (AGENTS.md) — commit the `start` move (with the committed `spec.md`/`plan.md`) before the first code change. Add `--worktree` to isolate the item's code in its own git worktree + branch (transitions stay on the primary checkout; edits ride the work branch and merge back).
- **during `active`** — on any capability change, run contradiction-detection (tcw-capabilities).
- **`tcw work complete <slug> --resolution <done|wontfix|duplicate|superseded> --confirm`** — the final step. Reconcile capabilities first (the tcw-capabilities ledger flip), since the DoD "capabilities reconciled" item is acknowledged here. `--force` overrides unresolved blockers.

## Resume (across sessions)

`tcw work list --status active` → `tcw work show <slug>` → read the item's `content.md` / `spec.md` / `plan.md`. For an epic, `tcw work reconcile <slug>` to refresh the rollup before choosing the next action.

## Sub-procedures (read on demand)

The core lifecycle above is self-sufficient. For these rarer situations, read the matching doc and follow it:

- **Triaging a `docs/work/inbox/` doc** (raw request / `delegate`/`escalate` drop) → [`docs/process-inbox.md`](docs/process-inbox.md)
- **Splitting a too-large item into child items** in the same repo (`--parent`) → [`docs/decompose.md`](docs/decompose.md)
- **Coordinating work across separate sub-project repos** (a cross-node `--epic`, `delegate`/`--initiative`/`reconcile`) → [`docs/cross-node-epic.md`](docs/cross-node-epic.md)

## Quick reference

| Goal | Command |
|---|---|
| triage an inbox doc | read → `tcw work new "<title>" [--initiative <slug>]` (pipe stripped body) → `git rm` the doc |
| split an item (same repo) | `tcw work new "<sub>" --parent <slug>` (child nests under it; shows indented in `list`) |
| start work | `tcw work start <slug> [--worktree]` |
| finish work | `tcw work complete <slug> --resolution done --confirm` |
| see the board | `tcw work list [--status active]` (hides completed; `--all` to include; sorts by priority, then topologically) |
| set priority | `tcw work new "<t>" --priority N` · `tcw work edit <slug> --priority N` (higher int = higher; default unspecified) |
| topology | `tcw work nodes` |
| epic rollup | `tcw work reconcile <epic-slug>` |
| hand work down / up | `tcw work delegate <child> "<t>"` · `tcw work escalate "<t>"` |
