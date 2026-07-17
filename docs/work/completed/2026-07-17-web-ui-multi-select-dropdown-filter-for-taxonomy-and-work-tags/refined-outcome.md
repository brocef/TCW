# Refined outcome: web UI multi-select dropdown filter

## Verification decision

Approved under the user's standing directive this session — "drive the other work
items to completion" (local merge to `main`, defer the version cut). Verified
in-browser and dual-reviewed before completing.

## Refinements after initial implementation

None. The implementation met every acceptance criterion on first in-browser check,
and the dual review required no code changes.

One judgment-call finding is **surfaced, not silently resolved** (per the review
rule): facet filters prune matches but don't force-expand a manually-collapsed
parent (spec-aligned with the status toggles; the text filter does force-expand).
Kept the spec-compliant behavior; the user can request the "reveal like search"
variant as a one-line follow-up. See `outcome.md` for the full triage.

## Capabilities reconciliation (completion gate)

- `web` (Browse TCW content in a local web app) — `changed:`. Body updated to
  describe the independent list-column scroll and the multi-select category filter
  (tag for work, kind for taxonomy) alongside the text filter. Still `Supported`.
- `tcw capabilities check` and `tcw validate` clean.

## Final verification evidence

- In-browser: taxonomy Kind prune; work Tags OR multi-select (3 of 5 items);
  empty-tags hint; no capabilities-view facet; dropdown stays open; popover
  un-clipped; no console errors.
- `pytest` — 629 passed.

## Closeout choices

- **Route:** implemented directly on `main` (no `--worktree`) — already local-merged.
- **Documentation:** README (`tcw serve` section), release notes, developer
  changelog, and the `web` capability body updated. `tcw-work` skill unchanged
  (web-only, not a `tcw work` CLI change).
- **Follow-ups:** optional facet force-expand behavior (finding 1). No new TCW
  items created; the user can decide.
- **Version bump:** now that all three 2026-07-17 tags/web items are done, a cut is
  ready to offer — **deferred pending the user's go-ahead** (they said the cut comes
  after these items).
