# Multi-file TCW implementation plans specification

## Capability changes

- Change `plugin/work-lifecycle` so agents can create optional staged plans,
  load `plan.md` first, and selectively load a relevant stage document.
- Change `web/editing` so users can view, create, edit, remove, and open
  documents declared by a staged plan.
- No taxonomy change is required; the existing work-item and local-web-app
  vocabulary covers the behavior.

## Problem

Large implementation plans are expensive to reload as a whole. TCW currently
has a bounded lifecycle artifact set, but `plan.md` is the only plan resource.
Users need an optional, bounded decomposition that remains storage-neutral and
does not turn stages into workflow statuses.

## Goals

- Keep `plan.md` as the canonical plan entry point and lifecycle artifact.
- Let it declare an ordered DAG of stage metadata in YAML frontmatter.
- Derive one bounded document resource per declaration.
- Validate declarations and documents while preserving drafts and legacy plans.
- Expose revision-aware stage CRUD and open operations through the web app.

## Non-goals

- Migrating or backfilling existing plans.
- Tracking formal per-stage execution status.
- Enforcing dependency order as a transition gate.
- Replacing nested work items or initiative tasks for independently owned work.

## Format

A staged `plan.md` uses canonical YAML frontmatter with a `stages` list. Every
entry requires `id`, `title`, and `depends_on`. IDs are lowercase kebab case,
unique, safe resource identifiers. Dependencies must reference declared IDs and
form an acyclic graph. Optional `effort` and `complexity` use TCW's existing
levels; `priority` is an integer; `tags` is a list of registered work tags.

List order is stable presentation order. Dependencies provide ordering guidance
and allow the UI to group stages whose identical prerequisites are satisfied.
Each declaration maps to a resource named by its ID; the filesystem adapter
stores that resource at `plan/<id>.md` without exposing that path in the model.

The Markdown body of `plan.md` contains non-empty `Overview` and `Stage
ordering` sections. Each stage document contains non-empty `Objective`,
`Pre-stage checks`, `Implementation`, and `Post-stage checks` sections. A plan
without a `stages` key remains a valid legacy plan.

## Store and validation behavior

Add storage-neutral `PlanStage` metadata and `WorkStore` methods to list the
declared stages, read/write/delete a declared stage resource, and obtain an
openable stage locator. Discovery is bounded by the manifest, not directory
globbing at callers. The filesystem adapter may inspect `plan/*.md` privately to
report undeclared resources.

Validation reports malformed frontmatter, unsafe or duplicate IDs, invalid
metadata, unknown/self dependencies, cycles, stale tags, missing or empty stage
documents, missing/empty required headings, and undeclared stage files.

## API and web behavior

Work-detail responses include ordered stage summaries, dependency metadata,
document presence, and revision tokens. Authenticated resource-oriented routes
read, replace, delete, and open an individual declared stage. They reject
unknown IDs and traversal attempts, preserve stale-write behavior, and return
validation warnings without discarding a saved draft.

The React detail view displays stage metadata, dependencies, parallel-ready
groups, and document presence. Each stage has individual edit, delete, and open
controls. Dirty navigation and 409 recovery match existing artifact editing.

## Lifecycle compatibility

The five-artifact lifecycle spine is unchanged. `P` still means `plan.md`
exists. For a staged plan, `plan.md` and all declared stage documents form one
plan checkpoint commit. Consolidation and existing artifact editing continue to
accept legacy single-file plans.

## Dependencies and risks

The active Fastify/React migration overlaps the API and UI files and is recorded
as a blocker. The implementation must target the post-migration architecture or
wait until that work item is reconciled. YAML parsing must remain safe, and all
stage identifiers must be validated before any filesystem path is derived.

## Acceptance criteria

- Legacy and staged plans both validate according to their own format.
- Serial and parallel DAGs are represented deterministically; cycles and invalid
  declarations fail validation.
- Store operations work through the abstract interface and a non-filesystem test
  double, with revision-safe filesystem behavior.
- API and UI users can inspect and manage only declared stage resources.
- Existing lifecycle, board, consolidation, and artifact-editor behavior remains
  unchanged.
