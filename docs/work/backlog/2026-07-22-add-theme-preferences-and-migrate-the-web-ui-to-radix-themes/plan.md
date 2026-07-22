---
stages:
  - id: theme-foundation
    title: Theme foundation and settings
    depends_on: []
  - id: browsing-shell
    title: Hard conversion of the browsing shell
    depends_on: [theme-foundation]
  - id: editing-feedback
    title: Hard conversion of editing and feedback
    depends_on: [browsing-shell]
  - id: assets-docs-reconciliation
    title: Generated assets, documentation, and capability reconciliation
    depends_on: [editing-feedback]
---

# Implementation plan — Radix Themes and appearance preferences

## Capability changes

- `web/choose-a-theme` is already declared `Missing`, points to
  `Feature=local-web-app`, and is listed under `new:` for this work item.
- Keep it Missing through implementation and user visual verification. At the
  completion gate, set it to `Supported`, run capability validation, and only
  then run `tcw work complete` after explicit user approval.
- No taxonomy change is planned.

## Overview

Replace the client visual system in four strictly sequential stages. Each stage
has its own bounded document under `plan/`; read only the current stage after
this manifest, run its pre-stage checks, implement it, run its post-stage checks,
and commit that stage before moving to the next.

The implementation boundary remains closed while
`2026-07-21-upgrade-tcw-serve-to-fastify-and-react` is active. Once that item is
completed, run `tcw work start` and commit the transition before touching code.

## Stage ordering

1. `theme-foundation` establishes pinned packages, first-paint behavior,
   preference state, and the Settings interaction.
2. `browsing-shell` depends on the foundation and replaces all read/browse
   presentation while preserving behavioral structure.
3. `editing-feedback` depends on the converted shell and replaces all mutation,
   lifecycle, and feedback presentation, removing the legacy visual system.
4. `assets-docs-reconciliation` depends on the complete client migration and
   rebuilds distributable assets, synchronizes documentation, runs the full
   verification matrix, and records evidence.

The stages are deliberately sequential because each changes the same client
surface and CSS foundation. Focused tests within a stage may run in parallel,
but no later-stage source edit begins before the prior stage is verified and
committed.

## Documentation sync

The public user-facing theme behavior triggers `README.md` and
`docs/release-notes/upcoming.md`. Any code change triggers
`docs/changelogs/upcoming.md`, including the implementation hash range. Re-run
the Documentation Sync skill in the final stage. No driving-skill update is
expected because no CLI surface, lifecycle, installation requirement, or agent
workflow changes.

## Verification summary

Focused Vitest/component/Playwright checks bracket each stage. Final verification
runs `pnpm typecheck`, lint, Vitest, Playwright, deterministic build checking,
full pytest, capability/taxonomy/node validation, whitespace checking, a live
server smoke, and an isolated-wheel offline smoke. After `outcome.md` is
committed, stop for user visual verification and refinements; do not write
`refined-outcome.md`, flip the capability, complete the item, or cut a version
without explicit approval.
