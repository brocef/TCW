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

## Planning

During request ingestion and request processing, identify the affected nodes and whether the work belongs in same-node child items (`tcw work new --parent`) or cross-node initiative children (`tcw work delegate <child> ... --initiative <epic-slug>`). For product work, coordinate product-layer capability wording through the tcw-capabilities process.

Write `spec.md` as an overview spec. It should describe the initiative, affected nodes, expected child tasks, capability changes, dependencies, risks, and acceptance criteria for the overall initiative.

Write `plan.md` as a coordination plan. It should list child tasks, delegation commands, dependency order, possible parallelism, rollup checkpoints, verification expectations, and documentation-sync expectations.

## Coordination

Start the epic before child tasks begin implementation:

```
tcw work start <epic-slug>
```

Then delegate or create children. Initiative child tasks cannot start until the related epic is active. Run:

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

## Verification and closeout

Stop for user verification after child work is reconciled. Write `refined-outcome.md` with the user's aggregate verification decision, remaining deferred work, and closeout choices.

An epic cannot complete while initiative child tasks are still open. Complete or explicitly defer child tasks first, then run a final reconcile. Before `tcw work complete`, reconcile capabilities for product-layer changes and evaluate Documentation Sync triggers.
