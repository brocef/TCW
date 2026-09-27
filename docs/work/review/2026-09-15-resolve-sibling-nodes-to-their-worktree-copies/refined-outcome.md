# Refined outcome: resolve sibling nodes to their worktree copies

## Decision

**Accepted** on 2026-09-27 in an unattended run (`extras-autonomous-work`), by
the coordinating session on the verifier's recommendation; no user present.

## Evidence

- Criteria 1-4: `tests/test_worktree_sibling_nodes.py` (9) and the verifier's
  hand-built layouts, each run with main's build and the branch's.
- Criterion 5: full suite 4631 passed, 3 skipped on the final code; after
  merging main, the resolver, validate, recursion, worktree and provisioning
  files passed (369) and `tcw validate` is OK.

## Follow-ups

- Filed: `2026-09-27-resolve-project-graph-paths-by-case-and-through-a-symlinked-config`
  (letter case, a symlinked config, the override question, and two submodule
  layouts).

## Originating issue

GitHub #39 is **not** answered or closed yet. This repository's rule is that an
issue closes only after the fix is published — complete the items, cut the
version, push, then answer and close — so the reporter is never told it is fixed
before they can install it. Nothing is posted without the exact text being
approved first.

## Closeout

- Route: `tcw work complete`, merging into `main` locally; not pushed.
- Jira TCW-12 moves with the item through tracker sync.
- No capability ledger change. Version not cut.
