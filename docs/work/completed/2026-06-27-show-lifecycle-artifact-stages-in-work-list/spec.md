# Spec — Show lifecycle artifact stages in work list

## Capability changes

- **Changed:** `work#view-the-board` should describe the lifecycle artifact
  stage string instead of the usually-empty `phase` column.

## Problem

`tcw work list` shows a `phase` column, but most work items have no populated
phase, so the board commonly shows `-`. Agents and users cannot quickly see
whether a backlog item has request, spec, plan, or outcome artifacts without
opening the item folder.

## Goals

- Show completed lifecycle artifact stages directly in each `tcw work list` row.
- Keep the row compact and stable for terminal use.
- Treat empty artifact files as absent for display purposes.
- Preserve priority, title, blocker annotations, nesting, and sorting behavior.

## Non-goals

- Do not implement a full lifecycle state machine in this item.
- Do not add a new persistent item status.
- Do not infer semantic completion from document content beyond nonempty files.

## Current-state findings

- `tcw/work/cli.py` prints list rows in the local `emit()` function:
  `<slug> | <status> | <phase|-> | <priority|-> | <title>`.
- `WorkItem.phase` exists in `tcw/store/base.py`, but current backlog items
  typically store `phase: ''`, so the list prints `-`.
- `FsWorkStore.path(slug)` can resolve the current item folder, which contains
  lifecycle artifact files beside `content.md`.
- Existing lifecycle docs define the artifact spine:
  `initial-request.md -> spec.md -> plan.md -> outcome.md -> refined-outcome.md`.

## Proposed behavior

Replace the visible phase value in `tcw work list` with an artifact-stage string:

- `R` when `initial-request.md` exists and has non-whitespace content.
- `S` when `spec.md` exists and has non-whitespace content.
- `P` when `plan.md` exists and has non-whitespace content.
- `O` when `outcome.md` exists and has non-whitespace content.
- Consider `F` for `refined-outcome.md` if implementation wants full lifecycle
  coverage; otherwise defer it and document the chosen set clearly.
- Print `-` when none of the tracked lifecycle artifacts exist or are nonempty.

Example:

```
some-slug | backlog | RSP | 12 | Title of work item
```

The implementation can be filesystem-adapter aware because lifecycle artifacts
are bounded named attachments on a work item, which has an abstract analog. Avoid
introducing arbitrary path scanning into the core model.

## Acceptance criteria

- `tcw work list` prints the artifact-stage string in the third column.
- Existing rows with no artifacts still print `-` in that column.
- Nonempty artifact files contribute letters in lifecycle order.
- Empty or whitespace-only artifact files do not contribute letters.
- Nested child rows and blocker suffixes keep existing behavior.
- README, release notes, changelog, and `tcw-work` skill wording describe the
  new list output.

## Risks and dependencies

- Users or scripts may interpret the third column as phase. Update public docs
  and keep the delimiter/order otherwise stable.
- `phase` may still be useful in `tcw work show`; this change should not remove
  the stored field unless a later item scopes that cleanup.
