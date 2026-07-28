# Epics — deltas only

An **epic** (`type: epic`) is a coordination item. It implements nothing itself;
child tasks do the work and point back with `initiative: <epic-slug>`.

Everything in the stage documents applies unchanged. Only these differ — and this
file stays a delta list on purpose, because the two full lifecycle documents it
replaces were ~85% identical and had already drifted apart.

## What the artifacts mean

| Artifact | For an epic |
|---|---|
| `initial-request.md` | The initiative request and coordination goal. Also the managed target for `reconcile`'s rollup. |
| `spec.md` | An overview spec: affected nodes, child boundaries, ordering constraints, acceptance criteria for the whole initiative. Implementation detail belongs in each child's own spec. |
| `plan.md` | A coordination plan: child tasks, delegation commands, dependency order, rollup checkpoints. |
| `outcome.md` | Aggregate status reconciled from the children. |
| `refined-outcome.md` | Aggregate verification and closeout decisions. |

## Choosing the child relation

By **scheduling semantics**, not by node locality:

- `tcw work new "<task>" --initiative <epic-slug>` for tasks that start and
  complete independently over time. Valid in the same node or across registered
  nodes; `reconcile` follows this relation. Cross-node:
  `tcw work delegate <child> "<task>" --initiative <epic-slug>`.
- `tcw work new "<piece>" --parent <slug>` for nested pieces worked together that
  transition with the parent. Starting or completing one independently promotes
  it to top level, so it is the wrong shape for scheduled epic tasks. See
  `decompose.md`.

## Ordering is a blocker, not a sentence

`--initiative` carries no dependency relation, so children with a required order
all read as workable at once. Record the order with
`tcw work edit <slug> --blocked-by <ref>`: `start` then refuses past it `[gated]`
and `reconcile`'s **Next** names only what is actually ready.

Do not chain children that are genuinely parallel. A false blocker is a lie the
tool will enforce.

## Coordination replaces implement

`tcw work start <epic-slug>` before any child begins — an initiative child cannot
start until its epic is active. `[gated]`

Then `tcw work reconcile <epic-slug>` before each coordination decision, after
any child status change, and before closeout. That is the epic's live view.

The epic's `implement` stage **is** coordination: dispatch, monitor blockers,
reconcile, answer escalations, adjust the plan. Never use the epic item as the
place to make a child's code changes.

## Closeout

An epic cannot complete while any initiative child is open. `[gated]` Complete or
explicitly defer them, then reconcile a final time.

Once every child is resolved the epic may complete **directly from `backlog`** —
a coordinator epic never needed its own `start`. `tcw work reconcile <epic>
--complete-when-ready` auto-closes a ready epic; all gates still run.
