# Refined outcome — `extends` resolves the sibling's store

_Accepted._

## Decision

Accepted. The substitution is small; the two corrections it forced are the
interesting part, and both are covered by tests that existed before the change or
were added with it.

## Evidence

- **Suite:** 2306 passed; the established environmental failures only.
- **The defect is fixed and demonstrated**: a sibling whose capabilities tree is
  at a configured `capabilities.path` is now extended, and its capability appears
  in the extending node's federated list.
- **Both misleading messages are gone**, each with its own test: a project with
  no component is named as such, and one with a declared-but-unprovisioned tree
  reports the url and `tcw provision`.
- **The cycle is still reported, not recurred.** `test_check_federation_cycle`
  failed the moment the naive substitution landed and passes with the guard moved
  to project identity — which is the check doing exactly its job.
- **Nothing else moved.** Every pre-existing federation, reset and taxonomy test
  passes unmodified, which was the criterion for "the default path is untouched".

## Deferred follow-ups

- **No taxonomy-side test of the moved-tree case.** The capabilities test covers
  the shared code path — `_extended_component_roots` is component-generic and
  both stores reach it identically — but the symmetric taxonomy test is not
  written. Low value, honestly noted.
- **The read-path cost is unmeasured.** One extra config read per store open, no
  perceptible change to `tcw validate` on this repository. Not benchmarked, and
  at this magnitude that is a decision rather than an omission.

## Closeout choices

- **Merge route:** the session branch.
- **Documentation:** changelog and release notes. README and the component skills
  were checked and assert nothing about where an extended tree lives, so those
  triggers did not fire — recorded so the next reader knows they were considered
  rather than missed.
- **Capabilities:** none. `capabilities/federate` describes extending another
  project's tree without saying where it sits, so this makes an existing claim
  true rather than changing it.
- **Version:** deferred to the end of the run — this is the last item, so the cut
  is now due.
- **Originating GitHub issue:** none; found by a sweep.

## Notes

Worth recording that this was found by the `spec` stage's required sibling sweep
and not by a user, and that the sweep was right: no configuration hits it today,
and the failure it would have produced was silent and misdirecting.
