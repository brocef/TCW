# Refined outcome — Provisioning stops walking at a project that is already here

_Accepted._

## Decision

Accepted. The steady state — the only state a configured workspace is normally in
— now provisions correctly, demonstrated on the real repositories rather than a
fixture.

## Evidence

- **Suite:** 2322 passed on the final tree; the five environmental failures.
- **The real case:** with the orchestration node already provisioned and only the
  `proposit-core` copy removed, `tcw provision` re-obtains core. Before, the
  present orchestration node was skipped and never read, so the project reachable
  only through its declaration was invisible.
- **Both holes are covered separately**: `projects()` for what is present at the
  start, the enqueue for what becomes present during the walk.
- **`--dry-run` plans rather than claims.** Asserted with a project declared from
  both sides, and by the absence of any cache directory.

## Deferred follow-ups

- **`--component` does not scope node provisioning.** `_provision_nodes` runs
  outside the component loop, so `tcw provision --component taxonomy` still
  contacts every declared connected-project remote. The documentation now says so
  plainly, but whether it *should* be scopable is a design question rather than a
  defect, and it is filed separately rather than decided in this item.
- **`repository.checkout` is unbounded in a transitively discovered config.**
  `path` is bounded against escape; `checkout` is not, and the transitive walk
  means a third-hop config the user never wrote can name a directory. Existing
  mitigations are real but partial: the destination is printed before contact,
  `_obtain` refuses an existing directory, and a refresh into a foreign
  repository is refused. Filed separately as a design question.

## Closeout choices

- **Merge route:** the session branch, per the run-wide deviation recorded on the
  delete-safety item.
- **Documentation:** the changelog entry for connected-project declarations
  already covers the reachability rule; this makes it true rather than changing
  it. No release-note change: a user never saw the broken intermediate.
- **Capabilities:** none — `cli/provision-declared-stores` already promises a
  project you can reach is never fetched, and says nothing about the walk
  stopping there.
- **Version:** accumulating; no cut.
- **Originating GitHub issue:** none.

## Notes

Two design questions surfaced and were deliberately not settled here, because
both are about what the command *should* do rather than whether it does what it
says: scoping node provisioning, and bounding `checkout` in a config the user did
not write. Filed.
