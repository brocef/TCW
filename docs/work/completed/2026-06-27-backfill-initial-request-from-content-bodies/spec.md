# Spec — Backfill initial-request from content bodies

## Capability changes

- **Changed:** `work#open-a-work-item` and lifecycle guidance should clarify
  that `content.md` is the always-present item body, while `initial-request.md`
  is the canonical lifecycle request artifact.

## Problem

`content.md` predates the formal lifecycle. Many older work items have useful
request context only in `content.md`, so the lifecycle stage display does not
show `R` and agents must remember to inspect a legacy body file.

## Proposed behavior

- For every existing work item folder under `docs/work/`, if `content.md` exists
  and `initial-request.md` does not, create `initial-request.md` by copying the
  nonempty `content.md` content.
- Do not overwrite existing `initial-request.md` files.
- Do not delete `content.md`; it remains the item body surface for now.
- Update lifecycle/docs wording to make the split explicit.

## Acceptance criteria

- Existing work items that only had `content.md` now have `initial-request.md`.
- Existing `initial-request.md` artifacts are unchanged.
- `tcw work list` shows `R` for migrated items.
- Docs explain `content.md` as body/overview and `initial-request.md` as the
  request lifecycle artifact.
