# Implementation plan

1. Add recursive CLI coverage in `tests/test_validate.py` using registered
   parent, child, and grandchild fixtures. Prove that bare `tcw validate`
   surfaces a descendant-only problem with project context and exits `1`, that
   all-clean recursion exits `0`, that `--no-recurse` ignores descendant content
   failures, that an explicit path stays local, and that a descendant with only
   taxonomy or capabilities initialized is not omitted. Retain focused tests for
   invalid project graphs and existing single-node behavior. Run
   `python -m pytest tests/test_validate.py tests/test_project_registry.py -q`.

2. Update the top-level validation orchestration and parser in `tcw/cli.py`.
   Add `--no-recurse`; after the active registry passes its fail-closed check,
   select the active project plus the registry's recursively declared
   descendants for a bare command, or only the active project when opted out or
   when a path selector is present. Invoke the existing single-project
   `tcw.validate.validate` operation for each selected project, qualify
   multi-project diagnostics with canonical project IDs, aggregate failures,
   and print success only after the selected set is clean. Do not make
   filesystem discovery or the work-store-filtered `child_nodes()` helper part
   of validation semantics. Re-run the focused tests from task 1 and
   `python -m pytest tests/test_validate_target.py tests/test_environment_hardness.py -q`.

3. Run the broader regression suite to catch callers that assume bare
   validation is single-project or depend on its exact output:
   `python -m pytest -q`. Also run `tcw taxonomy check`,
   `tcw capabilities check`, `tcw validate --no-recurse`, and
   `git diff --check`.

4. Complete Documentation Sync as one final block after the implementation is
   stable:

   - Update `README.md` for the public CLI behavior, recursive default,
     active-project-only flag, path-selector scope, and examples.
   - Update `docs/release-notes/upcoming.md` in user-facing language because the
     public command behavior changes.
   - Update `docs/changelogs/upcoming.md` with the technical CLI and traversal
     change because runtime code changes.
   - Update `docs/capabilities/cli/validate-a-node/description.md` so the standing
     capability describes recursive descendant validation, `--no-recurse`, and
     local path narrowing.
   - Re-evaluate the `[Skill-Driven-Component]` trigger against the finished
     diff. No matching component skill update is currently expected because
     `validate` is a top-level cross-component command, but update any driving
     skill whose CLI/model/lifecycle contract actually changes during
     implementation.

   Verify the finished documentation and capability ledger with
   `tcw capabilities check`, `tcw taxonomy check`, `tcw validate --no-recurse`,
   and `git diff --check`.

## Verification

- Inspect `tcw validate --help` to confirm `--no-recurse` is discoverable and
  the positional path help makes its local-only scope clear.
- In an isolated nested fixture, confirm diagnostics name the descendant
  project rather than presenting ambiguous identical relative paths.
- Confirm no object-scoped `validate(..., target=...)` caller changes behavior;
  recursion remains CLI orchestration and does not alter the storage-neutral
  validation selector.
- Do not start the work item, implement code, update release metadata, or cut a
  version until this plan is reviewed and implementation is explicitly begun.
