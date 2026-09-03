# Refined outcome — The provisioning skip misses a reachable project

_Accepted._

## Decision

Accepted. The workstation layout now fetches nothing, which is the property the
whole feature has to have for someone who already holds every repository.

## Evidence

- **Suite:** 2310 passed; the established environmental failures.
- **The hierarchical workspace plans nothing and creates no cache directory** —
  four `already available` lines and no remote named. That is criterion 3, run
  against the real Proposit configuration rather than a fixture.
- **The absent project is still obtained** in the same run, so the wider skip did
  not become a blanket refusal.
- **One cache directory, matched by cache key** rather than by a substring that
  the test's own name could satisfy.
- **The previous skip test passes unchanged**, so the narrower case is still
  covered.

## Deferred follow-ups

- **`--refresh` on a present project** is still asserted only indirectly, carried
  over from the previous item. Cheap to write; not written.

## Closeout choices

- **Merge route:** the session branch.
- **Documentation:** the changelog entry for the skip, amended rather than
  duplicated — the two ship together and a reader never saw the intermediate
  behavior.
- **Capabilities:** none. `cli/provision-declared-stores` already promised what
  the code now does.
- **Version:** deferred to the run's single cut.
- **Originating GitHub issue:** none.

## Notes

Accepting a second correction to the same two lines is worth a moment's honesty:
the first fix was written to the case in front of it, and the spec that approved
it said "already reachable here" without noticing that the implementation had
substituted three relations for that phrase. The verify stage read the code
against the criteria and did not catch it either. What caught it was running the
command in a layout nobody had tried yet — which is the argument for keeping the
two-layout check in the verification plan of anything touching this seam.
