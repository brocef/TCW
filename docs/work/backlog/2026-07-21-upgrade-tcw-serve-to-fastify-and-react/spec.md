# Upgrade `tcw serve` to Fastify and React

## Capability changes

- `web` changes in wording only: it remains `Supported`, and its description
  must state that `tcw serve` requires Node.js 22.12 or newer.
- `web/editing` is a parity acceptance surface but is otherwise unchanged. The
  migration must preserve all existing browser editing workflows before the
  implementation can be considered complete.
- The `local-web-app` taxonomy Feature remains the correct registered feature.
  No vocabulary or Feature change is required.

## Problem

The current `tcw serve` implementation combines a 1,227-line Python
`BaseHTTPRequestHandler` API/static server with a 3,271-line untyped browser
application in `tcw/serve/static/app.js`. It has accumulated a broad interactive
surface, but its manual request dispatch, state management, and DOM rendering
make continued parity-preserving development difficult.

Move the browser-facing runtime to Fastify and the client to React without
moving TCW domain behavior out of Python or changing what users can do.

## Goals

1. Preserve the public `tcw serve` command and its `--port` and `--no-open`
   options, including automatic descendant-board aggregation.
2. Preserve every existing `/api/*` contract and browser workflow.
3. Isolate the Python API as an authenticated, private sidecar while Fastify is
   the sole browser-facing listener on `127.0.0.1`.
4. Rebuild the client in TypeScript with React and React Router Data Mode while
   retaining the existing three-pane information architecture and styling.
5. Make builds deterministic and installations self-contained: developers use
   pnpm, while released users need only Python and Node.js 22.12 or newer.
6. Establish automated browser parity coverage that subsumes the outstanding
   manual live-browser verification item.

## Non-goals

- A visual redesign, rich-text editor, hosted server, multi-user service, SSR,
  or React Server Components.
- New public CLI options, API routes, capability entries, taxonomy entries, or
  abstract store operations.
- Reimplementing `WorkStore`, `TaxonomyStore`, `CapabilitiesStore`, validation,
  lifecycle transitions, revision calculation, or graph resolution in
  TypeScript.
- Requiring pnpm, `node_modules`, network access, or a frontend build in an
  installed wheel, pipx environment, or plugin installation.
- Adopting Next.js. Its standalone deployment output is viable, but its broader
  rendering and runtime conventions add no needed value to this local
  client-rendered application.

## Current state

- `tcw/cli.py` owns the public parser, validates the project graph, and invokes
  `tcw.serve.serve(..., include_descendants=True)`.
- `tcw/serve/__init__.py` owns static serving, SPA fallback, `/api/*` dispatch,
  store construction, security checks, JSON parsing, and process lifetime.
- `tcw/serve/static/` contains the handwritten app, tree helper, stylesheet,
  vendored Markdown renderer, and HTML shell. `pyproject.toml` packages
  `static/*` under `tcw.serve`.
- `tests/test_serve.py`, `tests/test_serve_write.py`,
  `tests/test_serve_descendants.py`, and `tests/test_serve_resolve.py` exercise
  the API and server contract. `tests/tree.test.mjs` and
  `tests/test_tree_js.py` cover the standalone tree helper.
- The browser surface includes deep links and history, independent/resizable
  panes, hierarchical navigation, text/category/status filters, Markdown
  preview, Work/Taxonomy/Capabilities create and edit flows, Work lifecycle
  actions, validation feedback, dirty-navigation protection, and HTTP 409
  stale-write recovery.

## Runtime and process architecture

### Public Python launcher

`tcw serve` remains a Python CLI command. Before binding either server it must:

1. resolve and validate the TCW node as it does today;
2. locate `node`, run `node --version`, parse the version without shelling out,
   and fail before starting children unless it is at least 22.12.0;
3. choose a cryptographically random per-process bearer token;
4. start an API-only Python sidecar on an OS-assigned loopback port;
5. start the packaged Node server with narrowly named environment variables
   carrying the sidecar origin and token plus the requested public port;
6. wait for a machine-readable readiness message from the Node child before
   printing the public URL or opening the browser.

The launcher must report missing/old Node, public port collisions, sidecar
startup errors, malformed or timed-out readiness, and premature child exits in
plain actionable language. SIGINT/KeyboardInterrupt, Python exceptions, and a
crash of either child/server must trigger coordinated shutdown without leaving
an orphaned process or listener. Normal Ctrl-C returns success; startup/runtime
failures return non-zero.

Environment variable names must use a TCW-specific prefix and are a private
launcher/child protocol, not a supported user configuration surface. The token
must not appear in the browser bundle, browser responses, command output, or
logs.

### Python API sidecar

Refactor the current handler rather than rewrite its domain behavior. The
sidecar binds only to an ephemeral `127.0.0.1` port and serves `/api/*` only. It
must reject every request that lacks the exact per-process token, including GET
requests, before routing or reading a body. Static files and SPA fallbacks are
not available on this listener.

The refactor must preserve API paths, methods, JSON bodies/envelopes, status
codes, content types, 1 MiB body limit, revision tokens, stale-write behavior,
validation warnings, open-artifact behavior, descendant addressing, and store
construction semantics. Existing Python contract tests remain authoritative and
should be adapted to exercise the API-only handler directly.

Authentication is defense in depth against other local processes accidentally
or opportunistically reaching the random loopback port; it does not turn the
sidecar into a remotely supportable service.

### Fastify server

The packaged Node entry point is the only listener reachable by the browser. It
must:

- bind only to `127.0.0.1` on the user-selected port;
- enforce the existing loopback Host/Origin policy for browser/API traffic and
  reject DNS-rebinding and cross-origin attempts;
- enforce a 1 MiB request body limit before proxying;
- serve only committed Vite production assets, with correct content types and
  a history-API fallback to `index.html` for non-API routes;
- preserve `Content-Security-Policy: default-src 'self'` unless implementation
  proves that a narrower explicit directive set is required;
- proxy `/api/*` method, path, query, headers needed by the contract, body,
  response status, content type, and body faithfully to the sidecar;
- inject sidecar authentication server-side and never forward it to the client;
- translate an unavailable sidecar into a stable non-success response without
  exposing private connection details.

Fastify v5 is suitable because its support line covers Node 22. React Router
Data Mode is suitable because it adds loaders, actions, pending states, and
navigation blocking while leaving bundling and server abstractions under this
project's control. Vite's documented runtime floor supplies the exact Node
22.12 minimum used by this item.

## Client architecture and parity

Create a Vite TypeScript React client using React Router Data Mode
(`createBrowserRouter`/`RouterProvider`). Route loaders and actions may call the
compatible `/api/*` surface, but API types should be explicit and browser code
must not encode store rules.

Port the current UI rather than redesign it. Acceptance requires parity for:

- routes, deep links, Back/Forward, tab navigation, and `tcw://` link handling;
- the three-pane shell, independent scrolling, both resizers, tree expansion,
  selection, and automatic ancestor expansion;
- text filters, Work tag match-any filtering, Work status toggles, and Taxonomy
  kind filtering;
- Work creation/editing, artifacts, `capabilities.yaml`, sidecars, start,
  complete, drop, DoD acknowledgments, blocker handling, and copy-slug action;
- Taxonomy Vocabulary/Feature creation/editing and check feedback;
- Capability creation/editing, collections, inheritance/origin display, and
  check feedback;
- raw Markdown editing and preview, validation errors/warnings, toasts,
  dirty-state navigation/unload protection, and 409 conflict recovery that
  retains the draft.

Import the Markdown renderer through the locked pnpm dependency graph. Runtime
assets must remain offline and CSP-compatible; no CDN or runtime package fetch
is allowed.

## Source, build, and distribution layout

- Add a root `package.json`, `pnpm-lock.yaml`, Node engine declaration, and
  scripts for type checking, linting, unit tests, browser tests, and builds.
- Place maintainable Node server and React client TypeScript sources in an
  explicit web source tree rather than under generated Python package data.
- Emit deterministic production server/client artifacts into a dedicated
  `tcw.serve` package-data tree. Generated output is committed and reviewed.
- Update `pyproject.toml` so sdists and wheels include all generated assets and
  the Node entry point, including hashed/nested Vite assets.
- Add a deterministic check that a clean build produces no diff. Exclude
  `node_modules`, Playwright browser caches, coverage, and transient Vite output
  from distributions and version control.

Installed execution must resolve assets through Python package resources, not
the checkout root or current working directory. A wheel/pipx-style smoke test
must prove `tcw serve` can start after source files, pnpm, and `node_modules` are
absent.

## Compatibility and security acceptance criteria

1. `tcw serve`, `--port`, and `--no-open` behave as before; all non-serve TCW
   commands work without Node installed.
2. Missing Node and Node versions below 22.12 fail before listeners/children
   remain active and tell the user how to correct the prerequisite.
3. The existing Python API contract suite passes against the sidecar with no
   intentional contract changes.
4. Direct sidecar requests without the private token fail; authenticated proxy
   requests retain exact API behavior.
5. Only Fastify accepts browser traffic, only on loopback, with static/SPA,
   CSP, body-size, Host, and Origin protections verified.
6. Ctrl-C, launch failures, readiness failures, port collisions, and child
   crashes leave no orphan process or bound port.
7. React parity tests cover every Work, Taxonomy, Capabilities, navigation,
   filtering, editing, Markdown, validation, dirty-state, and stale-write flow
   listed above.
8. The app runs offline from a built wheel with Node 22.12+, without pnpm or
   `node_modules`.
9. No abstract store interface changes and no TypeScript duplication of Python
   store or lifecycle rules are introduced.

## Testing requirements

- Preserve and adapt the Python API contract suite; add focused tests for
  sidecar authentication and API-only behavior.
- Add Python launcher/process tests for version parsing, missing/old Node,
  startup, port collision, readiness timeout/malformed output, child crash,
  interrupt handling, and coordinated shutdown.
- Add Fastify tests for static assets, SPA fallback, CSP, 1 MiB limits,
  Host/Origin rejection, proxy fidelity, sidecar failure, and absence of token
  leakage.
- Add TypeScript type checking and linting plus Vitest/React Testing Library
  tests for components, loaders/actions, routing, filters, editor state, and
  conflict handling.
- Add Playwright tests against throwaway TCW nodes for the full parity matrix,
  including cross-process stale-write creation.
- Run a live manual smoke and a built-wheel isolated-install smoke as final
  system checks.

## Documentation requirements

The implementation changes public runtime requirements and behavior-affecting
code, so Documentation Sync predicts all applicable entries will fire:

- update `README.md` with Node 22.12+, installed-vs-developer prerequisites,
  unchanged command usage, offline packaged-build behavior, and troubleshooting;
- update `docs/capabilities/web/description.md` with the Node prerequisite while
  leaving its `Supported` status unchanged;
- add plain-language `docs/release-notes/upcoming.md` coverage;
- add a technical `docs/changelogs/upcoming.md` entry with the implementation
  commit hash range;
- update `skills/tcw-plugin/SKILL.md` and its relevant installation/doctor
  references so agents check Node only for `tcw serve` and understand that pnpm
  is developer-only.

The `tcw-plugin` skill is the driving skill for installation/doctor behavior;
`tcw-work`, `tcw-capabilities`, and `tcw-taxonomy` do not change unless the
implementation reveals an actual workflow change.

## Related work and closeout

- `2026-07-03-live-browser-test-pass-for-the-interactive-web-editor` is absorbed
  by the Playwright acceptance suite. At closeout, propose completing it with
  resolution `superseded` and point to this item's verification evidence; do not
  change it during planning.
- `2026-07-02-add-a-vendored-rich-markdown-editor-to-the-local-web-app` remains
  separate and in scope only after this parity migration lands.

## Risks and mitigations

- **Contract drift:** keep existing API tests authoritative and add proxy
  fidelity tests before porting UI flows.
- **Security regression across two listeners:** require sidecar authentication,
  keep both listeners loopback-only, and test every trust boundary explicitly.
- **Process leaks and flaky startup:** use an explicit readiness protocol,
  bounded startup timeout, supervised lifetimes, and deterministic teardown.
- **UI parity gaps hidden by a rewrite:** build a route/workflow matrix from the
  current app and require Playwright coverage before removing legacy assets.
- **Generated artifacts drifting from source:** pin the pnpm graph and require a
  clean rebuild check in verification and CI.
- **Packaging works only in a checkout:** exercise wheel installation in an
  isolated directory with development inputs removed.

## References

- [Vite compatibility note](https://vite.dev/guide/) documents Node 20.19+ or
  22.12+ for current Vite.
- [Fastify v5 LTS](https://fastify.dev/docs/v5.0.x/Reference/LTS/) lists Node 20
  and 22 for the v5 line.
- [React Router modes](https://reactrouter.com/start/modes/) distinguishes Data
  Mode's data APIs and architectural control from Framework Mode.
- [Next.js standalone output](https://nextjs.org/docs/app/api-reference/config/next-config-js/output)
  confirms the considered deployment option; it remains out of scope here.
