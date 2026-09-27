# Refined outcome: make a refused tcw work edit change nothing

## Decision

**Accepted** on 2026-09-26 in an unattended run (`extras-autonomous-work`), by
the coordinating session on the verifier's recommendation; no user present.

## Evidence

- Criteria 1-3, 5, 6: tests in `tests/test_edit_refusal.py` and the verifier's
  own hands-on runs, each followed by `git status --porcelain` showing nothing
  changed on a refusal.
- Criterion 4: as written it cannot fire (argument parsing refuses a bad
  `--effort` first, exit 2, writing nothing); the reverse-link case it guards is
  tested with an unregistered tag instead.
- Criterion 7: full suite 4494 passed, 3 skipped; 607 targeted by the verifier.

## Follow-ups

None filed; the review's findings were folded in.

## Closeout

- Route: `tcw work complete`, merging into `main` locally; not pushed.
- No capability ledger change. Version not cut.
