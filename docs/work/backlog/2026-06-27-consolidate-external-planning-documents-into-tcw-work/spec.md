# Spec — Consolidate external planning documents into TCW work

## Capability changes

- **New:** `work/consolidate-plans#consolidate-external-plans-into-tcw-work`
  remains `Missing` until this item lands.

## Problem

TCW work items are the durable planning source, but projects can accumulate
older planning documents outside `docs/work/`. Those documents become invisible
to `tcw work list`, cannot move through the lifecycle, and may continue to
compete with TCW as an unofficial backlog.

## Goals

- Provide a command to discover likely external planning documents.
- Convert each selected document into a TCW work item with lifecycle artifacts.
- Preserve a clear source-to-work-item mapping in command output.
- Allow safe cleanup of old documents after successful migration.

## Non-goals

- Do not build a general document classifier or semantic deduplication engine in
  the first pass.
- Do not add a new abstract `WorkStore` method for arbitrary filesystem search.
- Do not automatically rewrite links across the repo unless a later plan scopes
  that explicitly.

## Current-state findings

- `tcw/work/cli.py` owns work subcommands through `SUBCOMMANDS` and
  `add_subparser`; list/show/path/start/edit/complete/drop already use
  `FsWorkStore`.
- `FsWorkStore.create()` already creates a backlog item with `content.md` and
  `state.yaml`.
- Lifecycle artifacts are normal named files beside `content.md`:
  `initial-request.md`, `spec.md`, `plan.md`, `outcome.md`, and
  `refined-outcome.md`.
- The abstraction litmus test suggests arbitrary folder scanning should live in
  CLI/filesystem helper code, while item creation stays behind `WorkStore`.

## Proposed behavior

Add `tcw work consolidate-plans [PATH ...]` with a conservative first-pass
workflow:

- Resolve search roots from positional paths, or use a small project-local
  default set when none are supplied.
- Exclude `docs/work/`, `.git/`, virtualenv/cache folders, and generated output.
- Identify candidate Markdown planning documents using filename and heading cues
  such as `plan`, `spec`, `proposal`, `roadmap`, `todo`, or `followup`.
- Print candidates in a stable order and support a dry-run default.
- With an apply flag, create one backlog work item per accepted document.
- Write `initial-request.md` from the source document and inferred provenance.
- If the source document already has obvious spec/plan sections, copy them into
  `spec.md` and `plan.md`; otherwise keep the original content in
  `initial-request.md` and leave later lifecycle stages for normal planning.
- Print `source path -> work slug` for every migration.
- With an explicit cleanup flag, delete source documents only after all requested
  migrations have succeeded.

Suggested flags:

- `--apply` to create work items; without it, show the migration plan.
- `--delete` to remove imported source documents after successful creation.
- `--include PATTERN` and `--exclude PATTERN` only if the default candidate set
  proves too narrow during implementation.

## Acceptance criteria

- `tcw work consolidate-plans` appears in help and command dispatch.
- Passing one or more folders limits discovery to those folders.
- The command never imports documents already under `docs/work/`.
- Dry-run output is deterministic and does not write files.
- Apply mode creates backlog items with durable lifecycle artifacts.
- Delete mode removes source files only after successful item creation.
- Failures report which source document failed and leave already-created work
  items discoverable.

## Risks and dependencies

- Candidate detection can be noisy; keep the first implementation conservative
  and dry-run-first.
- Deletion is destructive; require an explicit flag and consider a confirmation
  flag if the UX would otherwise be surprising.
- Existing `FsWorkStore.create()` stages files with `git add`; tests should use
  temp git repos and account for that behavior.
