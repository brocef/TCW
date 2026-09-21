---
name: work
description: Drives the `tcw work` change-tracking CLI — the Work axis of TCW (Taxonomy · Capabilities · Work). Use when planning, starting, implementing, verifying, or completing a tcw work item; resuming one across sessions; triaging a docs/work/inbox request; decomposing an item into child items; or coordinating a cross-node epic. Does not reimplement the CLI.
when_to_use: Use when starting, continuing, triaging, planning, implementing, verifying, or decomposing tcw work items — when a user asks to plan work, drive work to completion, process a docs/work/inbox request, start or complete an item, resume an active item across sessions, break a large item into child items (`tcw work new --parent`), or coordinate orchestrator-level work across sub-project nodes via a cross-node epic. Also when searching the board, auditing the backlog, or consolidating external planning documents.
allowed-tools: Bash(tcw *), Bash(git *), Read, Edit, Write
metadata:
    author: Brian Cefali
license: Apache-2.0
dynamic_skill: false # which skills a project may override, and why: ../README.md
---
**Version check.** Under Claude Code, skip this: the session-start hook already ran it. Under any other harness, once per session before your first `tcw` command, run `bash "<plugin>/scripts/check_versions.sh"`, where `<plugin>` is two folders above the folder holding this `SKILL.md`, and pass on anything it prints to the user.

# Driving `tcw work`

`tcw work` is the change-tracking state machine. This skill is the **judgment**
on top of it. Name `tcw …` commands; never hand-edit the store when a command
exists, and never compose store paths — see [`commands.md`](references/commands.md).

Work is the last layer in `Vocabulary → Features → Capabilities → Work`; an item
may change any earlier one. For a product delta, check those layers in order
first. **REQUIRED SUB-SKILL: Use the `capabilities` skill.**

## Two ladders

A **stage** produces one artifact. A **transition** moves status. Nothing is
both. Stage detection is artifact presence; status is the folder.

**To learn how to perform a stage, invoke the `work-stage` skill with the stage id and the work item — `work-stage <stage> [<slug>]`.**
It is where a stage's instructions come from, composed with this project's own.

| Stage        | Produces                                |
| ------------ | --------------------------------------- |
| `inbox`      | — (creates the item)                    |
| `request`    | `initial-request.md`                    |
| `spec`       | `spec.md`                               |
| `plan`       | `plan.md`                               |
| `implement`  | `outcome.md`                            |
| `verify`     | `refined-outcome.md` **or** `rework.md` |
| `postmortem` | `post-mortem.md`                        |

`start` · `submit` · `rework` · `complete` · `discard` → [`transitions.md`](references/transitions.md)

## Finding your place

Read the item — and if any `handoff-*.md` sits in its folder, an agent paused mid-task there: read them, newest last, let them place you, then delete what you read, because a stale one misleads the next reader. Then invoke `work-stage` for **only** the first missing artifact's stage:
no `initial-request.md` → `request` · no `spec.md` → `spec` · no `plan.md` →
`plan` · no `outcome.md` → `implement` · no `refined-outcome.md`/`rework.md` →
`verify`. Resume across sessions with `tcw work list --status active` →
`tcw work show <slug>`; for an epic, `tcw work reconcile <slug>` first.

## Always

- **Commit each stage artifact as you write it.** `[judgment]` — nothing enforces
  it. Never batch several stages into one commit. TCW commits the _transitions_
  itself; do not commit those by hand.
- **`tcw work stage gate <id> <slug>`** at every stage entry — it refuses; `work-stage` carries the instructions.
  Bindings → [`hooks.md`](references/hooks.md) · declaring them: the `configure` skill
- For a small change, ask whether to compress planning detail — but keep the item
  the durable source of truth and write whatever is needed to resume or review.

## Read on demand

- [`commands.md`](references/commands.md) — every command, storage/item paths, addressing, command skills, the documentation gate (`tcw work docs`), publication on a provisioned store
- [`delegation.md`](references/procedures/delegation.md) — dispatching stages to subagents · [`decompose.md`](references/procedures/decompose.md) — splitting one item into nested pieces
- Turning an idea into a work item without duplicating tracked work → the `work-create` skill
- [`tags.md`](references/tags.md) — the node's tag vocabulary · [`epic-deltas.md`](references/epic-deltas.md) — `type: epic` differences · [`cross-node-deltas.md`](references/cross-node-deltas.md) — work across registered nodes
- **Only when the user asks for it** — [`audit-backlog.md`](references/procedures/audit-backlog.md): reviewing the whole backlog for stale, duplicate, or misplaced items · [`consolidate-plans.md`](references/procedures/consolidate-plans.md): migrating planning documents from outside `docs/work/` into work items, then deleting the sources · [`search.md`](references/procedures/search.md): answering a described question about the board as a table

> **Web editing:** items, artifacts (Request/Spec/Plan as tabs), and the `capabilities.yaml`
> sidecar use the configured store through `tcw serve`; it commits transitions but runs **no** hooks.
