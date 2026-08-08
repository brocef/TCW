# Implementation outcome

Implemented configurable external per-project filesystem work stores while
preserving the owning project's canonical ID, lifecycle policy, hooks,
capabilities, and code-worktree repository.

## Delivered

- `FsWorkStore` now separates the owning node root, configured work root, and
  work-store Git root. Default, relative, absolute, and symlinked locations use
  the same factory; broken, malformed, non-store, and configured non-Git targets
  fail with `work.path` diagnostics.
- Work discovery, qualified references, recursion, validation, web access,
  staging, transitions, resolved-status ignores, and transition commits route
  through the configured store. Relative configured paths are re-anchored to a
  linked worktree's primary checkout.
- `tcw work init --path` and `tcw init --work-path` scaffold external stores,
  preserve existing work configuration, write target-relative ignore rules,
  and replace only an exactly pristine generated default scaffold.
- Validation rejects registered projects that resolve to one physical work
  root.
- Starts now record claimant identity and UTC time, publish claims with a
  single-winner private rename, report contention, support explicit takeover
  and interrupted-claim recovery, clear claim metadata when leaving active, and
  show claim metadata in CLI/API read surfaces.
- README, release notes, changelog, capability records, taxonomy, and the
  `tcw-work` skill/reference guidance were updated.

## Verification

- `python -m pytest -q`: **1180 passed**.
- Focused external/claim/work suite after interrupted-recovery follow-up:
  **161 passed**.
- `pnpm exec tsc --noEmit`, `pnpm run lint`, `pnpm run test` (**50 passed**),
  `pnpm run build`, and `pnpm run check:build`: passed.
- `tcw taxonomy check`, `tcw capabilities check`, recursive `tcw validate`, and
  `git diff --check`: passed.
- `pnpm run typecheck` stopped in its Prettier pre-check because the repository
  already contains a broad set of formatting differences (61 files, mostly
  untouched lifecycle/plugin documents). The underlying TypeScript check passed
  when run directly. No bulk formatting rewrite was applied.

Completion and any version cut remain pending user acceptance.
