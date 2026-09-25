# Make the web app's end-to-end tests pass and their theme screenshot stable

`pnpm test:e2e` (Playwright, `web/e2e/parity.spec.ts`) does not pass on `main`.
Two tests fail the same way before and after the 2026-09-24 dependency updates:
"searches references and surfaces targeted validation warnings" (a
`toContainText`), and "edits lifecycle artifacts and preserves a draft across a
stale write" (the saved spec reads `# spec`, not `Updated specification`). The
theme test's screenshot comparison passes on some runs and fails on others.
CI does not run these tests, so nothing noticed.

## Origin

Found while verifying the Dependabot dependency updates; the user asked for them
to be fixed.

## References

- the completed item 2026-09-24-update-the-web-app-s-npm-dependencies-to-clear-the-open-dependabot-alerts (commit 03fc0728) — where the failures were first recorded
