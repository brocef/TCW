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

`tcw work` is the change-tracking state machine. This skill is the **judgment**
on top of it. Name `tcw …` commands; never hand-edit the store when a command
exists, and never compose store paths — see [`commands.md`](references/commands.md).

Work is the last layer in `Vocabulary → Features → Capabilities → Work`; an item
may change any earlier one. For a product delta, check those layers in order
first. **REQUIRED SUB-SKILL: Use tcw-capabilities.** `tcw-plugin` maps the
skills.

## Two ladders

A **stage** produces one artifact. A **transition** moves status. Nothing is
both. Stage detection is artifact presence; status is the folder.

| Stage        | Produces                                | Document                                                          |
| ------------ | --------------------------------------- | ----------------------------------------------------------------- |
| `inbox`      | — (creates the item)                    | [`stage-inbox.md`](references/lifecycle/stage-inbox.md)           |
| `request`    | `initial-request.md`                    | [`stage-request.md`](references/lifecycle/stage-request.md)       |
| `spec`       | `spec.md`                               | [`stage-spec.md`](references/lifecycle/stage-spec.md)             |
| `plan`       | `plan.md`                               | [`stage-plan.md`](references/lifecycle/stage-plan.md)             |
| `implement`  | `outcome.md`                            | [`stage-implement.md`](references/lifecycle/stage-implement.md)   |
| `verify`     | `refined-outcome.md` **or** `rework.md` | [`stage-verify.md`](references/lifecycle/stage-verify.md)         |
| `postmortem` | `post-mortem.md`                        | [`stage-postmortem.md`](references/lifecycle/stage-postmortem.md) |

`start` · `submit` · `rework` · `complete` · `discard` →
[`transitions.md`](references/transitions.md)

## Finding your place

Read the item, then load **only** the document for the first missing artifact:
no `initial-request.md` → `request` · no `spec.md` → `spec` · no `plan.md` →
`plan` · no `outcome.md` → `implement` · no `refined-outcome.md`/`rework.md` →
`verify`. Resume across sessions with `tcw work list --status active` →
`tcw work show <slug>`; for an epic, `tcw work reconcile <slug>` first.

## Always

- **Commit each stage artifact as you write it.** `[judgment]` — nothing enforces
  it. Never batch several stages into one commit. TCW commits the _transitions_
  itself; do not commit those by hand.
- **Run `tcw work stage <id> <slug>`** at every stage entry — it carries the
  methodology, the stage document only what the CLI cannot. Bindings →
  [`hooks.md`](references/hooks.md) · defaults → [`lifecycle/default/`](references/lifecycle/default/README.md)
- For a small change, ask whether to compress planning detail — but keep the item
  the durable source of truth and write whatever is needed to resume or review.

## Read on demand

- [`commands.md`](references/commands.md) — every command, storage/item paths, addressing, slash commands, the documentation gate (`tcw work docs`), publication on a provisioned store
- [`delegation.md`](references/procedures/delegation.md) — dispatching stages to subagents · [`decompose.md`](references/procedures/decompose.md) — splitting one item into nested pieces
- [`tags.md`](references/tags.md) — the node's tag vocabulary
- [`epic-deltas.md`](references/epic-deltas.md) — `type: epic` differences
- [`cross-node-deltas.md`](references/cross-node-deltas.md) — work across registered nodes
- **Only when the user asks for it** — [`audit-backlog.md`](references/procedures/audit-backlog.md): reviewing the whole backlog for stale, duplicate, or misplaced items · [`consolidate-plans.md`](references/procedures/consolidate-plans.md): migrating planning documents from outside `docs/work/` into work items, then deleting the sources

> **Web editing:** items, artifacts (Request/Spec/Plan as tabs), and the `capabilities.yaml`
> sidecar use the configured store through `tcw serve`; it commits transitions but runs **no** hooks.
