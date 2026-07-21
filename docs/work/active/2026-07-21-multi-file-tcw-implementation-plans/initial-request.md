# Multi-file TCW implementation plans

## Product changes

Allow complex work items to keep `plan.md` as a concise entry point while
declaring a bounded collection of stage documents. Users should be able to view,
create, edit, delete, and open those declared documents in the local web app,
and agents should selectively load only the stage they are implementing.

## Technical changes

- Add canonical YAML frontmatter to staged plans with required stage IDs,
  titles, and dependencies plus optional effort, complexity, priority, and
  registered tags.
- Validate the declaration as a DAG and validate its derived stage documents,
  without creating stage statuses or enforcing execution order.
- Add storage-neutral plan-stage metadata and bounded store operations; the
  filesystem adapter realizes each declared stage as `plan/<id>.md`.
- Extend the work-detail API and React editor with revision-aware stage
  summaries and authenticated CRUD/open routes.
- Preserve legacy single-file plans, the five-artifact lifecycle spine, and the
  board's existing `P` meaning.

## Meta changes

- Update the TCW work skill, task/epic lifecycle references, planning and drive
  prompt commands, README, release notes, changelog, and the two affected
  capability descriptions.
- Do not add taxonomy or migrate existing plans automatically.
- Keep stage ordering advisory. Informal progress may be written in plan or
  outcome prose but is never formal stage state.
- The active Fastify/React migration blocks this work because it overlaps the
  API and web surfaces.

