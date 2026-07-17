# Refined outcome: flag / auto-advance a completable epic

## Verification decision

Approved under the user's standing directive — "do the first two [backlog items],
drive to completion" (local merge to `main`; version cut batched for later).
Dual-reviewed and verified before completing.

## Refinements after initial implementation

From the review (a real Medium bug + a Low): moved `capability_gate` into
`recursion.py` so `reconcile --complete-when-ready` enforces it (it previously
bypassed the gate — a broken guarantee), with a test covering a Missing declared
capability; and restructured `reconcile` to rewrite the rollup after completion so
a completed epic keeps no stale "Ready to close" note (+ regression test). The
marker-precision Low was intentionally left: `ready-to-close` means "children
resolved," as the docs frame it.

## Capabilities reconciliation (completion gate)

- `work/complete-a-work-item` + `work/view-the-board` (both `changed:`) — bodies
  updated (epic complete-from-backlog / auto-complete; `ready-to-close` marker);
  both remain `Supported` and resolve. `changed:` entries are checked only for
  resolution — clean.
- `tcw capabilities check` + `tcw validate` clean.

## Final verification evidence

- `pytest` — 649 passed.
- CLI end-to-end: `ready-to-close` marker, rollup line, complete-from-backlog,
  `--complete-when-ready` auto-close, capability-gate refusal.

## Closeout choices

- **Route:** implemented directly on `main` — already local-merged.
- **Documentation:** README, release notes, developer changelog, `tcw-work` skill,
  and both capability bodies updated.
- **Follow-ups:** none.
- **Version bump:** deferred — both requested backlog items are now done; ready to
  offer a cut on the user's go-ahead.
