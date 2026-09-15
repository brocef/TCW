# Outcome — Audit and prune the work backlog

Work implemented and ready for user verification.

## What changed

- Added `tcw work audit-work-backlog`, a read-only backlog audit command.
- The command reports cleanup findings with recommendation, severity, reason,
  evidence, and suggested action.
- Covered the planned checks for likely duplicate/completed work, missing
  lifecycle artifacts, broken local references, stale blockers, malformed
  capability deltas, wrong-node candidates, and vague or under-specified items.
- Made malformed work-item `capabilities.yaml` load as an auditable finding
  instead of crashing work-item reads.
- Updated public CLI docs, release notes, changelog, the `tcw-work` skill, and
  the work capability ledger.

## Verification

- `pytest tests/test_work.py` — 60 passed.
- `pytest` — 210 passed.
- `tcw work audit-work-backlog --help` — command help renders.
- `tcw work audit-work-backlog` — reports findings for the current backlog and
  exits successfully.
- `tcw work --help` — command appears in the work subcommand list.
- `tcw capabilities check` — capabilities OK.

## Deviations from plan

- Wrong-node detection uses a bounded sentinel scan tailored for audit reporting
  rather than the heavier cross-node `child_nodes()` helper, because the live
  smoke test showed that the full helper can spend too long crawling symlinked
  plugin/cache trees for this read-only heuristic.
- JSON output remains deferred as planned.

## Follow-up notes

- The path-reference heuristic intentionally remains conservative and textual.
  It validates likely file references against the repo root and the work item
  folder, while ignoring TCW lifecycle artifact filenames.
