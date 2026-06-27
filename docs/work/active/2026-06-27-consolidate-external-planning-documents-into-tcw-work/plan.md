# Plan — Consolidate external planning documents into TCW work

## Phase 1 — CLI shape and discovery helpers

- Add `consolidate-plans` to `tcw/work/cli.py` command registration and help.
- Implement path resolution and candidate discovery as filesystem-local helper
  code used by the CLI, not as a new abstract `WorkStore` operation.
- Exclude `docs/work/`, `.git/`, common dependency/cache folders, and hidden
  tool output by default.

## Phase 2 — Migration behavior

- Implement dry-run output first: stable rows with candidate path, inferred
  title, and planned target slug/title.
- Implement apply mode using `FsWorkStore.create()` for item creation.
- Write lifecycle artifacts beside the created item:
  `initial-request.md` always, and `spec.md`/`plan.md` only when the source has
  clear matching sections.
- Record source provenance in the migrated artifact text.

## Phase 3 — Cleanup controls

- Add explicit deletion behavior, likely `--delete`, gated on successful
  migration.
- Prefer all-or-report behavior for each source file: a failed migration should
  not delete that file.
- Use the repo's normal removal path for tracked files in implementation and
  tests.

## Phase 4 — Tests

- Add tests in `tests/test_work.py` or a focused new work CLI test module for:
  dry-run no writes, folder-limited discovery, `docs/work/` exclusion, apply
  mode artifact creation, and delete mode safety.
- Include at least one candidate with spec/plan sections and one ambiguous
  request-only document.

## Documentation sync tasks

- Update `README.md` because the public CLI surface changes.
- Update `docs/release-notes/upcoming.md` with user-facing wording.
- Update `docs/changelogs/upcoming.md` with technical implementation notes and
  the commit range.
- Update `skills/tcw-work/SKILL.md` because the work component CLI surface and
  ingestion workflow change.

## Verification

- `pytest`
- `tcw work --help`
- `tcw work consolidate-plans --help`
- A temp-repo smoke test that imports a sample external plan and confirms
  `tcw work list --status backlog` shows the new item.
