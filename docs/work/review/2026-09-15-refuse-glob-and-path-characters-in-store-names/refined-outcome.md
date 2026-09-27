# Refined outcome: store names are names, never patterns

## Decision

**Accepted** on 2026-09-26 in an unattended run (`extras-autonomous-work`), by
the coordinating session on the verifier's recommendation; no user present.

## Evidence

- Criteria 1-4: `tests/test_literal_store_names.py` (4 of its first 6 tests
  failed on main's code, as the verifier reproduced), and its hands-on runs:
  path-shaped slugs through the store API, 404s from `tcw serve`, capability
  `a*` set and removed beside an unsaved edit in `abc`, and every command with
  `GIT_LITERAL_PATHSPECS=1`.
- Criterion 3 was rewritten after review (work slugs cannot hold `[` or `?`);
  it is tested through the stage and commit helpers a transition uses.
- Criterion 5: full suite 4592 passed, 3 skipped; after merging main, the
  affected files passed again (161).

## Follow-ups

- Not filed: `start --worktree` on a hand-made glob-named folder (git refuses
  the branch name); nothing TCW creates can have such a name.

## Closeout

- Route: `tcw work complete`, merging into `main` locally; not pushed.
- Jira TCW-20 moves with the item through tracker sync.
- No capability ledger change. Version not cut.
