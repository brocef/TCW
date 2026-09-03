# Refined outcome — `tcw provision` fetches a project the checkout already has

_Accepted._

## Decision

Accepted. Small, and it closes the one gap between the node walk and the rule the
rest of TCW follows.

## Evidence

- **Suite:** 2307 passed; the established environmental failures.
- **The real reproduction is fixed**, and it is the acceptance evidence rather
  than a fixture: the line that read `proposit-app-repo: would obtain into …` now
  reads `already available`, and the cache holds two directories instead of
  three.
- **The absent project is still obtained in the same run**, so the skip did not
  turn into a blanket refusal.
- **One cache directory per repository**, asserted by name so a second copy of
  the caller's own repo would fail the test.

## Deferred follow-ups

- **`--refresh` on a present project** bypasses the skip by construction and is
  asserted only indirectly. A dedicated test would be cheap; it is not written.

## Closeout choices

- **Merge route:** the session branch.
- **Documentation:** changelog, README's transitive paragraph, and the
  `cli/provision-declared-stores` body.
- **Capabilities:** `cli/provision-declared-stores` changed, recorded in
  `capabilities.yaml`.
- **Version:** deferred to the run's single cut.
- **Originating GitHub issue:** none.

## Notes

Worth keeping: this was found in the first hour of using the feature on a real
workspace, and the fixtures written for that feature could not have found it —
they had no case where two nodes both knew about one edge, which is the normal
state of a reciprocal graph. The lesson is the one the previous item's notes
already recorded, now with a second example.
