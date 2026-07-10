# Spec — tcw:// reference protocol + tcw validate + web-view navigation

Single cohesive feature (three collaborating parts), not phased. Builds on the folder+federation substrate ([[2026-07-10-unify-folder-substrate-across-taxonomy-capabilities-work-and-add-capability-federation]]); the stable capability `id` and path-addressed stores are the resolution targets.

## Capability changes

Product delta to the `tcw` CLI + serve viewer (TCW dogfoods its own capabilities):

- **New:** "Reference a TCW object with a `tcw://` link" — author inline markdown links to taxonomy/capability/work objects.
- **New:** "Validate a TCW node" — `tcw validate [path]` reports YAML, reference, and structural problems in one pass.
- **Changed:** "Browse TCW content in a local web app" (`web`) — rendered `tcw://` links become in-app navigation with browser history.

## Problem

Today a cross-object reference in prose is an inert string — nothing checks it resolves, and nothing follows it. TCW objects now have stable, path/slug identities across three axes and (for T/C) federation aliases, so a typed, resolvable reference is expressible. There is also no single "is this node internally consistent?" command — YAML soundness and reference integrity are only partially covered by the per-component `check`s, and `tcw://` links aren't covered at all.

## Goals

1. A pure, portable `tcw://[<namespace>/]<axis>/<ref>` grammar with a parser and a resolver that dispatches through the abstract stores.
2. `tcw validate [path]` — one aggregate command: YAML well-formedness + `tcw://` link resolution + illegal-char checks + delegation to component `check()`s.
3. In `tcw serve`, a rendered `tcw://` link navigates the SPA (History API) for hosted objects; foreign-namespace links render inert.

## Non-goals

- `tcw://` does **not** replace the structured pointers (`Subject`/`Feature`/`Planning doc`/`blocked_by`) — it's an additive inline-prose mechanism.
- No new store-interface methods, no remote namespace adapters, no cross-repo global index, no link-authoring UI. Stored markdown is never rewritten.

## Constraints

- **Litmus:** parsing is pure; resolution only calls existing abstract `get()` / `resolve_qualified_work_ref`. Markdown scanning + web-nav are FS/serve-adapter details. No new interface method is added, so nothing new can be FS-only.

## Current-state findings

- Top-level CLI (`tcw/cli.py:62`) registers `init`/`serve` as `sub.add_parser(...).set_defaults(func=...)`; `tcw validate` slots in identically.
- Stores resolve refs today: `FsTaxonomyStore.get(ref)` and `FsCapabilitiesStore.get(ref)` handle bare + `alias/`-prefixed refs (federation) and raise `AmbiguousRef`; `resolve_qualified_work_ref(node, ref)` (`fs.py:182`) handles bare / `sub/proj/<slug>` / `<status>/…/<slug>`. Node discovery: `find_node` / `find_node_root`.
- Serve SPA router (`app.js:2740`): URL scheme `/{namespace}/{axis}/{identifier}`, `axis ∈ {taxonomy,capabilities,work}`; `parsePath`/`pathFor`/`applyRoute`/`pushRoute` with History API + `popstate`. `applyRoute` selects a key only if it names a loaded object. Bodies render via `marked.parse(...)` in `renderCapability`/`renderTaxonomy`/`renderWork`. Server aggregates descendants when `include_descendants` (`serve/__init__.py:311`).

## Proposed behavior

### 1. `tcw/refs.py` — parse + resolve (new module)

```
@dataclass TcwRef:  namespace: str  # "" = local
                    axis: str       # "T" | "C" | "W" (normalized upper)
                    ref: str

parse_tcw_uri(uri) -> TcwRef | None
```
- Require the `tcw://` scheme; **split the remainder on `/` first, then percent-decode each segment** (matching `app.js:2752` `parsePath`, so a `%2F` inside a segment can't inject a spurious separator). The **axis** is the first segment whose `.upper()` ∈ {T,C,W}; `namespace` = segments before it joined by `/`; `ref` = segments after it joined by `/`. Return `None` if there is no axis segment, an empty `ref`, or **any segment** (namespace or ref) contains a control char / `..` / NUL (the illegal-char guard applies to namespace segments too, mirroring `_safe_store_id`). Total function — never raises.
- **Namespace/axis collision (documented limitation):** because the axis is the first bare `T/C/W` segment, an `extends` alias or node dir literally named `t`/`c`/`w` is unsupported and would be swallowed as the axis. Not code-enforced (pathological); documented, and covered by a test asserting the first-bare-axis-wins behavior.

```
resolve_tcw_ref(node_root, uri, include_descendants=False) -> ResolveResult
@dataclass ResolveResult: ok: bool; axis: str|None; key: str|None; reason: str
```
- Parse; dispatch by axis, building the SPA object `key` (namespace-qualified where present). Wrap each store call in a broad `except` → `ok=False, reason=str(e)` (never propagate a store exception to a caller scanning many links):
  - **T** → `FsTaxonomyStore.open(node).get(<namespace/ref or ref>)`; `key` = the term's `qualified`.
  - **C** → `FsCapabilitiesStore.open(node).get(...)`; `key` = the capability's `qualified`.
  - **W** → `resolve_qualified_work_ref(node, <namespace/ref or ref>)`; `key` = the (namespace-qualified) slug. **A descendant-node (namespaced) work ref resolves to `ok=True` only when `include_descendants` is set** — otherwise `ok=False` (the viewer isn't hosting it, so the SPA would dead-end). Local (un-namespaced) work always resolves.
- `ok=False` with a `reason` when the node/store is absent, the ref is malformed, doesn't resolve, or is ambiguous (`AmbiguousRef`). `parse_tcw_uri` is genuinely **pure**; `resolve_tcw_ref` is thin CLI/serve **adapter glue** (it imports the FS stores and is keyed on a `Path`) — litmus-clean only in that it adds no store-interface method, not part of the abstract spine.

### 2. `tcw validate [path]`

- Resolve the node (`find_node`); error if none. Scan roots = `[path]` if given, else the node's `docs/taxonomy`, `docs/capabilities`, `docs/work`.
- **(a) YAML well-formedness** — every `*.yaml` under the scan roots loads via the unique-key loader (`load_yaml(..., unique=True)`); a parse error (incl. duplicate keys) is a problem `"<file>: <error>"`.
- **(b) `tcw://` links** — every `*.md` under the scan roots is scanned for the markdown **link-target form only** — `](tcw://…)` — **after stripping fenced (```` ``` ````) and inline (`` ` ``) code spans**, so `tcw://` examples in code (README, skills, release notes) are ignored and docs that teach the scheme don't fail their own validator. (Bare autolinks aren't matched — the render shim can't turn them into anchors anyway, §3.) Each match is `resolve_tcw_ref`'d; malformed or unresolved → problem `"<file>: tcw:// <uri> → <reason>"`.
- **(c) component checks** — run each component's `check()` and prefix its lines. **With no `[path]`**, run both `FsTaxonomyStore.check()` and `FsCapabilitiesStore.check(taxonomy=…)`. **With `[path]`**, run the `check()` of whichever component tree the path falls under (`docs/taxonomy` → taxonomy, `docs/capabilities` → capabilities; a path under `docs/work` or spanning several runs none). **Guard:** if pass (a) reported a YAML *syntax* error, **skip** the component checks (they re-`load_yaml` the same files and would raise) and note that they were skipped.
- Print problems grouped by source; exit `1` if any, else print `validate OK`, exit `0`.

### 3. Web-view navigation (serve)

**Prerequisite — the render shim must emit link anchors.** `tcw/serve/static/marked.min.js` is a hand-written minimal shim (headings/paragraphs/lists) that HTML-**escapes** every line — it renders **no** `<a>` elements, so a body's `[text](tcw://…)` currently shows as escaped literal text and the scan-for-anchors mechanic below finds nothing. Teach the shim to emit `<a href="tcw://…">text</a>` for the **inline link form `[text](tcw://…)` restricted to the `tcw://` scheme** (text still escaped; no other scheme, no reference-style links) — the minimal change that fits the shim's "minimal subset" intent without pulling in real `marked`.

- **`POST /api/resolve`** (new route): body `{"uris": ["tcw://…", …]}` (list capped at **256**; the existing `MAX_BODY_BYTES` 1 MiB cap and the loopback + JSON guards via `_validate_mutating_request`/`_read_json_body` apply — a read carried over POST so it can take a body) → `{"<uri>": {"ok": true, "axis": "capabilities", "key": "shared/auth/login"} | {"ok": false}}`, computed with `resolve_tcw_ref(node_root, uri, include_descendants=self.server.include_descendants)`, so a descendant work ref reports `ok:false` when the viewer isn't aggregating descendants.
- **SPA** (`app.js`): after a **read-render** body renders (`renderWork`/`renderTaxonomy`/`renderCapability` — **not** the live editor preview, so the editor dirty-guard is never in play), scan the rendered `<article>` for `a[href^="tcw://"]`, collect the hrefs, `POST /api/resolve`, then per anchor:
  - resolvable → set `data-nav` to the SPA route (`pathFor(axisWord, key)`, mapping `T/C/W → taxonomy/capabilities/work`); a delegated click handler `preventDefault`s and navigates in-app (set `state.view`/`state.selected`, `render()`, `pushRoute()`) so `popstate`/back works;
  - unresolvable, **or if the `/api/resolve` call itself fails** (network error) → add a `tcw-inert` class + `title` = the raw uri, `preventDefault` (styled, non-navigating — fail safe).
- Axis-word mapping and the `key` come straight from `/api/resolve`, so the client does no TCW parsing of its own.

## Acceptance criteria

- `parse_tcw_uri` round-trips the grammar: `tcw://C/auth/login` → (`""`,`C`,`auth/login`); `tcw://shared/C/auth/providers/github` → (`shared`,`C`,`auth/providers/github`); `tcw://W/2026-01-01-x` → (`""`,`W`,`2026-01-01-x`); rejects a missing axis, empty ref, `..`/control chars in any segment; handles multiple slashes and the `tcw://T/C/ref` first-bare-axis-wins collision per the documented rule; splits before percent-decoding.
- `resolve_tcw_ref` resolves local + `extends`-alias (T/C) + descendant-node (W, only with `include_descendants`) refs; returns `ok=False` with a reason for dangling/ambiguous/foreign/unhosted-descendant; never propagates a store exception.
- `tcw validate` on a clean node prints `validate OK` (exit 0); a malformed `meta.yaml`, a dangling `](tcw://…)` link in a body, and a taxonomy/capability `check` failure each surface as a distinct problem with exit 1. A `tcw://` example inside a fenced code block is **ignored**. `tcw validate docs/capabilities` narrows the scan and runs the capabilities `check()`. A YAML syntax error does not crash the run (component checks are skipped and noted).
- In `tcw serve`: a body's `[text](tcw://…)` renders as a real anchor; a link to a hosted object navigates the SPA in-place and pushes history (back returns); a link to an unhosted namespace (or on a resolve failure) renders inert with a tooltip. `POST /api/resolve` returns the correct axis/key or `ok:false`, caps the list, and rejects a non-loopback/oversize request.
- No new `TaxonomyStore`/`CapabilitiesStore`/`WorkStore` interface method is added. Full suite green + new `tests/test_refs.py`, `tests/test_validate.py`, and serve resolve tests.

## Risks & dependencies

- **Grammar / namespace collision** — the axis is the first bare `T`/`C`/`W` segment, so a `ref` or an `extends` alias / node dir literally named `t`/`c`/`w` is unsupported (swallowed as the axis). Documented limitation, not code-enforced (pathological — nobody names an alias `c`); `parse` is total (returns `None`, never crashes) and a test pins the first-wins behavior.
- **Render-shim dependency (blocker if missed)** — the web-nav relies on the shim emitting anchors, which it does not today; the prerequisite shim change (§3) is a first-class task, not a footnote.
- **Markdown scanning breadth/fidelity** — bounded to the `docs/` trees (not the whole repo); scans only the `](tcw://…)` link-target form after stripping code spans, so code examples don't false-positive.
- **`tcw validate` ↔ component `check()` ordering** — a YAML syntax error must short-circuit the component checks (they re-load the file and would raise). Handled by the pass-(a)-gates-pass-(c) guard.
- Depends only on already-shipped resolution (`get`, `resolve_qualified_work_ref`); no interface change.

## Documentation-sync (triggers expected to fire)

- `README.md` [Public-API] — new `tcw validate` command + `tcw://` linking.
- `docs/release-notes/upcoming.md` [Public-API] and `docs/changelogs/upcoming.md` [Any-Code-Change].
- `skills/tcw-*/SKILL.md` [Skill-Driven-Component] — mention `tcw://` linking + `tcw validate` where each component's skill teaches authoring/validation (at least tcw-capabilities and tcw-taxonomy bodies; tcw-work artifacts).
