# Plan: resolve sibling nodes to their worktree copies

## Tasks

1. **Tests first** in `tests/test_worktree_sibling_nodes.py`: criteria 1-4 with
   real repositories and `git worktree add`.
2. **Rule 2** in `ProjectRegistry._locator_path`; drop `_counterpart_path` if
   nothing else uses it.
3. **Docs**: changelog and release notes; check
   `docs/guide/connected-projects.md` (or wherever worktree resolution is
   described) for the "exactly one pair" wording.

## Verification

Hands-on: the issue's layout, `tcw validate` from `app-wt/pkg-a` with the
worktree's `tcw`.
