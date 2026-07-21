# Outcome — Upgrade `tcw serve` to Fastify and React

The runtime migration is implemented and verified as a parity-first compatibility
release candidate. Fastify is now the only browser-facing listener, Python domain
behavior remains in an authenticated private sidecar, and a Vite-built React Router
shell hosts the established three-pane editor. The public command surface is
unchanged; `tcw serve` alone now requires Node.js 22.12 or newer.

## What changed

- Added a pinned pnpm workspace with TypeScript, ESLint, Vite, Fastify 5, React 19,
  React Router Data Mode, Vitest, React Testing Library, and Playwright.
- Refactored the Python server so it can run as an API-only sidecar on an ephemeral
  loopback port. Every private request requires a cryptographically random,
  constant-time-checked process token; static and SPA routes are unavailable there.
- Added a Python launcher that checks Node before startup, starts both runtimes,
  passes the private origin and token through TCW-prefixed environment variables,
  waits for explicit readiness, opens the browser afterward, detects either runtime
  exiting unexpectedly, and coordinates interrupt, error, and SIGTERM shutdown.
- Added a loopback-only Fastify server with strict CSP, Host/Origin validation, a
  1 MiB request limit, authenticated `/api/*` proxying, static assets, and SPA
  fallback.
- Added a React Router Data Mode application shell and bundled the established
  editor implementation, styling, tree helper, and Markdown behavior as offline
  compatibility assets beneath it.
- Added deterministic committed server/client bundles to Python package data. An
  installed wheel runs without pnpm, `node_modules`, or frontend source files.
- Updated the README, web capability description, release notes, changelog, and
  `tcw-plugin` installation/doctor guidance for the Node runtime and build model.
  `web` remains `Supported`; `web/editing` and `local-web-app` remain unchanged.

## Verification performed

- `python -m pytest -q` — **664 passed**.
- `corepack pnpm install --frozen-lockfile`, `typecheck`, `lint`, `test`, `build`,
  and `check:build` — clean; Vitest/React Testing Library **4 passed**.
- `node --test tests/tree.test.mjs` — **23 passed**.
- Playwright against a throwaway TCW node — **3 passed**, covering all three axes,
  navigation, filtering, API/SPA route separation, and deep-link fallback.
- Live `tcw serve` smokes proved browser/API service and coordinated SIGTERM
  shutdown without orphaning either listener.
- An isolated wheel install proved that the packaged Node entry point, hashed Vite
  assets, and API work outside the checkout without pnpm or `node_modules`.
- `tcw capabilities check`, `tcw taxonomy check`, `tcw validate`, and
  `git diff --check` — clean.

## Deviations from the implementation plan

- The client is not yet a full component-by-component TypeScript rewrite. React and
  React Router own the entry point and route synchronization, but the established
  parity-tested editor remains packaged JavaScript loaded by the React shell. This
  avoided a high-risk simultaneous rewrite of every editing and lifecycle workflow,
  but leaves a deliberate compatibility bridge instead of completing phases 5–6 as
  originally specified.
- The new Playwright suite is a browser-facing parity smoke, not the exhaustive
  workflow matrix specified for Work, Taxonomy, Capabilities, Markdown, validation,
  dirty-state, and cross-process stale-write behavior. Those behaviors retain their
  existing implementation and Python/API coverage, but do not each have a new
  Playwright scenario.
- Legacy browser assets and their tree tests remain in the distribution because the
  compatibility bridge still uses them. They were not removed or replaced with
  equivalent TypeScript modules.

These deviations are material scope decisions and require explicit user acceptance
before closeout. If exact conformance to the original React-port and browser-test
requirements is required, the item should remain active for that additional work.

## Closeout decisions still pending

- Decide whether to accept the compatibility bridge or require the full TypeScript
  React port and exhaustive Playwright matrix before completion.
- If accepted, resolve
  `2026-07-03-live-browser-test-pass-for-the-interactive-web-editor` as superseded
  by this item's automated and live-browser evidence.
- Keep the rich Markdown editor backlog item separate.
- Choose the merge/PR route and version bump before running `tcw work complete`.
