## Objective

Rebuild deterministic distributable assets, synchronize triggered
documentation, run the full verification matrix, and record evidence without
crossing the visual-verification or completion gates.

## Pre-stage checks

- Confirm the first three stages are verified and committed.
- Record the implementation hash range for the developer changelog.
- Invoke Documentation Sync; cross-check the current version against versioned
  note files and reassess README, release-note, changelog, and driving-skill
  triggers.

## Implementation

- Rebuild and inspect the committed `tcw serve` client bundle.
- Document developer formatting commands in `README.md`.
- Add plain-language tree/editor improvements to
  `docs/release-notes/upcoming.md` and technical architecture, formatting,
  testing, and generated-asset details with hash ranges to
  `docs/changelogs/upcoming.md`.
- Keep driving skills unchanged unless final inspection discovers a real CLI,
  lifecycle, model, or agent-workflow change.
- Write `outcome.md` with implementation, verification, deviations, and the
  pending capability/user-verification state.

## Post-stage checks

- Run `pnpm prettify:check`, `pnpm typecheck`, `pnpm lint`, `pnpm test`,
  `pnpm test:e2e`, `pnpm build`, and `pnpm check:build`.
- Run `python -m pytest`, `tcw capabilities check`, `tcw taxonomy check`,
  `tcw validate`, and `git diff --check`.
- Inspect deterministic asset and documentation diffs and commit the stage with
  `outcome.md`.
- Stop for user visual verification. Do not reconcile capability wording,
  complete the item, or cut a release.
