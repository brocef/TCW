# Refined outcome — Unreachable connected projects degrade instead of failing every command

_Accepted._

## Decision

Accepted. Every acceptance criterion is met or accounted for, the change is
covered by 16 new tests, and the real-checkout behavior the item exists for is
demonstrated rather than asserted.

## Evidence

- **Suite:** 2245 passed, 4 failed. All four failures reproduce at the `v1.2.3`
  tag with none of this item's code present, so they are the container's
  (root defeats the `PermissionError` assertions; one test builds a wheel).
- **The failure this item was filed for is gone.** `tcw work list` in
  `apps/server` of a code-only `proposit-app` checkout no longer answers
  `registered target has no tcw-config.yaml`. `tcw validate` there exits 0 and
  names the connection it could not follow.
- **The sibling case is fixed, and provably.** Declaring the in-repo
  `proposit-shared` edge takes the `extends project 'proposit-shared' is not
  reachable` problems from seven to zero, leaving only `proposit-core` — the
  cross-repository edge the next items address.
- **Fail-closed is intact.** Invalid and duplicate IDs, cycles, unparseable
  YAML, and a *present* counterpart pointing elsewhere all still raise, each
  with its own test.
- **The spec's first risk was checked, not assumed.** A mistyped locator now
  reads as unreachable rather than as an error, so the mitigation had to be real:
  `tcw validate` prints it every run, naming the project, the config that
  declared it, and the path it resolved to.

## Deferred follow-ups

- **`registered_project_id`** was listed in the spec as a message site and turned
  out not to be one. No follow-up needed; recorded so a later reader does not go
  looking.
- **`tcw validate --json`** does not exist, so criterion 8's JSON half is served
  by the `check()`/`unreachable()` API split. A JSON surface for `validate` is a
  separate item if anyone wants one.
- **The store half of the cloud case** — `work.path` naming an absent directory —
  is the blocked follow-up item, by design.
- **`_extended_component_roots` composing `docs/<component>`** was filed
  separately from the spec's sweep and is on the board.

## Closeout choices

- **Merge route:** committed directly to the session's working branch, as every
  item in this run is; no worktree was used.
- **Documentation:** README, release notes, changelog, the changed capability
  body, and two `tcw-work` skill references, all in `1389a5a`.
- **Capabilities:** `cli/host-multiple-projects-in-one-repo` reworded to separate
  an inconsistent declaration from an unfollowable one. No new capability.
- **Version:** *deferred deliberately.* Per `CLAUDE.md`, the version cut is
  batched across a run of items rather than cut one per item, and publishing is a
  human step. This item is one of several landing together; the cut is offered
  once at the end of the run.
- **Originating GitHub issue:** none — the item came from a working session.

## Notes

The plan's task ordering held: every commit left the suite green, and the one
deviation (merging the reporting task into the reclassification) was forced by
exactly the rule the plan used to order the tasks in the first place.
