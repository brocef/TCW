---
name: tcw-work
description: Drives the `tcw work` change-tracking CLI — the Work axis of TCW (Taxonomy · Capabilities · Work). Use when planning, starting, implementing, verifying, or completing a tcw work item; resuming one across sessions; triaging a docs/work/inbox request; decomposing an item into child items; or coordinating a cross-node epic. Does not reimplement the CLI.
when_to_use: Use when starting, continuing, triaging, planning, implementing, verifying, or decomposing tcw work items — when a user asks to plan work, drive work to completion, process a docs/work/inbox request, start or complete an item, resume an active item across sessions, break a large item into child items (`tcw work new --parent`), or coordinate orchestrator-level work across sub-project nodes via a cross-node epic.
allowed-tools: Bash(tcw *), Bash(git *), Read, Edit, Write
metadata:
  author: Brian Cefali
license: Apache-2.0
---

# Driving `tcw work`

`tcw work` is the change-tracking state machine: raw inbox entries are accepted into `backlog → active → completed`; blocked is a derived overlay, not a status. This skill is the *judgment* on top of the tool. Name `tcw …` commands; never hand-edit `docs/work/` when a command exists. The capability axis is **REQUIRED SUB-SKILL: Use tcw-capabilities** at the planning and completion gates.

> **Web editing:** Work items, lifecycle artifacts, and the `capabilities.yaml` sidecar can also be created and edited through the local `tcw serve` web app. The web-complete modal surfaces the DoD acknowledgments and the capabilities reconciliation reminder, matching the CLI gate.

Work is the final layer in the TCW chain: `Vocabulary -> Features ->
Capabilities -> Work`. A work item can describe changes to any earlier layer:
new vocabulary, new or changed features, new or changed capabilities, code, docs,
or the project process itself. For product changes, check the earlier layers in
order before settling the plan: vocabulary terms first, then taxonomy Features,
then capabilities. See `tcw-plugin` for the cross-skill map.

**Project identity:** `tcw init --id <project-id>` marks the current directory
with a canonical ID in `tcw-config.yaml`; existing configured nodes may omit the
flag. Commands still select the nearest enclosing sentinel, but all
cross-project operations follow only reciprocal `connected-projects`
registrations. Project locators may be relative, absolute, nested, or elsewhere;
TCW never scans for peers. Every command fails closed on an ID-less or invalid
graph. See `references/cross-node-epic.md`.

## Primary lifecycle

Drive work through the TCW SDLC. Read [`references/lifecycle.md`](references/lifecycle.md) whenever planning a work item, driving an item toward completion, resuming mid-flight work whose next stage is unclear, or compressing stages for a small change. It dispatches by the item relation fields to one of two leaves, which you can also read directly: [`references/epic-lifecycle.md`](references/epic-lifecycle.md) for a `type: epic` item, [`references/task-lifecycle.md`](references/task-lifecycle.md) for a standalone item or initiative child task.

The artifact spine is:

`initial-request.md` → `spec.md` → `plan.md` → `outcome.md` → `refined-outcome.md`

**Commit every stage as you go.** After writing or materially updating any
lifecycle artifact, commit that artifact and the related TCW work files before
starting the next stage. Use narrow staging so unrelated working-tree changes
are never swept into a lifecycle checkpoint; do not create empty commits for
unchanged stages. The `tcw work start` and `tcw work complete` status moves are
separate commits at their respective transition boundaries.

`initial-request.md` is always-present — it serves as the item body/overview
surface, scratch space, and the managed rollup target for epics.

The work store exposes the bounded lifecycle artifact set through
`artifacts(slug)` and openable handles through `artifact_locator(slug, name)`.
Use those store methods for board or viewer behavior; do not reconstruct artifact
state by globbing item folders outside the filesystem adapter.

For small changes, ask whether to compress unnecessary planning detail, but keep the work item as the durable source of truth and write any artifact that is needed to resume or review the work. **Product-first:** if there is any product delta, check whether taxonomy Vocabulary or Feature entries need to be added/updated, then run the tcw-capabilities planning gate before writing the technical plan.

## Tags

Tags are a project-scoped classification vocabulary for grouping and filtering
work across lifecycle statuses. They are descriptive facets such as `cli`,
`docs`, `bug`, or `tech-debt`; they do not change priority, status, ownership, or
transition rules. Prefer a small reusable vocabulary over one-off tags that
repeat an item's title.

Each node registers its allowed tags in `tcw-config.yaml`. Manage that registry
through the CLI: `tcw work tags list`, `tcw work tags add <tag>...`, and
`tcw work tags rm <tag>...`. Removing a registered tag warns when items still
carry it, and `tcw validate` rejects that stale state until the affected items
are retagged or the tag is restored.

During request intake, inspect the registry, choose all materially applicable
tags, and create the item with repeatable `--tag <tag>` options. Register a
missing tag first only when it will be useful beyond this one item. For existing
items use `tcw work edit <slug> --tag <tag> --untag <tag>`; list filtering uses
repeatable `tcw work list --tag <tag>` with match-any semantics.

## The lifecycle handshake

**You drive the transitions — the tool never moves an item for you, so its status is only as accurate as you keep it.** Two transitions are mandatory and the easy ones to forget:

- **Before you write the first line of code for an item, run `tcw work start <slug>`.** If you ever notice you're editing code while the item is still in `backlog`, you skipped this — stop and start it.
- **The moment the work is done and verified, run `tcw work complete <slug> …`.** Don't leave a shipped item sitting in `active`.

Keep status in step *as you go*; don't batch the transitions at the end. The per-command detail:

- **`tcw work new`** — declare the delta; for a product delta, record `Missing` capabilities (tcw-capabilities).
- **`tcw work start <slug>`** — when planning concludes and implementation begins, move the item to active. **This transition is the first implementation commit** (AGENTS.md) — commit the `start` move after the separate `plan.md` checkpoint and before the first code change. Add `--worktree` to isolate the item's code in its own git worktree + branch (transitions stay on the primary checkout; edits ride the work branch and merge back).
- **during `active`** — on any capability change, run contradiction-detection (tcw-capabilities).
- **`tcw work complete <slug> --resolution <done|wontfix|duplicate|superseded> --confirm`** — the final step. Reconcile capabilities first (the tcw-capabilities ledger flip): the DoD "capabilities reconciled" item is now **enforced**, not just acknowledged — `complete` **fails closed** if a capability the item declared in its `capabilities.yaml` `new:` list still reads `Missing`, or if any declared path doesn't resolve. Flip it (`tcw capabilities set <path> --status <S>`), mark it `Omitted` if you deliberately didn't build it, or `--force` past the gate with the reason in `outcome.md`. (`changed:` entries are only checked for resolution, not status.) After success, commit the completion status move and its related TCW work-file changes. `--force` also overrides unresolved blockers. For a `--worktree` item, `complete` **merges the work branch back** into the primary checkout before tearing it down (the caps gate runs **after** the merge, so a flip made on the work branch counts), and **fails closed** on a merge conflict (branch + worktree left intact, item stays `active`) — resolve the conflict and re-run rather than `--force`ing past it.

## Resume (across sessions)

`tcw work list --status active` → `tcw work show <slug>` → read the item's `initial-request.md` body plus whatever lifecycle artifacts exist (`spec.md`, `plan.md`, `outcome.md`, `refined-outcome.md`). For an epic, `tcw work reconcile <slug>` to refresh the rollup before choosing the next action.

## Sub-procedures (read on demand)

The core lifecycle above is self-sufficient. For these rarer situations, read the matching doc and follow it:

- **Planning, implementation, verification, and closeout across the SDLC** → [`references/lifecycle.md`](references/lifecycle.md)
- **Triaging a `docs/work/inbox/` doc** (raw request / `delegate`/`escalate` drop) → [`references/process-inbox.md`](references/process-inbox.md)
- **Splitting one item into nested pieces that transition together** (`--parent`) → [`references/decompose.md`](references/decompose.md)
- **Coordinating independently scheduled epic tasks** (`--initiative`, valid in the same node or across nodes) → [`references/epic-lifecycle.md`](references/epic-lifecycle.md); for delegation across separate sub-project repos, also read [`references/cross-node-epic.md`](references/cross-node-epic.md)

## Quick reference

| Goal | Command |
|---|---|
| plan a request/item | `/tcw-plan-work` or read [`references/lifecycle.md`](references/lifecycle.md) |
| drive remaining stages | `/tcw-drive-work-to-completion` or read [`references/lifecycle.md`](references/lifecycle.md) |
| triage an inbox entry | `tcw work inbox list` → `tcw work inbox show <entry>` → `tcw work inbox accept <entry> [--title <title>]` |
| split an item into coupled nested pieces | `tcw work new "<sub>" --parent <slug>` (child nests under it; parent transitions carry it; starting/completing it alone de-nests it) |
| add an independently scheduled task to an epic | `tcw work new "<task>" --initiative <epic-slug>` (same-node or cross-node; included by `reconcile`) |
| start work | `tcw work start <slug> [--worktree]` |
| finish work | `tcw work complete <slug> --resolution done --confirm` |
| see the board | `tcw work list [--status active]` (hides completed; `--all` to include; `-i` / `--incl-desc` / `--include-descendants` lists registered descendant boards grouped by project ID, with initiative children indented beneath visible epics; descendant items print `<project-id>/<slug>`; shows lifecycle stages and sorts by priority/topology) |
| address a descendant item | pass `<descendant-project-id>/<slug>` to any work command; only registered descendants resolve, while a bare slug remains local (`tcw serve` uses the same IDs) |
| audit backlog relevance | `tcw work audit-work-backlog` (read-only cleanup recommendations for stale, duplicate, broken, blocked, vague, or misplaced backlog items) |
| migrate external plans | `tcw work consolidate-plans [PATH ...] [--apply] [--delete]` (dry-run first; converts external planning docs into backlog items) |
| find item files | `tcw work path <slug>` |
| validate the node | `tcw validate [path]` (always validates the whole registered graph; `path` narrows YAML/link/component checks only) |
| reference another object in prose | `[text](tcw://W/<slug>)` locally; use `<project-id>/` only for a registered descendant (`W`) or explicit axis inheritance (`T`/`C`) |
| address by status path | any work command also accepts a `<status>/…/<slug>` locator (e.g. `active/my-item`); the status segment must match the item's real status, intermediate segments are ignored, and the slug stays the identity |
| set priority | `tcw work new "<t>" --priority N` · `tcw work edit <slug> --priority N` (higher int = higher; default unspecified) |
| set estimates | `tcw work new "<t>" --effort <l> --complexity <l>` · `tcw work edit <slug> --effort <l> --complexity <l>` (`<l>` = low\|medium\|high\|very-high, or L/M/H/VH shorthand; optional; shown in `show`, not `list`) |
| manage tags | `tcw work tags add\|rm\|list <tag>...` — the node's registered tag set, stored in `tcw-config.yaml` (`work.tags`); fail-closed vocabulary |
| tag an item | `tcw work new "<t>" --tag <tag>` · `tcw work edit <slug> --tag <tag> --untag <tag>` (repeatable; each `--tag` must be registered or it's rejected) |
| filter by tag | `tcw work list --tag <tag>` (repeatable = match any); a tag later unregistered while still on an item is flagged by `tcw validate` |
| topology | `tcw work nodes` |
| epic rollup | `tcw work reconcile <epic-slug>` (`--complete-when-ready` auto-closes a fully-resolved epic) |
| close a done epic | when all children are resolved the epic shows `ready-to-close` in `list`/rollup and may `complete` **directly from backlog** — no throwaway `start` |
| hand work down / up | `tcw work delegate <child> "<t>"` · `tcw work escalate "<t>"` |
