# Plan — Keep a child whose state.yaml cannot be read visible to its parent's completion gate

## Tasks

1. **Write the tests first:** `tests/test_unreadable_state_gates.py`, one test
   per acceptance criterion from 1 to 5. Run them against the current code
   and confirm criteria 1, 2, 3 and 5 fail for the reason the spec gives.
   Criterion 4 guards against an over-broad fix, so it passes before and
   after.
2. **Store code (`tcw/store/base.py`, `tcw/store/fs.py`).**
   - Add `unreadable_open_items()` and `unreadable_slice_candidates()` to
     the abstract store, each returning `[]` by default.
   - Pull `_state_damage` out of `_require_readable_state`.
   - Implement both methods in `FsWorkStore`.
   - Add the refusal to `require_nothing_open_beneath`, and the epic
     refusal in `complete`, placed before `from_backlog_epic` is computed.
3. **Mutation checks.** Remove each refusal in turn and confirm its tests
   go red.
4. **Full suite**, run in the item's own venv.

## Documentation Sync

- `docs/changelogs/upcoming/<slug>.md` (Any-Code-Change): under Fixed.
- `docs/release-notes/upcoming/<slug>.md` (Public-API): the user-visible
  refusal.
- `docs/guide/work.md` (Guide-Topic-Change): add a sentence each to the
  parent paragraph (around line 527) and the epic paragraph (around line
  345).
- `skills/work/references/transitions.md` (Skill-Driven-Component): add the
  refusal next to the epic bullet (line 103).
- README, `configure`, and `jira.md`: not triggered, because no CLI
  surface, configuration key, or tracker behavior changes.

## Verification

- Every acceptance criterion is covered by a test.
- A hands-on check drives `tcw work complete` against a scratch board with
  a damaged slice.
