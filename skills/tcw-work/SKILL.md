---
name: tcw-work
description: Use when starting, continuing, triaging, or decomposing tcw work items — when you face a docs/work/inbox to process, are planning a change, need to start or complete an item, are resuming an active item across sessions, want to break a large item into child items (`tcw work new --parent`) so no item is too large, or are coordinating orchestrator-level work across sub-project nodes via a cross-node epic. Drives the `tcw work` CLI; does not reimplement it.
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

Fill the item's `content.md` under `## Product changes` / `## Technical changes` / `## Meta changes` — which sections are non-empty *is* the classification. **Product-first:** if there is any product delta, run the tcw-capabilities planning gate *before* writing the technical plan.

**Write the spec and the implementation plan to files *inside the work-item folder* — `spec.md` and `plan.md`, beside `content.md`.** This is required (AGENTS.md): planning artifacts live with the item they plan, never in a scratch or separate-tree location, so they travel through the lifecycle with it and freeze in `completed/`. Don't write the spec/plan to `docs/superpowers/` or elsewhere — put them in the item folder.

## The lifecycle handshake

- **`tcw work new`** — declare the delta; for a product delta, record `Missing` capabilities (tcw-capabilities).
- **`tcw work start <slug>`** — when planning concludes and implementation begins, move the item to active. **This transition is the first implementation commit** (AGENTS.md) — commit the `start` move (with the committed `spec.md`/`plan.md`) before the first code change. Add `--worktree` to isolate the item's code in its own git worktree + branch (transitions stay on the primary checkout; edits ride the work branch and merge back).
- **during `active`** — on any capability change, run contradiction-detection (tcw-capabilities).
- **`tcw work complete <slug> --resolution <done|wontfix|duplicate|superseded> --confirm`** — the final step. Reconcile capabilities first (the tcw-capabilities ledger flip), since the DoD "capabilities reconciled" item is acknowledged here. `--force` overrides unresolved blockers.

## Resume (across sessions)

`tcw work list --status active` → `tcw work show <slug>` → read the item's `content.md` / `spec.md` / `plan.md`. For an epic, `tcw work reconcile <slug>` to refresh the rollup before choosing the next action.

## Keep items small: decompose into child items

**No single work item should be too large.** When planning reveals an item is
big — it would touch many subsystems, span several sessions, or bundle loosely
related concerns — break it into **child items nested under it**, and whenever
the user asks you to split an item, do so the same way. This is the *intra-node*
decomposition path: one item, one repo, broken into smaller pieces that travel
with the parent.

```
tcw work new "<sub-item title>" --parent <parent-slug>
```

- The child's folder is created **inside** the parent's folder; `tcw work list`
  shows children indented under their parent.
- A child inherits the parent's status by living inside it. `tcw work start`/
  `complete` on the **parent** carries its children along; transitioning a
  **child** on its own promotes it to a top-level item (it de-nests).
- Decompose at *planning* time (in the parent's `plan.md`, list the children you
  intend to spin off), then create them. Each child gets its own
  `content.md`/`spec.md`/`plan.md` as it's planned — the parent stays a thin
  umbrella.

Reach for this **before** an item grows unwieldy. A parent with three focused
children beats one item whose `plan.md` has fifteen tasks.

## Orchestrator-level work: coordinate across sub-projects

When work spans **separate sub-project repos** (child *nodes* — see
`tcw work nodes`), the unit of coordination is a **cross-node epic** at the
orchestrator node, not a nested child. Use this path when the slices live in
different repos and progress independently; use `--parent` children when the
whole thing lives in one repo.

1. **Open the epic** at the orchestrator node:
   `tcw work new --epic "<epic title>"` → note its slug.
2. **Hand each slice down** to the owning sub-project:
   `tcw work delegate <child-node> "<slice title>" --initiative <epic-slug>` —
   this drops a request (with `from:`/`initiative:` front-matter) into that
   child node's `inbox/`. The orchestrator never writes into a child's tracking
   tree directly; the child agent runs process-inbox and
   `tcw work new --initiative <epic-slug>` to adopt the slice.
3. **Each sub-project works its slice independently**, linking its own
   capabilities. Product-layer wording is coordinated over the inbox channel
   (`tcw work escalate "capability wording: …"`) — **non-blocking**; never wait
   on a reply (tcw-capabilities).
4. **A sub-project escalates up** when it needs the orchestrator:
   `tcw work escalate "<title>"` writes into the parent node's `inbox/`.
5. **Roll up progress** from the orchestrator:
   `tcw work reconcile <epic-slug>` scans every node for
   `initiative == <epic-slug>` and writes a consolidated table (node, slug,
   status, blockers, next-ready) into the epic's `content.md`. Re-run it to
   refresh before deciding the next move.

**Which path?** Same repo, one big item → `--parent` children. Multiple
sub-project repos → an `--epic` + `delegate`/`--initiative`/`reconcile`.

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
