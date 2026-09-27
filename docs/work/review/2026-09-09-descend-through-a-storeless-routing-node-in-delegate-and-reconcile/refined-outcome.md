# Refined outcome — Descend through a storeless routing node in delegate and reconcile

**Accepted** (unattended run, 2026-09-27).

- `delegate` reaches the nearest node with a board on each branch, passing
  through nodes that keep none; aimed at a node below a board, it names that
  board as the target. `reconcile` reads every descendant with a board — the
  same set the completion gate reads. `tcw work nodes` is unchanged.
- Verified: the verifier found criteria 1–4 met; criterion 5 by the full suite
  on the branch merged with main (4679 passed, 3 skipped); the issue's graph driven by hand
  through the CLI.
- Review: one blocking finding (a registry reopened at each routing node broke
  `delegate` from a linked worktree), fixed with one registry at the root and a
  regression test that fails on the first version.

## Deferred

- **GitHub #30 stays open until publication.** This repository closes an
  originating issue only after the version carrying the fix is cut and pushed,
  and nothing is posted without the exact text approved first.
- Follow-up filed:
  `2026-09-27-share-one-descendant-walk-and-say-when-delegate-names-a-node-with-no-board`.
  Slug-only matching in `reconcile`'s Next line is handled by
  `2026-09-09-resolve-a-cross-node-external-blocker-against-the-node-that-owns-it`.
