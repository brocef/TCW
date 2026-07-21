# Upcoming

Developer changelog for the next version. Technical and precise; grouped by
category, with commit hash ranges so entries trace back to source.

## Changed

<changes starting-hash="1538701" ending-hash="1538701">
- Added reusable typed client-side reference ranking, highlighting, candidate
  scoping, and accessible single/multi combobox controls across Work, Taxonomy,
  and Capability edit fields.
- Added storage-neutral `ValidationTarget` selection to `tcw.validate.validate`
  and optional object identifiers to each store's `check()` contract, with
  filesystem-private bounded-resource resolution.
- Replaced component-wide post-write checks with safe object-scoped validation
  after web creates, structured edits, lifecycle artifact saves, and sidecar
  saves; committed mutations return warnings even if validation raises.
- Added Python, Vitest, React component, and Playwright coverage for scoped
  findings, unrelated-object isolation, ranking, highlighting, accessibility,
  canonical selection, warning display, and warning clearing.
</changes>

<changes starting-hash="93f6688" ending-hash="17fbd5a">
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
- Fixed Taxonomy and Capability tree-item wrappers so their selectable buttons
  flex across the available list-column width and nested rows use the same 8px
  vertical spacing as Work items, with browser geometry assertions.
- Moved the shared React create control above the ARIA object tree for all three
  axes and added component coverage that locks down the DOM order.
</changes>
