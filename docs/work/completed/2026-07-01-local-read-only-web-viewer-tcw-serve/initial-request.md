# Local read-only web viewer (`tcw serve`)

## Requested outcome

A simple, local web app that lets people interact with TCW content beyond the
CLI. `tcw serve` boots a localhost HTTP server that renders the **Work** board,
the **Taxonomy** tree, and **Capabilities** as browsable pages.

v1 is **read-only**, but the architecture and technology must support full
interaction (create/edit/transition) later as a purely *additive* step — no
rewrite. The forward-compat pivot is a JSON API over the existing store
interface: read-only ships GET only; writes later add POST/PATCH that call the
same store methods the CLI already uses.

## Decisions already made (brainstorm)

- **Stack:** stdlib `http.server` (no web framework), a JSON API produced by
  `dataclasses.asdict` over the store dataclasses, and one static HTML page.
  Markdown rendered client-side by a single vendored `marked.min.js`. **No new
  Python dependency** — TCW stays a one-runtime-dep project (PyYAML).
  (Rejected: Flask/FastAPI, and a React/Vite SPA build step — both add weight a
  localhost single-user tool doesn't need.)
- **Scope:** all three axes (Work, Taxonomy, Capabilities), read-only.
- **Item bodies:** inline-render only `initial-request.md`. The other lifecycle
  artifacts (`spec.md`/`plan.md`/`outcome.md`/`refined-outcome.md`) are shown as
  **links that open the file in the user's default editor**, not rendered
  inline. (User's call: initial-request is the natural at-a-glance read; the rest
  are editor territory.)
- **Artifact enumeration:** consolidate the "which lifecycle artifacts exist"
  logic — today duplicated in the board's `stages()` via `st.path()` — into one
  store method both the board and the web app call, so the filesystem coupling
  lives in the FS adapter (litmus-clean; a remote adapter realizes it its own
  way).

## Constraints / non-goals

- **Prime directive (litmus test):** the web layer calls only store-interface
  methods and serializes dataclasses. No `docs/` globbing in the web layer. A
  future `JiraWorkStore` must be able to back the identical UI.
- Bind **127.0.0.1 only**; no auth (local single-user tool).
- **Out of scope for v1:** in-browser editing (the "open in editor" link covers
  it), authentication, any framework/build step, inline rendering of
  spec/plan/outcome.

## Product delta

Yes — a new user-facing capability (`tcw serve`, browse TCW content in a local
web UI). Run the taxonomy (Vocabulary/Feature) check and the tcw-capabilities
planning gate before the technical plan.

## Open questions for spec

- The "open in default editor" endpoint: which opener strategy (respect
  `$VISUAL`/`$EDITOR`, else platform default `open`/`xdg-open`/`os.startfile`)?
- Exact shape of the consolidated artifacts store method (name + return type),
  and how `stages()` is refactored onto it without changing board output.
