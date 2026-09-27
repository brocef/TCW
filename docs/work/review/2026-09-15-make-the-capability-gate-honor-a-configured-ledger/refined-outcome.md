# Refined outcome: keep one bad capabilities.yaml from breaking the board

## Decision

**Accepted** on 2026-09-26 in an unattended run (`extras-autonomous-work`), by
the coordinating session on the verifier's recommendation; no user present.

## Evidence

- Part 1 of the request: already fixed on main (`61a298b9`), confirmed by the
  verifier with its test.
- Criteria 1-6: `tests/test_unreadable_capabilities_sidecar.py` (19, including
  the `validate` cases) and the verifier's hands-on runs of every bad-file kind
  through the board, the projection, the gate and the web app.
- Criterion 7: full suite 4552 passed, 3 skipped on the branch; 4622 passed,
  3 skipped after merging main and folding in the `validate` fix; the last
  commit (two read guards in `validate.py`) passed its files (67).

## Follow-ups

- Filed: `2026-09-26-keep-one-unreadable-state-yaml-or-artifact-from-breaking-the-board-or-an-item-s-detail`
  (with the web-save question added to it).

## Closeout

- Route: `tcw work complete`, merging into `main` locally; not pushed.
- Jira TCW-11 moves with the item through tracker sync.
- No capability ledger change. Version not cut.
