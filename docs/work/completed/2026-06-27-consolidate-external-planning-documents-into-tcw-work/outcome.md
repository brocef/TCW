# Outcome — Consolidate external planning documents into TCW work

Work implemented and ready for verification.

## What changed

- Added `tcw work consolidate-plans [PATH ...]`.
- The command discovers likely Markdown planning documents outside `docs/work/`
  using conservative filename/heading cues.
- The default mode is read-only and prints candidate source paths and inferred
  titles.
- `--apply` creates backlog work items and writes lifecycle artifacts:
  `initial-request.md` always, and `spec.md`/`plan.md` when matching sections
  are obvious in the source document.
- `--delete` removes source documents only after successful migration.
- Updated README, release notes, changelog, `tcw-work` skill, and the capability
  ledger.

## Verification

- `pytest tests/test_work.py` — 65 passed.
- `tcw work consolidate-plans --help` — command help renders.
- `tcw work --help` — command appears in the work subcommand list.

## Deviations from plan

- Include/exclude pattern flags remain deferred; the initial implementation
  supports explicit files/folders and conservative built-in exclusions.

## Follow-up notes

- Candidate detection intentionally remains simple and dry-run-first. It should
  be broadened only in response to real migration misses.
