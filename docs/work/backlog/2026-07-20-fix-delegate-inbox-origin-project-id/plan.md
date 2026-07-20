# Implementation plan

## Phase 1 — Correct delegation metadata

1. In `tcw/work/recursion.py`, resolve the current node's registered project ID
   inside `delegate`.
2. Pass that stable ID to `_inbox_write` instead of the legacy `"."` marker.
3. Keep child selection, inbox-only writes, and initiative handling unchanged.

## Phase 2 — Lock the behavior with tests

1. Update `tests/test_recursion.py` to assert the parent fixture's registered ID
   in delegated frontmatter.
2. Update `tests/test_environment_hardness.py` to assert the registered parent
   ID for delegation across the sibling-project graph.
3. Run the focused delegation/escalation tests before the full suite.

## Phase 3 — Documentation sync and verification

1. Leave `README.md` unchanged: the documented command and stable-ID behavior
   do not change; the implementation is being brought into conformance.
2. Update `docs/release-notes/upcoming.md` because users see corrected
   delegation metadata.
3. Update `docs/changelogs/upcoming.md` because runtime behavior changes,
   including a traceable commit range.
4. Leave `skills/tcw-work/SKILL.md` unchanged: its delegation model already
   specifies project-ID `from:` metadata and no workflow or guardrail changes.
5. Run `python -m pytest -q`, `tcw capabilities check`, `tcw taxonomy check`,
   `tcw validate`, and `git diff --check`.

## Phase 4 — Closeout and patch release

1. Record implementation evidence in `outcome.md` and the user-approved release
   decision in `refined-outcome.md`.
2. Complete and checkpoint the work item.
3. Run `python scripts/cut_version.py patch` to bump all five version-bearing
   files, rotate both upcoming documents, commit, and tag 0.13.1.
4. Verify version agreement, release-file rotation, tag placement, clean
   status, and the final test suite. Do not push.

## Parallelization

The code and two assertions form one atomic behavior change and are faster and
safer to execute sequentially. Documentation depends on the implementation
commit range, and the release depends on all prior verification.
