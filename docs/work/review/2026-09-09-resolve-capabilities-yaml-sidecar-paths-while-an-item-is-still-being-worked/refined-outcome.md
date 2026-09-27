# Refined outcome: resolve capabilities.yaml sidecar paths while an item is still being worked

## Decision

**Accepted** on 2026-09-26 in an unattended run (`extras-autonomous-work`), by
the coordinating session on the verifier's recommendation; no user present.

## Evidence

- Criteria 1-6: `tests/test_sidecar_paths_in_validate.py` (11) and the gate
  tests, and the verifier's hands-on runs in every status, with line numbers
  checked against comments, longer paths and flow lists.
- Criterion 7: full suite 4516 passed, 3 skipped on the branch; after merging
  main (a hand-resolved conflict in `tcw/validate.py`), 4593 passed, 3 skipped
  on the merged code.

## Known limits

- A YAML syntax error anywhere in the node skips this check along with the
  component checks, until it is fixed.
- A multi-line flow list gets no line number; a path listed twice points to
  its first listing.

## Follow-ups

- Filed: `2026-09-26-decide-whether-a-capability-path-may-name-a-connected-project-by-an-unambiguous-shorthand`.

## Originating issue

GitHub #27 is **not** answered or closed yet. This repository's rule is that an
issue closes only after the fix is published — complete the items, cut the
version, push, then answer and close — so a reporter is never told it is fixed
before they can install it. Nothing is posted without the exact text being
approved first.

## Closeout

- Route: `tcw work complete`, merging into `main` locally; not pushed.
- Jira TCW-15 moves with the item through tracker sync.
- No capability ledger change. Version not cut.
