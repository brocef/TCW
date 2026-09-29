# Refined outcome — Share one descendant walk, and say when delegate names a node with no board

## Decision

**Accepted**, 2026-09-29, during an unattended run: the decision is the
implementing agent's, taken in place of the user's at the user's request, on the
evidence below.

## Evidence

- `tcw:verifier` assessment: criteria 1–4 met by tests and by hand through the
  CLI in scratch graphs (`reconcile` rows `.`, `pa`, `pb`; the boardless,
  not-provisioned, broken-path and unregistered messages; ancestor and sibling
  still "no child node").
- Full suite after the review fixes (started after `df415d68`), from the item
  worktree with its private virtual environment: **4803 passed, 3 skipped**.
- One verify fold-in after that run (`f23c6a3a`): "keeps no board" unless the
  node sets `work.path` or `work.repository` (a `work:` section with other
  settings only was read as a broken board). One condition; the item's tests
  and `tests/test_routing_nodes.py` pass (14).
- Hands-on (mine): root → mid (no board) → pa; `tcw work delegate mid Hello`
  exits 1 with "'mid' keeps no board … Nodes with a board below it: pa.";
  `tcw work delegate pa Hello` writes into pa's inbox.

## Accepted deviations from the spec

- Goals 2–3 and the Design were amended at review and verify: the message is
  for nodes below this one only, and a board that is configured but cannot be
  opened gives its reason.

## Closeout

- Capability reconciliation: none declared; nothing to reconcile.
- Documentation: changelog and release-note entry files.
- Not from a GitHub issue.
- Merge route: `tcw work complete` from the `bug-run` integration worktree,
  merging into `bug-run`; `main` is left for the user to merge.
- Follow-ups: none filed. Recorded, not filed: `reconcile` opens each store
  about twice as often as before.
