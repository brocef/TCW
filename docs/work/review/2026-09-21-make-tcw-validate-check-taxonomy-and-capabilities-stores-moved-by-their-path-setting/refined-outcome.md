# Refined outcome: make tcw validate check taxonomy and capabilities stores moved by their path setting

## Decision

**Accepted** on 2026-09-26 in an unattended run (`extras-autonomous-work`), by
the coordinating session on the verifier's recommendation; no user present.

## Evidence

- Criteria 1-8: `tests/test_validate_moved_stores.py` and the existing validate
  tests (147 passed for the verifier), and its hands-on runs in scratch nodes,
  each compared with main's build.
- Criterion 9: full suite 4495 passed, 3 skipped on the final code; after
  merging main, the affected files passed again (345).

## Behavior change to know about

`tcw capabilities check` now reports "Subject and Feature not checked: …" and
exits 1 when a capability names a Subject or Feature and the configured
taxonomy cannot be opened, where it used to print OK.

## Follow-ups

- None new. `2026-09-26-make-tcw-init-honor-a-configured-taxonomy-or-capabilities-path`
  (filed earlier) is the related gap in `init`.

## Closeout

- Route: `tcw work complete`, merging into `main` locally; not pushed.
- No capability ledger change. Version not cut.
