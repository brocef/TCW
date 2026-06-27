# Outcome — Show lifecycle artifact stages in work list

Work implemented and ready for verification.

## What changed

- `tcw work list` now prints a lifecycle artifact stage string in the third
  column instead of the usually-empty `phase` value.
- Stage letters are `R` for `initial-request.md`, `S` for `spec.md`, `P` for
  `plan.md`, `O` for `outcome.md`, and `F` for `refined-outcome.md`.
- Missing or whitespace-only artifact files do not contribute letters; `-`
  remains the fallback when no lifecycle artifacts are present.
- Updated README, release notes, changelog, `tcw-work` skill, and the work
  capability ledger.

## Verification

- `pytest tests/test_work.py` — 68 passed.
- `pytest` — 218 passed.
- `tcw work list --status active` — active item row shows `RSPO`.
- `tcw capabilities check` — capabilities OK.

## Deviations from plan

- Included `F` for `refined-outcome.md` so the full lifecycle artifact spine is
  represented in the compact display.
