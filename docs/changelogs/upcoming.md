# Upcoming

Developer changelog for the next version. Technical and precise; grouped by
category, with commit hash ranges so entries trace back to source.

## Changed

<changes starting-hash="93f6688" ending-hash="40c9aba">
- Added a pinned pnpm/Vite/TypeScript workspace for Fastify 5, React 19, React
  Router Data Mode, Vitest, React Testing Library, ESLint, and Playwright.
- Refactored `tcw.serve` so an API-only `TcwServer` can require a per-process
  constant-time token, while the Python runtime checks Node 22.12+, launches the
  sidecar and packaged Fastify child, waits for explicit readiness, opens the
  browser only after readiness, and coordinates normal, error, interrupt, and
  SIGTERM shutdown.
- Added a loopback-only Fastify listener with CSP, Host/Origin enforcement, a
  1 MiB body limit, authenticated `/api/*` proxying, static asset serving, and
  SPA fallback.
- Rebuilt the three-pane editor as native TypeScript React components with
  React Router Data Mode, typed API transport, locked `marked` rendering,
  hierarchical navigation, axis-specific filters, create/edit/resource flows,
  lifecycle actions, dirty-state protection, and stale-write recovery.
- Removed the legacy global `app.js`, `tree.js`, vendored Markdown shim, Python
  static-file handler, and their package-data/test wiring. The tree model and
  tests now live in the TypeScript source graph.
- Added committed deterministic Node/client bundles to `tcw.serve` package data
  so wheel and pipx installs run without pnpm or `node_modules`.
- Added launcher version/authentication tests, Fastify tests for proxying and
  browser security, TypeScript component/model tests, and ten Playwright
  scenarios covering all axes and editing/lifecycle parity.
</changes>
