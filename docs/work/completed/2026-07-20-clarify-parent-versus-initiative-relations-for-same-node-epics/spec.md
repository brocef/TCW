# Spec — Clarify parent versus initiative relations

## Problem

The `tcw-work` guidance currently describes `--parent` as the same-node path and
`--initiative` as the cross-node path. Locality is not the decisive distinction.
A same-node epic whose tasks start and complete independently needs
`--initiative`; otherwise starting a nested child de-nests it and
`tcw work reconcile` does not include it in the epic rollup.

## Goals

- Define `--parent` by its coupled transition behavior: one large item split into
  nested pieces that normally move with the parent.
- Define `--initiative` by independent scheduling and epic rollup behavior,
  explicitly allowing same-node and cross-node tasks.
- Make the router, epic lifecycle, and decomposition reference agree.

## Non-goals

- No CLI, store-interface, model, or filesystem-adapter changes.
- No `tcw work edit --parent` option.
- No change to which relations `tcw work reconcile` follows.

## Acceptance criteria

- The epic lifecycle no longer routes relationships by node locality.
- The decomposition reference warns that `--parent` is inappropriate for
  independently scheduled epic tasks and points those tasks to `--initiative`.
- The `tcw-work` router exposes both same-node relation choices without implying
  that initiatives are cross-node-only.
- Existing Markdown links resolve and `tcw validate` passes.
