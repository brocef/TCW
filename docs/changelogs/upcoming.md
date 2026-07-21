# Upcoming

Developer changelog for the next version. Technical and precise; grouped by
category, with commit hash ranges so entries trace back to source.

## Changed

<changes starting-hash="93f6688" ending-hash="a9d52e8">
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
- Mounted the established three-pane editor shell under React Router while
  retaining the existing parity-tested editing implementation as packaged
  compatibility assets.
- Added committed deterministic Node/client bundles to `tcw.serve` package data
  so wheel and pipx installs run without pnpm or `node_modules`.
- Added launcher version/authentication tests and Fastify tests for proxying,
  static/SPA behavior, CSP, origin rejection, and request-size enforcement.
</changes>
