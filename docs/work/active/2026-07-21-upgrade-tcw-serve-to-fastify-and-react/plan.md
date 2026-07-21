# Implementation plan

## Delivery strategy

Migrate behind stable boundaries in this order: freeze the existing contract,
extract and authenticate the Python API, add the supervised Fastify listener,
port the client under automated parity coverage, then switch packaging and
remove the legacy browser assets. Keep the existing server/client usable until
the replacement passes the same contract and workflow matrix.

The first implementation action in a future session is:

```sh
tcw work start 2026-07-21-upgrade-tcw-serve-to-fastify-and-react
```

Commit that transition by itself before changing code. Do not run it during this
planning pass.

## Phase 1: Freeze contracts and establish the web workspace

1. Inventory every route/method/status/envelope in `tcw/serve/__init__.py` and
   every user workflow in `tcw/serve/static/app.js`. Turn the inventory into a
   checked test matrix so later phases cannot silently narrow parity.
2. Restructure existing server tests around reusable API-contract fixtures that
   can target the current handler, authenticated sidecar, and Fastify proxy
   without duplicating assertions.
3. Add a root pnpm workspace with pinned `packageManager`, `engines.node`, and a
   committed `pnpm-lock.yaml`.
4. Add maintainable TypeScript source roots for the Fastify server and React
   client, with shared API transport types limited to wire contracts rather
   than Python store/domain types.
5. Configure TypeScript, ESLint, Vitest, React Testing Library, and Playwright.
   Add root scripts with narrow names for `typecheck`, `lint`, unit tests,
   Playwright tests, production build, and committed-build verification.
6. Update `.gitignore`/test configuration for `node_modules`, coverage,
   Playwright caches/results, and transient build directories without ignoring
   the committed distribution output.
7. Add CI-equivalent local checks that can run Python-only tests without pnpm
   and web-development checks with the locked pnpm graph.

Expected touch points:

- `package.json`, `pnpm-lock.yaml`, `tsconfig*.json`, ESLint/Vitest/Playwright
  configuration
- a new `web/server/` and `web/client/` source tree (final names may follow the
  established root layout discovered during implementation)
- `.gitignore`, `pyproject.toml`, `tests/test_serve*.py`

Gate: the existing Python suite remains green; the new web toolchain installs
from the lockfile and empty starter typecheck/lint/test/build commands pass.

## Phase 2: Extract the authenticated Python API sidecar

1. Split `tcw/serve/__init__.py` into cohesive modules for API routing/response
   behavior, sidecar HTTP adaptation, process launching, and package-resource
   lookup. Keep store construction and all TCW mutations in Python.
2. Preserve the API handler's existing route precedence, percent-decoding,
   JSON parsing, content types, response envelopes, validation warnings,
   revision semantics, status codes, and 1 MiB limit.
3. Remove static-file and SPA fallback responsibilities from the sidecar.
4. Add a required token check at the earliest request boundary for every
   method. Use constant-time comparison where practical and return a uniform
   rejection without revealing expected credentials.
5. Bind the sidecar to `127.0.0.1:0`, capture the assigned port, and expose a
   small in-process lifecycle handle that the launcher can stop deterministically.
6. Keep direct sidecar construction available to Python tests without exposing
   it as a public CLI or supported server mode.
7. Adapt the full existing API suite to send authentication and prove that the
   extraction made no intentional contract change.

Expected touch points:

- `tcw/serve/__init__.py` reduced to exports/compatibility shims as appropriate
- new Python modules under `tcw/serve/` for API, sidecar, and launcher concerns
- `tests/test_serve.py`, `tests/test_serve_write.py`,
  `tests/test_serve_descendants.py`, `tests/test_serve_resolve.py`
- new focused sidecar/security tests

Gate: the complete pre-migration API contract passes against the authenticated
sidecar; unauthenticated requests of every supported method fail; non-API and
static requests are unavailable on the sidecar.

## Phase 3: Build the Fastify browser-facing server

1. Create a Fastify v5 application factory whose inputs are the public host/port,
   built asset directory, private sidecar origin, and private token.
2. Bind exclusively to `127.0.0.1`; validate the selected public port and report
   collisions through the readiness/error protocol.
3. Implement loopback Host and Origin enforcement equivalent to the current
   mutating-request protection and apply the appropriate check before proxying.
   Test absent, malformed, foreign, IPv4 loopback, and supported localhost forms.
4. Configure a 1 MiB body limit and make over-limit behavior compatible with the
   existing API response contract.
5. Proxy every `/api/*` request to the sidecar without transforming successful
   or error bodies. Preserve method, encoded path/query, relevant request
   headers, status, response content type, and bytes; inject the private token
   only on the upstream request.
6. Serve the committed Vite asset manifest/output with correct content types,
   immutable caching only for hashed assets, and `index.html` fallback for
   non-API application routes. Unknown `/api/*` routes must remain API 404s.
7. Emit the strict CSP and other existing security headers from all relevant
   browser responses. Keep `default-src 'self'`; document and test any necessary
   directive refinement.
8. Emit exactly one machine-readable readiness record only after the public
   listener is accepting requests. Send diagnostics to stderr and never include
   the sidecar token or private origin in browser-visible responses.
9. Handle sidecar unavailability and shutdown without hanging requests or
   leaking private connection details.

Expected touch points:

- Node server modules and tests under the new web source tree
- production server bundle under `tcw/serve/` package data
- Python package-resource/launcher glue

Gate: Fastify tests pass for assets, SPA fallback, API 404 separation, CSP, body
limits, Host/Origin rejection, proxy byte/status fidelity, upstream failure, and
token non-disclosure. Direct sidecar access remains rejected.

## Phase 4: Supervise startup, readiness, and shutdown from Python

1. Add a small Node discovery/version parser that invokes an argv list (never a
   shell), accepts Node 22.12.0 or newer, and reports the discovered version on
   failure. Do not perform this check for any command other than `tcw serve`.
2. Keep node resolution and project-graph validation before child startup.
3. Generate the per-process secret with Python's cryptographic randomness and
   pass only the private sidecar origin/token and public bind settings through
   narrowly prefixed TCW environment variables. Preserve the rest of the child
   environment needed to locate Node normally.
4. Launch the sidecar first, then the packaged Node entry point. Consume stdout
   until the readiness record arrives, with a bounded timeout and maximum line
   size; treat malformed output or early exit as startup failure.
5. Print the existing `Serving TCW at http://127.0.0.1:<port>/` result and open
   the browser only after readiness. Preserve `--no-open` exactly.
6. Supervise both lifetimes. On KeyboardInterrupt, termination signal, Python
   error, readiness failure, Node crash, or sidecar failure, stop accepting new
   work and terminate/join both sides in a bounded order, escalating only when
   graceful shutdown times out.
7. Return zero for normal Ctrl-C shutdown and non-zero for actionable startup or
   runtime failure. Avoid tracebacks for expected prerequisite/port errors.
8. Preserve dependency injection seams for tests so fake Node executables and
   child processes do not require real network listeners.

Expected touch points:

- `tcw/cli.py`
- Python launcher/process modules under `tcw/serve/`
- new launcher and lifecycle tests under `tests/`

Gate: focused tests cover missing Node, unparsable output, old versions, minimum
and newer versions, sidecar failure, public port collision, readiness success,
timeout/malformed readiness, early/late child crash, browser-open timing,
Ctrl-C, cleanup, and exit codes. Non-serve commands pass with `node` unavailable.

## Phase 5: Port the React shell, routing, and read workflows

1. Create the Vite React TypeScript entry point and React Router Data Mode route
   tree for the existing Taxonomy, Capabilities, Work, detail, descendant, and
   deep-link URL shapes.
2. Add a typed fetch layer that treats the Python response as external data,
   reports non-JSON failures safely, and preserves status information needed for
   409 handling. Do not reproduce domain validation in the browser.
3. Port the top bar, tabs, three-pane shell, independent scroll regions,
   list/detail and editor/preview resizers, toast/error surfaces, and responsive
   behavior using the current CSS as the visual baseline.
4. Port the pure hierarchical tree behavior and its existing fixture coverage:
   folder nodes, work parent/child nesting, expansion, selected-ancestor reveal,
   stable ordering, and descendant project qualification.
5. Port route loaders and read views for all axes plus `tcw://` resolution and
   in-app navigation. Confirm reload, Back, Forward, and copied deep links.
6. Port filtering: text plus ancestors, Work tags with match-any semantics,
   Work backlog/active/completed toggles and defaults, and Taxonomy kind choices.
7. Port Markdown display through a package dependency bundled by Vite and keep
   generated output compatible with the CSP and offline requirement.

Expected touch points:

- React client components, routes, styles, API types/client, and unit tests
- current `tcw/serve/static/style.css` as a migration input
- existing tree JS tests replaced by equivalent TypeScript tests once parity is
  proven

Parallelization: after the typed fetch/route skeleton and shared shell land,
read-only axis views and tree/filter component tests can be ported independently.

Gate: unit/component tests and the first Playwright tranche cover all routes,
navigation history, tree behavior, filters, resizers, Markdown rendering, and
read-only display across Work, Taxonomy, and Capabilities.

## Phase 6: Port editing and lifecycle workflows

1. Implement shared typed form/error primitives without flattening the
   axis-specific request bodies or validation messages.
2. Port Work creation with every current field: title, priority, effort,
   complexity, tags, blockers, parent, and initiative.
3. Port Work core/body editing, lifecycle artifacts, discovered sidecars, and
   `capabilities.yaml`, preserving revision tokens and resource switching.
4. Port Work start, forced-start handling, complete modal acknowledgments,
   capability reconciliation reminder, blocker handling, drop/delete, and
   copy-slug action.
5. Port Taxonomy Vocabulary/Feature creation/editing, relation fields, and
   post-write check failures/warnings.
6. Port Capability creation (including existing collections), metadata/body
   editing, inheritance/origin display, and post-write check failures/warnings.
7. Port the raw Markdown textarea/live-preview experience without adding the
   deferred rich editor.
8. Implement one dirty-state model across links, tabs, browser history,
   selection changes, resource changes, and unload. Use React Router's Data Mode
   blocking APIs where applicable and retain the current confirmation behavior.
9. Implement 409 recovery for core and resource writes: retain the draft, fetch
   the server version, show conflict state, and allow the same recovery choices
   as the legacy app.
10. Preserve focus, keyboard, labels, roles, live regions, and accessible modal
    behavior during the port.

Parallelization: Work, Taxonomy, and Capability form ports can proceed in
parallel once shared API/form/dirty-state primitives stabilize. Lifecycle and
conflict flows should remain a single integration stream because they share
navigation and revision state.

Gate: Vitest/React Testing Library tests cover forms and state transitions;
Playwright covers every workflow in the spec against isolated throwaway nodes,
including validation failures, dirty navigation, and a real cross-process stale
write.

## Phase 7: Commit deterministic builds and switch packaging

1. Configure the client and server production builds to emit into a staging
   directory, then atomically replace the committed `tcw.serve` package-data
   output only after a successful full build.
2. Ensure asset references and the server entry point are independent of the
   checkout path and current working directory.
3. Update `pyproject.toml` package-data patterns for nested/hashed assets and the
   packaged Node server bundle. Verify both sdist and wheel contents.
4. Commit the generated server/client output and add a check that rebuilds from
   the lockfile and fails on any diff or untracked generated file.
5. Switch the Python launcher to the packaged Node entry point and built Vite
   assets.
6. Remove `tcw/serve/static/app.js`, `tree.js`, `marked.min.js`, and other legacy
   generated/runtime assets only after replacement contract and Playwright tests
   pass. Retain attribution/license material required by the new locked graph.
7. Retire legacy JS-specific tests only when equivalent TypeScript/Playwright
   coverage is demonstrably present.
8. Build a wheel, install it into an isolated environment/directory, remove or
   hide the source checkout, pnpm, and `node_modules`, and prove `tcw serve`
   starts and serves hashed assets/API traffic using only Python plus Node 22.12+.

Gate: clean checkout build is reproducible, `git diff --exit-code` remains
clean, sdist/wheel contain all required runtime artifacts and no development
cache, and the isolated install smoke passes offline.

## Phase 8: Documentation and capability reconciliation

Documentation Sync predicts every repository entry below will fire because the
implementation changes public runtime requirements and behavior-affecting code:

1. Update `README.md`:
   - state that only `tcw serve` requires Node.js 22.12+;
   - distinguish installed runtime requirements from pnpm-based contributor
     requirements;
   - preserve the documented `tcw serve`, `--port`, and `--no-open` examples;
   - describe committed offline build artifacts and add missing/old-Node
     troubleshooting;
   - remove the obsolete “no build step” implementation claim without changing
     the user-visible offline guarantee.
2. Update `docs/capabilities/web/description.md` with the Node 22.12+
   prerequisite. Keep its metadata status `Supported` and do not alter
   `web/editing` unless verification exposes a real product change.
3. Update `docs/release-notes/upcoming.md` in plain language with the runtime
   prerequisite, unchanged command surface, and parity-focused migration.
4. Update `docs/changelogs/upcoming.md` with technical Fastify/React/sidecar,
   security, testing, build, and packaging details plus the final implementation
   commit hash range.
5. Update `skills/tcw-plugin/SKILL.md` and the relevant installation/doctor
   references so agents:
   - require/check Node 22.12+ only when diagnosing or using `tcw serve`;
   - do not require pnpm or `node_modules` for installed TCW;
   - know how to distinguish Node prerequisite failures from broken packaged
     assets or child startup failures.
6. Re-run Documentation Sync after implementation to catch any additional
   public surface discovered during the migration.
7. Run `tcw capabilities set web --status Supported` only if needed to update
   its description/fields through supported CLI operations; otherwise edit the
   description body as the capability documentation surface. Confirm the work
   item's `capabilities.yaml` still lists only `changed: [web]`.
8. Keep `local-web-app` and `web/editing` unchanged, then run capability and
   taxonomy checks.

Gate: documentation matches the built behavior, the `web` ledger entry resolves
and remains Supported, and no skill claims Python alone is sufficient for
`tcw serve`.

## Phase 9: Full verification and closeout preparation

Run from a clean checkout with locked dependencies:

```sh
corepack pnpm install --frozen-lockfile
corepack pnpm typecheck
corepack pnpm lint
corepack pnpm test
corepack pnpm test:e2e
corepack pnpm build
corepack pnpm check:build
python -m pytest
tcw capabilities check
tcw taxonomy check
tcw validate
git diff --check
```

Use the exact script names established in Phase 1 if they differ, and record the
commands/results in `outcome.md`.

Then perform these system checks:

1. Start `tcw serve --no-open` on an available port with Node 22.12+; fetch the
   app shell, a hashed asset, and representative GET/write API calls through
   Fastify; stop with Ctrl-C and confirm both listeners/processes exit.
2. Repeat with a requested occupied port and confirm actionable failure plus no
   orphan sidecar.
3. Run the wheel/pipx-style isolated-install smoke without pnpm,
   `node_modules`, or source-tree asset access.
4. Run the missing/old-Node smoke and a non-serve Python command without Node.
5. Inspect the final source and generated diffs, dependency/license inventory,
   wheel contents, process list, and listening ports.

Before completion:

- write and separately commit `outcome.md` with implementation and verification
  evidence;
- stop for explicit user verification and refinements;
- write and separately commit `refined-outcome.md` after approval;
- reconcile `web` and re-run all TCW checks;
- propose resolving
  `2026-07-03-live-browser-test-pass-for-the-interactive-web-editor` as
  `superseded`, citing the Playwright evidence, but obtain the user's closeout
  decision before changing it;
- leave the rich Markdown editor item untouched;
- ask the user to select completion route and version. Do not infer a release or
  push from successful implementation.

Only after those gates should a future session run:

```sh
tcw work complete 2026-07-21-upgrade-tcw-serve-to-fastify-and-react --resolution done --confirm
```

Commit the completion transition separately. Cut a release only after the user
chooses a version; push only if explicitly requested.

## Parallelization map

- Phases 1-4 are the critical path because they define contracts and the
  browser/sidecar trust boundary.
- Within Phase 3, static serving/security tests and proxy-fidelity tests can be
  developed independently after the Fastify factory exists.
- Within Phase 5, the three read-only axis views and the shared tree/filter
  tests can proceed in parallel after routing and transport types stabilize.
- Within Phase 6, Work, Taxonomy, and Capability forms can proceed in parallel;
  dirty-state, lifecycle, and revision-conflict integration stays centralized.
- Documentation drafting and wheel-smoke scaffolding can begin after Phases 3-4,
  but final wording/evidence waits for the built behavior.
- Playwright cases can be added continuously alongside each ported workflow;
  the legacy app is not removed until the complete parity matrix is green.
