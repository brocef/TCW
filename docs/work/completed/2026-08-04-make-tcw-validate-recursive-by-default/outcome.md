# Outcome

## Shipped

1. Added CLI regression coverage for recursive registered descendants, nested
   descendant failures, clean recursive runs, `--no-recurse`, local path
   selection, and descendants without work stores. Implemented the recursive
   root selection in `tcw/cli.py`, using `FsProjectRegistry.descendants()` and
   canonical project IDs in multi-project diagnostics. Explicit paths remain
   local and automatically disable recursion. Commit: `100eda3`.

2. Completed the Documentation Sync gate. Updated the README, user-facing
   release notes, developer changelog, and `cli/validate-a-node` capability to
   describe the recursive default, `--no-recurse`, and local path behavior.
   No driving component skill changed because `tcw validate` remains a
   top-level cross-component command and no component CLI/model/lifecycle
   contract changed. Commit: `f0ee8fa`.

## Verification

- `python -m pytest tests/test_validate.py tests/test_project_registry.py -q`
  — 42 passed.
- `python -m pytest tests/test_validate_target.py tests/test_environment_hardness.py -q`
  — 78 passed.
- `python -m pytest -q` — 1170 passed.
- `tcw validate --help` — documents `--no-recurse` and states that an explicit
  path disables recursion.
- `tcw capabilities check` — passed.
- `tcw taxonomy check` — passed.
- `tcw validate` — passed with the new recursive default.
- `git diff --check` — passed.

## Plan and specification corrections

None. The implementation followed the planned CLI-orchestration boundary and
left the storage-neutral `validate(..., target=...)` behavior unchanged.
