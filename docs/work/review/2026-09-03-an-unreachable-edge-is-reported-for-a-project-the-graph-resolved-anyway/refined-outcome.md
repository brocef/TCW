# Refined outcome — An unreachable edge is reported for a project the graph resolved anyway

_Accepted._

## Decision

Accepted. The reports this removes were the last noise in the cloud-shaped
Proposit checkout, and one of them actively misled.

## Evidence

- **Suite:** 2309 passed; the established environmental failures.
- **All three Proposit nodes report `validate OK` with no notices** in a checkout
  holding only `proposit-app`. Two false reports before, none after.
- **A genuinely absent project is still reported**, with its own test, so the
  filter did not become a silence.
- **The lookup path is covered**, which is what the correction was about:
  `unreachable_project` is what every message consults, and its test asserts
  `None` for the resolved case.

## Deferred follow-ups

- **A per-edge diagnostic** — "this locator does not resolve here, though the
  project does" — is deliberately not built. It would be useful for someone
  auditing configuration and useless in the common case, which is why the spec
  named it a non-goal rather than a gap.

## Closeout choices

- **Merge route:** the session branch.
- **Documentation:** changelog, README, the changed capability body.
- **Capabilities:** `cli/host-multiple-projects-in-one-repo` changed — its
  promise about naming unfollowable connections is now true rather than
  approximately true.
- **Version:** deferred to the run's single cut, now due.
- **Originating GitHub issue:** none.

## Notes

Third defect in this run found by using the software on a real workspace rather
than by a test. All three were in the same place — the seam between a graph that
may be partial and the messages describing it — which is worth knowing the next
time that seam is touched.
