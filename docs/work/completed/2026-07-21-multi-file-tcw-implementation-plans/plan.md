# Multi-file TCW implementation plans

## Phase 1: Plan-stage model and validation

- Add storage-neutral `PlanStage` and stage-resource types to the work store.
- Parse optional canonical YAML frontmatter from `plan.md`; retain legacy plans
  when `stages` is absent.
- Validate IDs, dependencies, DAG acyclicity, optional metadata, registered
  tags, required plan/stage sections, document presence, and undeclared files.
- Add parser and store tests covering serial and parallel graphs, malformed
  declarations, revisions, locators, atomic writes, deletion, stale writes, and
  a non-filesystem adapter.

Touch points: `tcw/store/base.py`, `tcw/store/fs.py`, validation modules,
`tests/test_work.py`, `tests/test_store_editor.py`, and focused validation tests.

## Phase 2: API resources

- Extend work detail serialization with ordered plan-stage summaries and
  revisions.
- Add authenticated resource-oriented routes for reading, replacing, deleting,
  and opening declared stages.
- Apply the same CSRF, size, path-safety, validation-warning, and 409 semantics
  as existing artifact routes.
- Test malformed manifests, unknown stages, encoded traversal, CRUD/open,
  validation warnings, and revision conflicts.

Touch points: the current serve implementation and its API test modules. This
phase depends on Phase 1 and on the active Fastify/React migration's settled API
structure.

## Phase 3: React work-detail editing

- Extend client types and API helpers for plan-stage summaries and resources.
- Render metadata, dependencies, parallel-ready groups, presence, and individual
  open/edit/delete controls.
- Preserve drafts when validation fails and reuse dirty-navigation and stale
  write recovery behavior.
- Add React unit and Playwright coverage for presentation and editing flows.

Touch points: `web/client/src/model/`, `web/client/src/ui/`, styles, unit tests,
and `web/e2e/`. This phase depends on Phases 1 and 2.

## Phase 4: Agent workflow and documentation

- Update `skills/tcw-work/SKILL.md`, task/epic lifecycle references, and the
  planning/drive prompt commands: staged plans are optional, `plan.md` loads
  first, only the relevant stage is then loaded, and pre/post checks bracket
  implementation. Ordering remains advisory and progress prose is not state.
- Update `plugin/work-lifecycle` and `web/editing` capability descriptions.
- Update `README.md`, `docs/release-notes/upcoming.md`, and
  `docs/changelogs/upcoming.md`; include the implementation commit range in the
  changelog.

This phase can begin after the behavior is stable and depends on the final
public/API shape from Phases 1-3.

## Phase 5: Verification and reconciliation

- Run focused parser/store/API/React tests throughout implementation.
- Run the complete Python test suite.
- Run the established pnpm typecheck, lint, unit, E2E, and build checks.
- Run `tcw capabilities check`, `tcw taxonomy check`, `tcw validate`, and
  `git diff --check`.
- Confirm legacy plans, board `P`, lifecycle transitions, consolidation, and
  existing artifact editing remain unchanged.
- Reconcile the declared changed capabilities and record the evidence in
  `outcome.md` before requesting user verification.

## Parallelization

Once Phase 1 fixes the store contract, API implementation and workflow-document
drafting can proceed independently. React implementation waits for the API
payload and routes. Verification runs after all implementation and docs converge.

## Documentation sync

The public CLI/user behavior trigger requires `README.md` and release notes. Any
code change requires the developer changelog with commit range. The work
component changes require its driving skill and relevant lifecycle references.
