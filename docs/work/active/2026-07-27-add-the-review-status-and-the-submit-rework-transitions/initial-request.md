# Add the review status and the submit/rework transitions

Epic: [Redefine the TCW work lifecycle](tcw://W/2026-07-27-redefine-the-tcw-work-lifecycle-explicit-stages-transitions-and-hooks)

Child 1 of 5. The epic's `spec.md` and `plan.md` are the authority; this file
records the slice. **Runs first** — later children document what this ships.

## Scope

Owns the state machine only. Nothing about config, commits, or hooks.

- `WORK_STATUSES` gains `review`. `RESOLVED_STATUSES` unchanged, so an item in
  `review` still blocks its dependents.
- `LEGAL_TRANSITIONS` gains `(active, review)`, `(review, completed)`,
  `(review, active)`, `(review, discarded)`.
- `WorkStore.submit()` and `.rework()` beside `start()` / `complete()`.
- `tcw work submit <slug>`. `tcw work rework <slug>`, which **fails closed while
  `refined-outcome.md` is present** — TCW never deletes it for the agent.
- `complete` accepts `review` as a source, and warns on the `active` route that
  the `verify` stage was skipped (stderr only, not a second confirmation).
- `WORK_ARTIFACTS` gains `post-mortem` and `rework`. Names only — child 4 owns
  what those files must contain. The set stays bounded.
- Add the `pr` field. **Delete `phase`**: the model field, its `state.yaml` key,
  the `show` line (`work/cli.py:97`), and the reconcile column
  (`work/recursion.py:134`). It has never been written by any code path.
- `web/client/src/model/types.ts` and the precedence map in `tree.ts`.
- Lazy `review/` creation for nodes predating the status.

## Done when

- An item traverses `active → review → active → review → completed`.
- `rework` refuses while `refined-outcome.md` exists.
- `complete` still works from `active`, with the warning.
- A node with no `review/` folder does not crash.
- `phase` appears nowhere, and a pre-existing `state.yaml` still carrying it
  loads without error and drops it on the next write.
- **The Python↔TypeScript status parity test exists and fails when the two sets
  diverge.** A named deliverable, not a by-product — it is the one guard missing
  today, and adding a status is exactly when its absence bites.

## Notes

`RESERVED_PROJECT_IDS` derives from `WORK_STATUSES`, so `review` becomes a
reserved project id. A node already using that id needs an actionable error.
