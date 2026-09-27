# Refined outcome: show the server's message for a web save refused for a reason other than a stale revision

## Decision

**Accepted** on 2026-09-26 in an unattended run (`extras-autonomous-work`), by
the coordinating session on the verifier's recommendation; no user present.

## Evidence

- Server: stale PATCH and PUT carry `"code": "stale-revision"`; generated-sidecar
  and strict refusals do not (`tests/test_serve_write.py`,
  `tests/test_tracker_strict.py`; 8 + 1 targeted passes by the verifier).
- Client: `isStaleWrite` unit test, 5 passed; it went red against the old
  "every 409 is stale" rule. tsc and eslint clean.
- Playwright: 14 passed, including the real stale-write banner.
- Full Python suite: 4475 passed, 3 skipped.
- Hands-on: `curl` against `tcw serve` from the worktree showed the marker only
  on the stale refusal.

## Follow-ups

None filed. Known limit recorded in `outcome.md`: no UI path reaches a non-stale
409 today, so the fix guards the next one.

## Closeout

- Route: `tcw work complete`, merging into `main` locally; not pushed.
- Jira TCW-1 moves with the item; the ticket's reporter is not written to (no
  GitHub issue).
- No capability ledger change. Version not cut.
