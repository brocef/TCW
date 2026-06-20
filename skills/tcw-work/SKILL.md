---
name: tcw-work
description: Use when starting, continuing, triaging, or decomposing tcw work items — when you face a docs/work/inbox to process, are planning a change, need to start or complete an item, are resuming an active item across sessions, or are splitting work into a cross-node epic. Drives the `tcw work` CLI; does not reimplement it.
---

# Driving `tcw work`

`tcw work` is the change-tracking state machine: items move `inbox → backlog → active → completed` by changing directory; blocked is a derived overlay, not a status. This skill is the *judgment* on top of the tool. Name `tcw …` commands; never hand-edit `docs/work/` when a command exists. The capability axis is **REQUIRED SUB-SKILL: Use tcw-capabilities** at the planning and completion gates.

## Recursive process-inbox

`docs/work/inbox/` holds raw request docs — including `delegate`/`escalate` drops carrying `---\nfrom: …\n[initiative: …]\n---` front-matter. Inbox holds raw `.md` docs only; `tcw work new` creates a **backlog** folder, never an inbox folder.

For each doc:
1. Read it; extract `initiative:` / `from:` from the front-matter.
2. `tcw work new "<title>" [--initiative <slug>]`, piping the **body with the front-matter stripped** as stdin (`tcw work new` reads stdin for the body but does not parse front-matter).
3. `git rm` the source doc — it has been ingested into the new backlog item.

Across child nodes (`tcw work nodes`), an orchestrator triages **its own** inbox and *delegates* down (`tcw work delegate <child> "<title>"`); it never writes into a child's tracking tree directly.

## Three-axis / product-first planning

Fill the item's `content.md` under `## Product changes` / `## Technical changes` / `## Meta changes` — which sections are non-empty *is* the classification. **Product-first:** if there is any product delta, run the tcw-capabilities planning gate *before* writing the technical plan. Put the spec and implementation plan inside the work-item folder (`spec.md`, `plan.md`).

## The lifecycle handshake

- **`tcw work new`** — declare the delta; for a product delta, record `Missing` capabilities (tcw-capabilities).
- **`tcw work start <slug>`** — begin; add `--worktree` to isolate the item's code in its own git worktree + branch (transitions stay on the primary checkout; edits ride the work branch and merge back).
- **during `active`** — on any capability change, run contradiction-detection (tcw-capabilities).
- **`tcw work complete <slug> --resolution <done|wontfix|duplicate|superseded> --confirm`** — the final step. Reconcile capabilities first (the tcw-capabilities ledger flip), since the DoD "capabilities reconciled" item is acknowledged here. `--force` overrides unresolved blockers.

## Resume (across sessions)

`tcw work list --status active` → `tcw work show <slug>` → read the item's `content.md` / `spec.md` / `plan.md`. For an epic, `tcw work reconcile <slug>` to refresh the rollup before choosing the next action.

## Decompose into a cross-node epic

1. `tcw work new --epic` in the orchestrator node (the epic).
2. `tcw work delegate <child> "<slice title>"` for each child node — or have each child run process-inbox and `tcw work new --initiative <epic-slug>`.
3. `tcw work reconcile <epic-slug>` to consolidate child progress into the epic's rollup.

## Quick reference

| Goal | Command |
|---|---|
| triage an inbox doc | read → `tcw work new "<title>" [--initiative <slug>]` (pipe stripped body) → `git rm` the doc |
| start work | `tcw work start <slug> [--worktree]` |
| finish work | `tcw work complete <slug> --resolution done --confirm` |
| see the board | `tcw work list [--status active]` |
| topology | `tcw work nodes` |
| epic rollup | `tcw work reconcile <epic-slug>` |
| hand work down / up | `tcw work delegate <child> "<t>"` · `tcw work escalate "<t>"` |
