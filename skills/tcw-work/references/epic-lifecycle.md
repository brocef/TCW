# Epic lifecycle

Use this lifecycle for work items with `type: epic`. An epic is a coordination item, not a directly implemented code task. Child tasks do the implementation and point back with `initiative: <epic-slug>`.

The artifact spine is:

`initial-request.md` -> `spec.md` -> `plan.md` -> `outcome.md` -> `refined-outcome.md`

For epics, the artifacts mean:

- `initial-request.md`: initiative request and coordination goal.
- `spec.md`: overview spec, affected nodes, product/capability scope, ordering constraints.
- `plan.md`: delegation and coordination plan, including child tasks and dependencies.
- `outcome.md`: aggregate status from reconciled child tasks.
- `refined-outcome.md`: aggregate verification, closeout decisions, and deferred follow-ups.

Each new or materially updated artifact is a stage checkpoint: commit it and
only its related TCW work-file changes before moving to the next stage. Do not
batch several epic artifacts into one commit or create empty commits for stages
that were already complete.

## Planning

During request ingestion and request processing, identify the affected nodes and
choose the child relation by scheduling semantics, not node locality:

- Use `tcw work new "<piece>" --parent <item-slug>` when decomposing one item
  into nested pieces that are worked together and transition with the parent.
  Starting or completing one nested child independently promotes it to a
  top-level item, so this relation is not the right shape for independently
  scheduled epic tasks.
- Use `tcw work new "<task>" --initiative <epic-slug>` for epic tasks that start
  and complete independently over time. This is valid in the same node or across
  registered nodes, and `tcw work reconcile` follows the `initiative` relation.
  For a task in another node, delegate it with
  `tcw work delegate <child> "<task>" --initiative <epic-slug>`.

For product work, coordinate product-layer capability wording through the
tcw-capabilities process.

After capturing the initiative request, commit `initial-request.md` and its
related item metadata before writing the overview spec.

Write `spec.md` as an overview spec. It should describe the initiative, affected nodes, expected child tasks, capability changes, dependencies, risks, and acceptance criteria for the overall initiative.

Commit `spec.md` and its related TCW work-file changes before writing the
coordination plan.

Write `plan.md` as a coordination plan. It should list child tasks, delegation commands, dependency order, possible parallelism, rollup checkpoints, verification expectations, and documentation-sync expectations.

Commit `plan.md` and its related TCW work-file changes before starting the epic.

## Coordination

Start the epic before child tasks begin implementation:

```
tcw work start <epic-slug>
```

Commit the start status move separately before child implementation begins.

Then delegate or create initiative children, locally or across registered nodes.
Initiative child tasks cannot start until the related epic is active. Run:

```
tcw work reconcile <epic-slug>
```

before choosing the next coordination action, after child task status changes, and before closeout. Reconcile is the epic's live view of related child work.

The epic implementation stage is coordination: dispatch child work, monitor blockers, reconcile rollups, answer escalations, and adjust the coordination plan. Do not use the epic work item as the place to implement child-node code changes.

Write `outcome.md` with aggregate progress:

- child tasks completed, deferred, or blocked;
- verification evidence reported by children;
- capability or product-layer reconciliation performed;
- natural-language follow-up notes.

Commit `outcome.md` and any stage-related reconcile changes before aggregate
verification/refinement. Keep unrelated child-node or working-tree changes out
of this checkpoint.

## Verification and closeout

Stop for user verification after child work is reconciled. Write `refined-outcome.md` with the user's aggregate verification decision, remaining deferred work, and closeout choices.

Commit `refined-outcome.md` and its related TCW work-file changes before the
completion transition.

An epic cannot complete while initiative child tasks are still open. Complete or explicitly defer child tasks first, then run a final reconcile. Before `tcw work complete`, reconcile capabilities for product-layer changes and evaluate Documentation Sync triggers. After completion succeeds, commit the completion status move and related TCW work-file changes as the final lifecycle checkpoint.
