# Refined outcome — Upgrade `tcw serve` to Fastify and React

## Verification decision

The user directed the completed migration through closeout on 2026-07-22 and
authorized proceeding to the dependent Radix Themes implementation. The work is
accepted on the local `main` branch. No additional release is being cut at this
checkpoint; version `0.13.4` was already cut after the implementation landed.

## Closeout refinements

Final verification found that the committed browser bundle lagged the current
React source. The deterministic assets were rebuilt and committed so installed
distributions include the current staged-plan interface.

The full Python suite also exposed one plan-stage route regression: writing an
undeclared stage returned HTTP 422 instead of the specified HTTP 400. The PUT
route now treats that bounded-resource error as a bad request while retaining
HTTP 409 for stale revisions. Focused regression coverage passes.

Documentation Sync was re-evaluated. The existing README, release notes for the
migration release, web capability description, and `tcw-plugin` guidance already
describe the Fastify/React runtime and Node requirement. The new packaged-asset
and status-code fixes are recorded in the upcoming release note and developer
changelog; no further README or driving-skill edit is required.

## Final verification evidence

- TypeScript typecheck and ESLint passed.
- Vitest passed: 18 tests.
- Deterministic production build and committed-build checking passed after the
  packaged bundle refresh.
- Playwright passed: 11 browser parity tests using installed Google Chrome,
  including routing, filters, all axis edits, validation, dirty state,
  stale-write recovery, lifecycle actions, and Drop.
- Focused plan-stage API regression tests passed: 2 tests.
- Full pytest passed after the route correction.
- A live `tcw serve --no-open` smoke returned the strict
  `default-src 'self'` CSP, served the current hashed client assets, and returned
  Work API data; coordinated Ctrl-C shutdown exited cleanly.
- `tcw capabilities check`, `tcw taxonomy check`, `tcw validate`, and
  `git diff --check` pass at closeout.

An additional wheel rebuild was attempted with the current Python 3.14
environment, but its local pip lacks an importable `setuptools.build_meta`.
This is an environment limitation rather than a product failure; the original
isolated-wheel offline smoke remains recorded in `outcome.md`, and the refreshed
asset tree passed deterministic build checking plus the live packaged-server
smoke above.

## Closeout choices

- Complete this work item locally with resolution `done`.
- Keep the rich Markdown editor as separate backlog work.
- Leave the older live-browser-pass item as a separate backlog cleanup decision;
  the migration's Playwright evidence supersedes its technical verification gap.
- Proceed to the blocked Radix Themes work item after this completion transition.
