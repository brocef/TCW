Work completed successfully.

## What changed

- Added storage-neutral `PlanStage` metadata plus bounded read, write, delete,
  list, and locator operations to `WorkStore`.
- Added filesystem-backed staged-plan parsing, DAG and metadata validation,
  required-section checks, bounded `plan/<id>.md` discovery, atomic writes, and
  revision-safe deletion.
- Extended work-detail responses and authenticated API routes with declared
  plan-stage summaries and revision-aware CRUD/open behavior.
- Extended the React work detail to show metadata, dependencies, parallelizable
  peers, document presence, and create/edit/delete/open controls while retaining
  dirty-draft and 409 handling.
- Updated the work skill, task/epic lifecycle references, planning/drive prompts,
  README, public release notes, developer changelog, and both declared changed
  capability descriptions.

## Verification

- Complete Python test suite: passed.
- `pnpm typecheck`: passed.
- `pnpm lint`: passed.
- `pnpm test`: passed.
- `pnpm build` and `pnpm check:build`: passed.
- `pnpm test:e2e`: passed.
- `tcw capabilities check`: passed.
- `tcw taxonomy check`: passed.
- `tcw validate`: passed.
- `git diff --check`: passed.

Focused coverage includes legacy plans, valid serial/parallel DAGs, unsafe and
duplicate IDs, cycles and unknown dependencies, bounded stage discovery,
revision-safe CRUD, work-detail serialization, stale writes, and undeclared
stage rejection. Existing board and artifact behavior also ran through the full
regression suites.

## Deviations and notes

- The Fastify/React migration remained active, so the work item retains that
  blocker. Implementation used TCW's explicit force-start override and targeted
  the migrated server/client structure already present in the checkout.
- No automatic plan migration, stage execution status, taxonomy entry, or
  version bump was added.
- The changed capabilities have been reconciled by updating their supported
  descriptions; their statuses remain Supported.

## Follow-up

User verification and closeout choices remain required before completion, in
accordance with the task lifecycle.
