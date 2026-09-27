# Refined outcome: strict gate refuses unfollowable moves; import nests children

## Decision

**Accepted** on 2026-09-27 in an unattended run (`extras-autonomous-work`), by
the coordinating session on the verifier's recommendation; no user present.

## Evidence

- Criteria 1-5: `tests/test_tracker_strict_gate.py` (13) and the existing
  held-item test, plus the verifier's probes.
- Criterion 6: full suite 4635 passed, 3 skipped on the final code; after
  merging main (which brought the tracker-hardening item), every tracker test
  file passed (1140) and `tcw validate` is OK.

## For the user to know

- Under strict mode a `submit`, `rework` or `complete` is now refused when the
  ticket's workflow has no single transition to follow.
- `tcw work new --parent` stays refused under strict mode; nest a child with
  `tcw work tracker import <ticket> --parent <slug>`. Both advisors flagged
  allowing `new` as a product decision for a person.
- The spec was corrected twice during the item (an impossible "resolution" fix
  removed; `--initiative` validation claim corrected).

## Follow-ups

- Filed: `2026-09-27-close-two-strict-mode-gaps-left-by-the-unfollowable-move-gate`
  (three gaps).

## Closeout

- Route: `tcw work complete`, merging into `main` locally; not pushed.
- Jira TCW-19 moves with the item through tracker sync.
- Capability `work/require-tracker-backed-work` description updated (declared
  `changed`). Version not cut.
