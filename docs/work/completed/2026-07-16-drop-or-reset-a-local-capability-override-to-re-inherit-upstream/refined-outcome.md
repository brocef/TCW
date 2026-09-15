# Refined outcome: drop/reset a local capability override

## Verification decision

Approved under the user's standing directive — "do the first two [backlog items],
drive to completion" (local merge to `main`; version cut batched for later).
Dual-reviewed and verified before completing.

## Refinements after initial implementation

From the review: documented `AmbiguousRef` on the abstract `reset` and added a
two-alias ambiguous-ref test (commit `Reset review fixes …`). No behavior change —
the propagation was already correct by construction. One review note (untracked
hand-created override folder → `CalledProcessError`) was intentionally left as-is,
matching the existing `remove` behavior.

## Capabilities reconciliation (completion gate)

- `capabilities/reset-an-override` (`new:`) — flipped `Missing → Supported`. Body
  authored with the user story and a `tcw://` link to `capabilities/override-inherited`.
- `tcw capabilities check` + `tcw validate` clean.

## Final verification evidence

- `pytest` — 635 passed.
- CLI end-to-end (federated): override → reset re-inherits → refuses when none →
  upstream untouched.

## Closeout choices

- **Route:** implemented directly on `main` — already local-merged.
- **Documentation:** README, release notes, developer changelog, and the
  `tcw-capabilities` skill updated.
- **Follow-ups:** none.
- **Version bump:** deferred (batched with item #2, then a cut on your go-ahead).
