# Implementation plan

1. Update the generated Feature requests in `web/e2e/parity.spec.ts` to include
   the existing `react-vocabulary` reference. Verify the full serial Playwright
   suite passes and reaches every scenario.
2. Run `python -m pytest -q`, `pnpm test`, `pnpm test:e2e`, and `pnpm lint`.
   Confirm every Playwright scenario executes rather than being skipped after a
   serial-suite failure.
3. Re-evaluate Documentation Sync against the finished diff. This test-fixture
   correction is expected not to fire `Public-API`, `Any-Code-Change`, or
   `Skill-Driven-Component`; therefore no README, release-note, changelog, or
   driving-skill update is planned.

## Verification

No manual verification is required beyond observing the complete command exit
statuses and test counts. Playwright must run where loopback socket binding is
permitted.
