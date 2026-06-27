# Plan — Audit and prune the work backlog

## Phase 1 — Command shell and report model

- Add `audit-work-backlog` to `tcw/work/cli.py` command registration and help.
- Implement a small internal report data shape with slug, recommendation,
  severity, reasons, evidence, and suggested action.
- Keep the command read-only in the first implementation.

## Phase 2 — Backlog item checks

- Reuse `FsWorkStore.board(status="backlog")` to preserve list ordering.
- Add checks for missing/empty lifecycle artifacts, vague or oversized items,
  blockers with no next action, and malformed `capabilities.yaml`.
- Add local-reference checks for paths mentioned in `content.md`,
  `initial-request.md`, `spec.md`, and `plan.md`.

## Phase 3 — Cross-item and cross-node checks

- Compare backlog items with other backlog items and completed items for likely
  duplicates or superseded work.
- Use existing node discovery helpers to identify candidate TCW nodes when an
  item appears misplaced.
- Keep movement as a recommendation; do not implement cross-node mutation in
  this item unless the implementation pass explicitly expands scope.

## Phase 4 — Tests

- Add focused tests for a clean backlog, an already-completed-looking item, a
  broken file reference, duplicate backlog entries, stale blockers, malformed
  `capabilities.yaml`, and wrong-node evidence.
- Include a test that asserts the command is read-only by comparing item files
  before and after audit.

## Documentation sync tasks

- Update `README.md` because the public CLI surface changes.
- Update `docs/release-notes/upcoming.md` with user-facing wording.
- Update `docs/changelogs/upcoming.md` with technical implementation notes and
  the commit range.
- Update `skills/tcw-work/SKILL.md` because backlog triage guidance changes.

## Verification

- `pytest`
- `tcw work --help`
- `tcw work audit-work-backlog --help`
- A temp-repo smoke test that produces at least one stale, one broken-reference,
  and one keep recommendation.
