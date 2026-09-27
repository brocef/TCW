# Plan: resolve capabilities.yaml sidecar paths while an item is still being worked

## Tasks

1. **Tests first** in `tests/test_sidecar_paths_in_validate.py`: criteria 1-5
   through `validate()`, each asserting the exact file:line prefix.
2. **Gate policy** in `tcw/work/recursion.py`: `in_progress=` on
   `capability_gate`; existing gate tests stay green (criterion 6).
3. **Validate pass** in `tcw/validate.py`.

## Documentation Sync

- Changelog, release notes.
- `docs/guide/linking-and-validation.md`: what validate checks.
- `skills/capabilities/SKILL.md`: the schema paragraph says the gate checks
  paths; add that validate checks them earlier.

## Verification

Hands-on: scratch node with an active item declaring `new: [shared/x]`; run the
worktree's `tcw validate`.
