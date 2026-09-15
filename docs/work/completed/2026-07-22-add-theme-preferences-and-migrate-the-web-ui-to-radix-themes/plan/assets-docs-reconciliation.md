## Objective

Finalize deterministic distributable assets, synchronize all triggered
documentation, run the complete verification matrix, and record implementation
evidence without crossing the user-verification or completion gates.

## Pre-stage checks

- Confirm all three client conversion stages are verified and committed.
- Note the implementation start commit and current commit for the changelog hash
  range.
- Invoke Documentation Sync and verify the expected README, release-note, and
  changelog triggers; re-evaluate whether any driving-skill behavior changed.

## Implementation

- Rebuild and commit deterministic client/server package assets, including
  Radix CSS/icons and the early theme initializer.
- Update `README.md` with the Settings gear location, Light/Dark/System choices,
  System default, and current-browser persistence.
- Add plain-language user coverage to `docs/release-notes/upcoming.md` and
  technical dependency/theme/initializer/build details with the implementation
  hash range to `docs/changelogs/upcoming.md`.
- Keep driving skills unchanged unless final inspection finds an actual CLI,
  lifecycle, installation, or agent-workflow delta.
- Write `outcome.md` with changes, verification evidence, deviations, retained
  custom behavior/CSS, documentation evaluation, capability state, and any
  follow-ups. Keep `web/choose-a-theme` Missing pending visual approval.

## Post-stage checks

- Run `pnpm typecheck`, `pnpm lint`, `pnpm test`, `pnpm test:e2e`,
  `pnpm build`, and `pnpm check:build`.
- Run full pytest, `tcw capabilities check`, `tcw taxonomy check`,
  `tcw validate`, and `git diff --check`.
- Smoke a live `tcw serve`, including first paint and both themes, and test an
  isolated installed wheel offline without source, pnpm, `node_modules`, or
  network access.
- Inspect deterministic generated-asset and documentation diffs, then commit
  them with `outcome.md` as the implementation outcome checkpoint.
- Stop for user visual verification and refinements. Do not write
  `refined-outcome.md`, set the capability Supported, run `tcw work complete`,
  or cut a release until the user explicitly approves those closeout steps.
