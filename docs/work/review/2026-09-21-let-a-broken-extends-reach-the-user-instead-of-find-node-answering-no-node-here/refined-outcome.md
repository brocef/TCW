# Refined outcome: let a broken extends reach the user instead of find_node answering no node here

## Decision

**Accepted** on 2026-09-26 in an unattended run (`extras-autonomous-work`), by
the coordinating session on the verifier's recommendation; no user present.

## Evidence

- Criteria 1-4: tests in `tests/test_store_provisioning.py` and
  `tests/test_legacy_store_config.py` (217 passed for the verifier), and the
  verifier's hands-on runs showing each real message and the unchanged "no
  node here" cases.
- Criterion 5: full suite 4481 passed, 3 skipped; the one test added after it
  passed on its own.

## Follow-ups

- Filed: `2026-09-26-make-tcw-init-honor-a-configured-taxonomy-or-capabilities-path`.

## Closeout

- Route: `tcw work complete`, merging into `main` locally; not pushed.
- No capability ledger change. Version not cut.
