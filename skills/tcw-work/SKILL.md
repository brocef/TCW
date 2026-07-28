# Driving `tcw work`

`tcw work` is the change-tracking state machine. This skill is the **judgment**
on top of it. Name `tcw …` commands; never hand-edit `docs/work/` when a command
exists.

Work is the last layer in `Vocabulary → Features → Capabilities → Work`; an item
may change any earlier one. For a product delta, check those layers in order
first. **REQUIRED SUB-SKILL: Use tcw-capabilities.** `tcw-plugin` maps the
skills.

## Two ladders

A **stage** produces one artifact. A **transition** moves status. Nothing is
both. Stage detection is artifact presence; status is the folder.

| Stage | Produces | Runs in | Document |
|---|---|---|---|
| `inbox` | — (creates the item) | pre-item | [`stage-inbox.md`](references/stage-inbox.md) |
| `request` | `initial-request.md` | backlog | [`stage-request.md`](references/stage-request.md) |
| `spec` | `spec.md` | backlog | [`stage-spec.md`](references/stage-spec.md) |
| `plan` | `plan.md` | backlog | [`stage-plan.md`](references/stage-plan.md) |
| `implement` | `outcome.md` | active | [`stage-implement.md`](references/stage-implement.md) |
| `verify` | `refined-outcome.md` **or** `rework.md` | review | [`stage-verify.md`](references/stage-verify.md) |
| `postmortem` | `post-mortem.md` | review, or after completed | [`stage-postmortem.md`](references/stage-postmortem.md) |

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
  it. Never batch several stages into one commit. TCW commits the *transitions*
  itself; do not commit those by hand.
- **Run `tcw work lifecycle --stage <id>`** before a stage and honor any binding
  it reports → [`hooks.md`](references/hooks.md)
- For a small change, ask whether to compress planning detail — but keep the item
  the durable source of truth and write whatever is needed to resume or review.

## Read on demand

- [`commands.md`](references/commands.md) — every command, addressing, slash commands
- [`delegation.md`](references/delegation.md) — dispatching stages to subagents
- [`tags.md`](references/tags.md) — the node's tag vocabulary
- [`epic-deltas.md`](references/epic-deltas.md) — `type: epic` differences
- [`cross-node-deltas.md`](references/cross-node-deltas.md) — work across registered nodes
- [`decompose.md`](references/decompose.md) — splitting one item into nested pieces

> **Web editing:** items, artifacts, and the `capabilities.yaml` sidecar can also
> be edited through `tcw serve`. It commits transitions but runs **no** hooks.
