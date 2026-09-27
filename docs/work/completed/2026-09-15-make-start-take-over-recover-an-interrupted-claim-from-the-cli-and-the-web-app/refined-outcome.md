# Refined outcome: make start --take-over recover an interrupted claim from the CLI and the web app

## Decision

**Accepted** on 2026-09-26 in an unattended run (`extras-autonomous-work`), by
the coordinating session on the verifier's recommendation; no user present.

## Evidence

- Criteria 1-5: `tests/test_interrupted_claim.py` (16), and the verifier's
  hands-on runs: CLI take-over of a hand-made `.claiming/` folder, a refusing
  tag-matched `pre` hook leaving the claim in place, and the web list, recover
  and 422 refusal by curl.
- Criteria 6-7: full Python suite 4495 passed, 3 skipped on the final code.
  After merging main (which conflicted only in the built bundle and the
  changelogs), the client bundle was rebuilt from the merged source, and vitest
  74, tsc, Playwright 14 and the affected Python files (414) passed.

## Follow-ups

- Filed earlier: `2026-09-26-refuse-to-take-over-a-claim-that-may-still-be-in-flight`.

## Closeout

- Route: `tcw work complete`, merging into `main` locally; not pushed.
- Jira TCW-4 moves with the item through tracker sync.
- No capability ledger change. Version not cut.
