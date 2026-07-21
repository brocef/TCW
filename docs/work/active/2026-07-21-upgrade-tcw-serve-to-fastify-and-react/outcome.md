# Outcome — Upgrade `tcw serve` to Fastify and React

The runtime and client migration is fully implemented. Fastify is now the only
browser-facing listener, Python domain behavior remains in an authenticated private
sidecar, and the three-pane editor is implemented in TypeScript with React and React
Router Data Mode. The public command surface is unchanged; `tcw serve` alone now
requires Node.js 22.12 or newer.

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
- Ported the complete editor to native React components: deep-link/history routing,
  hierarchical trees and keyboard navigation, persisted expansion and pane sizes,
  text/status/tag/kind filters, Markdown rendering and live preview, every axis's
  create/edit flows, artifacts and sidecars, Work lifecycle actions, validation,
  dirty-navigation protection, and stale-write recovery.
- Replaced the global tree helper with a typed model and imported Markdown through
  the locked frontend graph. Removed all legacy `tcw/serve/static` browser assets,
  the Python static-file handler, the vendored renderer shim, and legacy JS tests.
- Added deterministic committed server/client bundles to Python package data. An
  installed wheel runs without pnpm, `node_modules`, or frontend source files.
- Updated the README, web capability description, release notes, changelog, and
  `tcw-plugin` installation/doctor guidance for the Node runtime and build model.
  `web` remains `Supported`; `web/editing` and `local-web-app` remain unchanged.

## Verification performed

- `python -m pytest -q` — **659 passed**. The total is lower only because the
  obsolete Python wrapper/static-serving tests were removed with the legacy client.
- `corepack pnpm install --frozen-lockfile`, `typecheck`, `lint`, `test`, `build`,
  and `check:build` — clean; Vitest/React Testing Library **10 passed**.
- Playwright against a throwaway TCW node — **10 passed**, covering all three axes,
  deep links, API/SPA separation, text and facet filters, Back/Forward, Work,
  Taxonomy and Capability creation/editing, Markdown preview, validation and dirty
  navigation, artifact and sidecar editing, stale-write recovery, start/complete,
  and drop.
- Live `tcw serve` smokes proved browser/API service and coordinated SIGTERM
  shutdown without orphaning either listener.
- An isolated wheel install proved that the packaged Node entry point, hashed Vite
  assets, and API work outside the checkout without pnpm or `node_modules`.
- `tcw capabilities check`, `tcw taxonomy check`, `tcw validate`, and
  `git diff --check` — clean.

## Deviations from the implementation plan

None. The temporary compatibility bridge used during migration was removed before
verification and is not present in source, package data, or built output.

## Closeout decisions still pending

- After user verification, resolve
  `2026-07-03-live-browser-test-pass-for-the-interactive-web-editor` as superseded
  by this item's automated and live-browser evidence.
- Keep the rich Markdown editor backlog item separate.
- Choose the merge/PR route and version bump before running `tcw work complete`.
