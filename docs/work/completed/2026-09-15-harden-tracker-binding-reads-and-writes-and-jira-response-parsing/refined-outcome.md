# Refined outcome: harden tracker binding reads and writes, and Jira response parsing

## Decision

**Accepted** on 2026-09-27 in an unattended run (`extras-autonomous-work`), by
the coordinating session on the verifier's recommendation; no user present.

## Evidence

- Criteria 1-4: `tests/test_tracker_hardening.py`, two tests in
  `tests/test_tracker_cli.py`, and the verifier's hands-on runs of each.
- Criterion 5: full suite 4631 passed, 3 skipped on `7cd96323`; the one later
  code commit changed a message and its files passed (125). After merging main
  (a hand-resolved conflict in the web sidecar route), the affected files passed
  again (622) and `tcw validate` is OK.

## Behavior change to know about

One open item whose `tracker.yaml` cannot be read or used now stops `link`,
`import`, `create` and filing's ticket for every item (binding scans the whole
board); each says which item to repair.

## Follow-ups

- Filed: `2026-09-26-tidy-three-tracker-messages-left-by-the-binding-hardening-review`
  (five small tracker message and type issues).

## Closeout

- Route: `tcw work complete`, merging into `main` locally; not pushed.
- Jira TCW-18 moves with the item through tracker sync.
- No capability ledger change. Version not cut.
