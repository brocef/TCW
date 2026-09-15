# Plan — Show lifecycle artifact stages in work list

## Phase 1 — Stage-string helper

- Add a helper near `_list` in `tcw/work/cli.py` that accepts the store and item
  slug, resolves the item folder, and returns a compact stage string.
- Track bounded lifecycle artifact names in order:
  `initial-request.md`, `spec.md`, `plan.md`, `outcome.md`, and possibly
  `refined-outcome.md` if implementation chooses to expose it.
- Treat missing, empty, and whitespace-only files as absent.

## Phase 2 — List output

- Replace `it.phase or '-'` in the `emit()` row with the new stage string or
  `-`.
- Preserve the row order and delimiter:
  `<slug> | <status> | <stages|-> | <priority|-> | <title>[ | blocked-by: ...]`.
- Leave `tcw work show` unchanged so stored `phase` remains visible when set.

## Phase 3 — Tests

- Add `tcw work list` tests covering no artifacts, each artifact letter,
  combined `RSP`, empty artifact files, nested child rows, and blocker suffixes.
- Keep existing priority/list tests passing with the third-column meaning
  updated.

## Documentation sync tasks

- Update `README.md` because public CLI output changes.
- Update `docs/release-notes/upcoming.md` with user-facing wording.
- Update `docs/changelogs/upcoming.md` with technical implementation notes and
  the commit range.
- Update `skills/tcw-work/SKILL.md` because the work list guidance changes.
- Update `docs/capabilities/work/capabilities.md` for the changed board output
  when the implementation lands.

## Verification

- `pytest tests/test_work.py`
- `pytest`
- `tcw work list --status backlog`
