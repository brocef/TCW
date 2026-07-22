---
stages:
  - id: formatting-foundation
    title: Formatting foundation
    depends_on: []
  - id: modular-client-architecture
    title: Modular client architecture
    depends_on: [formatting-foundation]
  - id: tree-editor-experience
    title: Tree and editor experience
    depends_on: [modular-client-architecture]
  - id: assets-docs-verification
    title: Generated assets, documentation, and verification
    depends_on: [tree-editor-experience]
---

# Implementation plan — modular TCW web client

## Capability changes

- Record `web` and `web/editing` under `changed:`; both already exist and are
  Supported.
- No taxonomy changes are planned.
- Defer wording reconciliation until after user visual verification.

## Overview

Implement four sequential stages because they share the same client source and
build output. Read this manifest first, then only the current document in
`plan/`; run its pre- and post-stage checks and commit the stage before starting
the next one. Preserve all pre-existing unstaged Prettier/package/theme/bundle
changes through planning and the start transition.

## Stage ordering

1. `formatting-foundation` adopts the existing Prettier changes, bounds its
   surface, and isolates the initial mechanical formatting pass.
2. `modular-client-architecture` extracts focused components, state, utilities,
   styles, and tests while preserving behavior.
3. `tree-editor-experience` standardizes all axis rows and improves filter,
   toggle, status, and reference-result presentation.
4. `assets-docs-verification` rebuilds distributable assets, synchronizes
   triggered docs, runs the complete verification matrix, and records evidence.

## Documentation sync

The visible UI changes fire `README.md` and
`docs/release-notes/upcoming.md`; all behavior-affecting implementation fires
`docs/changelogs/upcoming.md`. No driving-skill update is expected because the
CLI, lifecycle, model, and agent workflow do not change. Re-evaluate these
triggers in the final stage.

## Completion boundary

Write and commit `outcome.md` with automated evidence, then stop for user visual
verification. Do not update capability wording, write `refined-outcome.md`, run
`tcw work complete`, or cut a release without explicit approval.
