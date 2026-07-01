---
name: tcw-work
description: Use when starting, continuing, triaging, planning, implementing, verifying, or decomposing tcw work items — when a user asks to plan work, drive work to completion, process a docs/work/inbox request, start or complete an item, resume an active item across sessions, break a large item into child items (`tcw work new --parent`), or coordinate orchestrator-level work across sub-project nodes via a cross-node epic. Drives the `tcw work` CLI; does not reimplement it.
---

# Driving `tcw work`

`tcw work` is the change-tracking state machine: items move `inbox → backlog → active → completed` by changing directory; blocked is a derived overlay, not a status. This skill is the *judgment* on top of the tool. Name `tcw …` commands; never hand-edit `docs/work/` when a command exists. The capability axis is **REQUIRED SUB-SKILL: Use tcw-capabilities** at the planning and completion gates.

Work is the final layer in the TCW chain: `Vocabulary -> Features ->
Capabilities -> Work`. A work item can describe changes to any earlier layer:
new vocabulary, new or changed features, new or changed capabilities, code, docs,
or the project process itself. For product changes, check the earlier layers in
order before settling the plan: vocabulary terms first, then taxonomy Features,
then capabilities. See `tcw-plugin` for the cross-skill map.

**Node identity:** `tcw init` marks the **current directory** a TCW node by writing a `tcw-config.yaml` sentinel there. All `tcw` commands resolve to the nearest `tcw-config.yaml` ancestor — so in a multi-project repo, `cd project-b && tcw work list` shows project-b's board. If a command fails with "no tcw … node here", run `tcw init` in the project folder first. Cross-node discovery (`tcw work nodes` / epics / delegate / escalate) still locates peers by git-repo root (see `docs/cross-node-epic.md`).

## Primary lifecycle

Drive work through the TCW SDLC. Read [`docs/lifecycle.md`](docs/lifecycle.md) whenever planning a work item, driving an item toward completion, resuming mid-flight work whose next stage is unclear, or compressing stages for a small change. It dispatches to the epic or task lifecycle based on the item relation fields.

The artifact spine is:

`initial-request.md` → `spec.md` → `plan.md` → `outcome.md` → `refined-outcome.md`

`initial-request.md` is always-present — it serves as the item body/overview
surface, scratch space, and the managed rollup target for epics.

For small changes, ask whether to compress unnecessary planning detail, but keep the work item as the durable source of truth and write any artifact that is needed to resume or review the work. **Product-first:** if there is any product delta, check whether taxonomy Vocabulary or Feature entries need to be added/updated, then run the tcw-capabilities planning gate before writing the technical plan.

## The lifecycle handshake

**You drive the transitions — the tool never moves an item for you, so its status is only as accurate as you keep it.** Two transitions are mandatory and the easy ones to forget:

- **Before you write the first line of code for an item, run `tcw work start <slug>`.** If you ever notice you're editing code while the item is still in `backlog`, you skipped this — stop and start it.
- **The moment the work is done and verified, run `tcw work complete <slug> …`.** Don't leave a shipped item sitting in `active`.

Keep status in step *as you go*; don't batch the transitions at the end. The per-command detail:

- **`tcw work new`** — declare the delta; for a product delta, record `Missing` capabilities (tcw-capabilities).
- **`tcw work start <slug>`** — when planning concludes and implementation begins, move the item to active. **This transition is the first implementation commit** (AGENTS.md) — commit the `start` move (with the committed `spec.md`/`plan.md`) before the first code change. Add `--worktree` to isolate the item's code in its own git worktree + branch (transitions stay on the primary checkout; edits ride the work branch and merge back).
- **during `active`** — on any capability change, run contradiction-detection (tcw-capabilities).
- **`tcw work complete <slug> --resolution <done|wontfix|duplicate|superseded> --confirm`** — the final step. Reconcile capabilities first (the tcw-capabilities ledger flip), since the DoD "capabilities reconciled" item is acknowledged here. `--force` overrides unresolved blockers. For a `--worktree` item, `complete` **merges the work branch back** into the primary checkout before tearing it down, and **fails closed** on a merge conflict (branch + worktree left intact, item stays `active`) — resolve the conflict and re-run rather than `--force`ing past it.

## Resume (across sessions)

`tcw work list --status active` → `tcw work show <slug>` → read the item's `initial-request.md` body plus whatever lifecycle artifacts exist (`spec.md`, `plan.md`, `outcome.md`, `refined-outcome.md`). For an epic, `tcw work reconcile <slug>` to refresh the rollup before choosing the next action.

## Sub-procedures (read on demand)

The core lifecycle above is self-sufficient. For these rarer situations, read the matching doc and follow it:

- **Planning, implementation, verification, and closeout across the SDLC** → [`docs/lifecycle.md`](docs/lifecycle.md)
- **Triaging a `docs/work/inbox/` doc** (raw request / `delegate`/`escalate` drop) → [`docs/process-inbox.md`](docs/process-inbox.md)
- **Splitting a too-large item into child items** in the same repo (`--parent`) → [`docs/decompose.md`](docs/decompose.md)
- **Coordinating work across separate sub-project repos** (a cross-node `--epic`, `delegate`/`--initiative`/`reconcile`) → [`docs/cross-node-epic.md`](docs/cross-node-epic.md)

## Quick reference

| Goal | Command |
|---|---|
| plan a request/item | `/tcw-plan-work` or read [`docs/lifecycle.md`](docs/lifecycle.md) |
| drive remaining stages | `/tcw-drive-work-to-completion` or read [`docs/lifecycle.md`](docs/lifecycle.md) |
| triage an inbox doc | read → `tcw work new "<title>" [--initiative <slug>]` → write `initial-request.md` → `git rm` the doc |
| split an item (same repo) | `tcw work new "<sub>" --parent <slug>` (child nests under it; shows indented in `list`) |
| start work | `tcw work start <slug> [--worktree]` |
| finish work | `tcw work complete <slug> --resolution done --confirm` |
| see the board | `tcw work list [--status active]` (hides completed; `--all` to include; `--include-descendants` to also list every descendant node's board grouped by node; shows lifecycle artifact letters in the stages column; sorts by priority, then topologically) |
| audit backlog relevance | `tcw work audit-work-backlog` (read-only cleanup recommendations for stale, duplicate, broken, blocked, vague, or misplaced backlog items) |
| migrate external plans | `tcw work consolidate-plans [PATH ...] [--apply] [--delete]` (dry-run first; converts external planning docs into backlog items) |
| find item files | `tcw work path <slug>` |
| set priority | `tcw work new "<t>" --priority N` · `tcw work edit <slug> --priority N` (higher int = higher; default unspecified) |
| set estimates | `tcw work new "<t>" --effort <l> --complexity <l>` · `tcw work edit <slug> --effort <l> --complexity <l>` (`<l>` = low\|medium\|high\|very-high; optional; shown in `show`, not `list`) |
| topology | `tcw work nodes` |
| epic rollup | `tcw work reconcile <epic-slug>` |
| hand work down / up | `tcw work delegate <child> "<t>"` · `tcw work escalate "<t>"` |
