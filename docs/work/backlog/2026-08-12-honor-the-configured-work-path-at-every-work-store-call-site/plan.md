# Implementation plan

## 1. Make opened work stores authoritative for discovery and Git routing

- Add focused two-repository fixtures in `tests/test_external_work_store.py`
  (or a narrowly shared test helper) that initialize a code repository, a
  separately owned configured work store, and optional decoy `docs/work`
  folders. Assert the fixture exposes distinct `node_root`, `root`, and
  `store_git_root` values and can report cleanliness for both repositories.
- Change `_has_work_store` in `tcw/store/fs.py` to determine presence only by
  opening the configured `FsWorkStore`; do not let a literal default directory
  bypass configuration validation.
- Add adapter-private helpers only where they remove repeated, error-prone
  filesystem calculations, such as deriving store-repository-relative
  pathspecs or committing a bounded set of store paths. Do not add filesystem
  paths or Git concepts to `WorkStore`.
- Audit the production `tcw/` tree for `docs/work` construction and Git calls
  receiving work paths. Classify each match as the configured default,
  initialization/ignore behavior, malformed-node validation fallback,
  documentation, or a live call site that must use the opened store.
- Verify with focused store/discovery tests, including valid external stores,
  invalid configured stores with decoy default folders, default stores, and
  registered child/parent/descendant discovery. Run `git diff --check`.

## 2. Route cross-node inbox writes and epic reconciliation through the target store

- In `tcw/work/recursion.py`, open the selected child or parent store before an
  inbox write and address its inbox from `store.root`.
- Tighten `_inbox_write` so it may restore the inbox leaf within a validated
  store but cannot manufacture a missing store root or ancestor chain. Preserve
  collision-safe entry naming and the existing origin/initiative format.
- Route reconciliation staging and optional commits through the epic store's
  `store_git_root`, deriving narrow pathspecs from the resolved content/store
  paths. Preserve unchanged-rollup idempotence and auto-completion behavior.
- Extend `tests/test_recursion.py` with separate-repository delegate, escalate,
  and reconcile cases. Assert destination visibility, absence of phantom
  default folders, exact commit ownership, idempotence, both-repository
  cleanliness, and clear failures when the target store or Git commit is
  unavailable.
- Verify with `python -m pytest -q tests/test_recursion.py
  tests/test_external_work_store.py` and `git diff --check`.

## 3. Make capability drift follow the configured work store

- Replace the literal-directory guard in
  `tcw/capabilities/cli.py::_shipped_but_missing` with an attempted
  `FsWorkStore.open(node)` and the established graceful fallback for a node
  without a usable work component.
- Extend `tests/test_capabilities.py` with an external completed planning item,
  both with and without a decoy default directory. Assert identical
  `shipped-missing` results, while retaining coverage for a true no-work node and
  discarded or non-completed planning items.
- Verify with `python -m pytest -q tests/test_capabilities.py` and
  `tcw capabilities check`.

## 4. Persist `start --worktree` setup in the repositories that own it

- Refactor the `--worktree` branch of `tcw/work/cli.py` so work-item transition
  and metadata paths are committed in `store.store_git_root`, while
  `.gitignore` is committed in `store.node_root` only when changed.
- Derive work pathspecs from `store.root` and the item's actual source and
  destination locations; retain the auto-commit-off behavior without assuming
  the lifecycle files can appear on a code-repository branch.
- Order the commits before `add_worktree`. On either failure, stop, return
  non-zero, name which repository operation failed, and describe already
  persisted state rather than silently continuing. Do not sweep unrelated
  staged changes into either commit.
- Add separate-repository CLI tests in `tests/test_work_autocommit.py` or
  `tests/test_external_work_store.py` for auto-commit on and off, an unchanged
  versus changed `.gitignore`, unrelated staged edits in both repositories, Git
  commit failures at each boundary, branch creation ordering, and final
  cleanliness. Keep the existing default-store branch-history assertions.
- Verify with `python -m pytest -q tests/test_work_autocommit.py
  tests/test_external_work_store.py` and inspect the commit contents created by
  the tests.

## 5. Close the call-site class and run the integrated regression set

- Repeat the production-code audit from task 1 after implementation. Remove or
  route any remaining live call site that reconstructs the active work store or
  uses the code-node Git root for a resolved store path; record why retained
  literals are configuration defaults or adapter-local initialization details.
- Add negative-path assertions where the audit identifies a write that can
  still report success after persisting nothing. Preserve existing exception
  contracts and convert expected operational failures into concise CLI errors
  without tracebacks.
- Run the focused combined set:
  `python -m pytest -q tests/test_external_work_store.py
  tests/test_recursion.py tests/test_capabilities.py
  tests/test_work_autocommit.py tests/test_validate.py
  tests/test_validate_target.py`.
- Run `tcw taxonomy check`, `tcw capabilities check`, `tcw validate
  --no-recurse`, and `git diff --check`.

## 6. Documentation Sync: update `README.md`

- Update the public work-store/worktree guidance to state the repaired behavior
  accurately: commands follow `work.path`, work artifacts are committed in the
  store repository, code worktree setup remains in the code repository, and a
  code worktree branch cannot carry lifecycle files owned elsewhere.
- Verify examples and command names against the final CLI behavior and run the
  documented-surface tests that cover README snippets.

## 7. Documentation Sync: update upcoming release notes

- Add a plain-language bug-fix entry to `docs/release-notes/upcoming.md` covering
  reliable inbox delivery, epic reconciliation, drift reporting, and worktree
  setup for externally stored work.
- Avoid internal function names and frame the outcome around configured-store
  users.

## 8. Documentation Sync: update the developer changelog

- Add a technical `Fixed` entry to `docs/changelogs/upcoming.md` naming
  configuration-aware discovery, store-repository Git routing, cross-node inbox
  writes, capability drift, and split-repository worktree persistence.

## 9. Documentation Sync: update the driving skills

- Update `skills/tcw-work/SKILL.md` and only the relevant on-demand references
  if necessary to teach the final external-store repository boundary for inbox,
  reconcile, and `start --worktree`, without bloating the router with rare
  details.
- Update `skills/tcw-capabilities/SKILL.md` so drift's completed-work lookup is
  explicitly configuration-aware and still degrades gracefully when no work
  component exists.
- Run the skill/documentation parity tests, including
  `tests/test_skill_lifecycle_parity.py` and
  `tests/test_documented_cli_surface.py`.

## 10. Reconcile the capability ledger

- Review and update the descriptions for
  `work/configure-the-work-store-location`, `work/manage-the-work-inbox`,
  `work/start-a-work-item`, `work/complete-a-work-item`, and
  `capabilities/detect-capability-drift` so they describe the final behavior and
  the unavoidable cross-repository worktree limitation without overstating
  atomicity.
- Keep the existing `configurable-work-store-location` feature link; no taxonomy
  entry is planned.
- Verify with `tcw capabilities check`, `tcw capabilities drift`, and
  `tcw validate --no-recurse`.

## Verification

- Run the full Python suite with `python -m pytest -q`.
- Run frontend/static checks affected by shared behavior or documentation:
  `pnpm exec tsc --noEmit`, `pnpm run lint`, `pnpm run test`, `pnpm run build`,
  and `pnpm run check:build`.
- Run `tcw taxonomy check`, `tcw capabilities check`, plain recursive
  `tcw validate`, and `git diff --check`.
- Manually inspect `git status --short` and the last TCW-created commit in both
  repositories of a two-repository smoke fixture. Confirm that no phantom
  `docs/work` tree exists, no work metadata remains staged, and no unrelated
  change was included.
- Confirm the production-code audit has an explicit disposition for every
  remaining `docs/work` literal and every direct Git operation touching a
  resolved work-store path; this semantic classification cannot be proven by
  the test suite alone.
- Record any pre-existing failure separately with the exact command and do not
  bulk-format unrelated files. In particular, use `pnpm exec tsc --noEmit` to
  isolate TypeScript rather than treating the `pnpm run typecheck` Prettier
  pre-check as authorization to reformat the repository.
