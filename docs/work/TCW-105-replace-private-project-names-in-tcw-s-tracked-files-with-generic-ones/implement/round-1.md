# Implement round 1 — TCW-105

Done by an agent in a separate worktree (commit `79c489c7` on its branch),
applied to `main` as `4c6636a1`.

## What was done

- **11 files.** Changed: the capability description's example paths,
  `docs/lifecycle/implementation.md` (the layout sketch is kept, under
  generic names, with no personal home path), `docs/release-notes/v2.5.1.md`
  and `docs/tcw-3.0-migration-log.md` (names only), TCW-76's implement round
  and TCW-100's spec, the `override_variable` docstring in
  `tcw/store/project.py`, and four test files.
- **Recomputed values.** The four cache keys in
  `test_the_cache_key_is_unchanged` were recomputed by calling
  `tcw.store.checkouts._cache_key`. The same call reproduced the old pinned
  value for the old URL.
- **Renames.** `test_the_proposit_migration_passes_through_no_blocked_state`
  became `test_the_workspace_migration_passes_through_no_blocked_state`, in
  the test file and in `tests/not_ported.py`.
- **Mutation checks.** Eight breaks to the cache key, `normalized_url` and
  `override_variable` were each caught by the changed tests. The renamed
  migration test is skipped through `not_ported.py`. With the skip removed,
  it fails identically before and after the change.
- **Left alone.** `proposit.atlassian.net` (kept by decision), and one
  `pnpm-lock.yaml` hit, which is the letters "PRPI" inside a hash.

## Test results

- In the worktree: `2 failed, 5151 passed, 119 skipped`. The two failures
  are the timing test `test_a_hanging_cli_is_abandoned_silently`, under
  machine load.
- On `main` after applying: `tests/test_store_provisioning.py`,
  `tests/test_project_registry.py` and `tests/test_upstream_projects.py`:
  274 passed, 38 skipped.
- `git grep` shows only the kept address.

## What the plan or spec got wrong

- They were written after the work. The item skipped spec and plan because
  it ran in parallel with other items' reviews.
- In the project registry test's docstring, the old names showed one name
  used both as a folder and as another project's ID. That coincidence is
  lost; the point the docstring makes (IDs and folder names differ) remains.

## Records changed

The example paths in
`docs/capabilities/work/declare-capability-changes-in-a-child-projects-ledger/description.md`.
