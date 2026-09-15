# Plan — Hierarchical tree view for the web UI object list

Almost entirely frontend. The **one** Python change is a one-line addition to the
static-asset allowlist so the new `tree.js` is served (see Phase 0); no store /
API / route / model change. Work is in `tcw/serve/static/` (`app.js`, `style.css`,
`index.html`), a new JS module, one Node test file, and that allowlist line +
its serving test. The abstraction litmus test is unaffected (no store surface).

## Testing approach (decided)

The repo has **no JS test toolchain** (tests are pytest against the Python
server; the frontend is plain browser globals loaded via `<script>`). The prune/
namespace logic is non-trivial and reviewers asked for it to be tested, so:

- Extract the **pure** tree logic into a new `tcw/serve/static/tree.js` (no DOM,
  no browser globals) with a guarded CommonJS export — keep it a **static object
  literal** `if (typeof module !== "undefined") module.exports = { … }` (Node's
  cjs-module-lexer only exposes named ESM imports from a literal; fall back to
  `import pkg from …; const { … } = pkg` if a named import ever fails).
- `index.html` loads it with `<script src="/tree.js" defer></script>` immediately
  **before** the existing `<script src="/app.js" defer>` tag, matching the current
  deferred-script pattern (same-origin; CSP `default-src 'self'` allows it; two
  deferred scripts run in document order).
- **The static-serving allowlist must include it** — see Phase 0; otherwise
  `/tree.js` falls through to the SPA fallback and returns `index.html`, and the
  browser executes HTML as JS → `renderList` throws → dead left column. This is
  the one thing an implementer would otherwise miss.
- Test it with `node --test` against `tests/tree.test.mjs` — **Node stdlib, zero
  new dependencies.** Wiring `node --test` into CI is an optional follow-up, not
  required for this item.

`app.js` keeps the DOM/rendering/state; `tree.js` holds only data→data
functions.

## Phase 0 — Serve `tree.js`  (`tcw/serve/__init__.py`, `tests/test_serve.py`)

Do this first so the new module actually loads.

- `tcw/serve/__init__.py:423` — add `"/tree.js"` to the static allowlist tuple
  `("/app.js", "/style.css", "/marked.min.js")`. (`_static_bytes` already maps
  `.js` → the right content-type; no other change.)
- `tests/test_serve.py` — the existing `<script src="/app.js"` check
  (`:82`) is a substring assert and does **not** break when a new tag is added,
  so it needs no edit. **Add** a serving test mirroring
  `test_static_assets_still_serve_own_bytes` (`:107`) that `GET /tree.js` returns
  the module's own bytes with a JS content-type (guards against the allowlist
  regression above).

## Phase 1 — Pure tree model + tests  (`tree.js`, `tests/tree.test.mjs`)

Independent of CSS (Phase 4); Phases 2–3 depend on this.

Functions in `tree.js`:

- `buildPathTree(items, keyOf)` — split each `keyOf(item)` on `/`; build nested
  nodes `{ name, path, item|null, children: [] }`; a node is **selectable** iff
  `item != null` (an exact-path match), else a folder. Federated `<alias>/…`
  items nest under a non-selectable `<alias>` root automatically.
- `buildWorkTree(items, keyOf)` — index by `keyOf(item)` (the work slug/qualified
  slug); resolve each item's `parent` **within its own namespace prefix**: for
  `itemKey = "<prefix>/<slug>"`, look up parent as `"<prefix>/<parent>"`; for a
  bare key, look up `parent` bare. Missing/out-of-set parent → node is a root
  (never synthesize a folder); a promoted node **keeps its full `itemKey`
  unchanged** (identity is never rewritten). Preserve input order per level.
  Guard against a parent cycle with a visited set so a malformed relation can
  never hang the browser (cheap; the store already forbids cycles, but a UI hang
  is not an acceptable failure mode).
- `pruneTree(node, predicate)` — keep a node iff `predicate(node.item)` is true
  **or** any descendant is kept; return the pruned tree **and** the set of paths
  that must be force-expanded (ancestors of kept matches). Folder nodes
  (`item == null`) are kept iff a descendant is kept.
- `ancestorsOf(key)` — for a path key, the list of ancestor path prefixes; for a
  work key, the chain of parent keys (namespace-aware) — used to auto-expand.

`tests/tree.test.mjs` (`node --test`) covers:

1. path-axis folders vs selectable nodes (`capabilities/…` folders non-selectable;
   `web` selectable **and** a parent of `web/editing`); plus edge cases: empty
   input, a single root item, a deeply nested path;
2. work nesting by `parent`; missing/out-of-set parent → promoted to root with its
   key intact;
3. **qualified `sub/proj/<slug>`** parent resolves in-namespace (child nests under
   the descendant parent, not root); key never split on `/`; and a
   **substring-but-not-namespace** parent (`parent: "foo"` must not match item
   key `"foobar"`) stays a root — proving the resolution is prefix-segment-aware,
   not substring;
4. `pruneTree` reachability: a non-matching parent with a matching child is kept
   and reported as force-expand; no-match and all-match extremes;
5. `ancestorsOf` for a nested path and a work chain; and an **unknown/absent key**
   returns best-effort ancestors without throwing;
6. the **effective-expansion merge** helper (`state.expanded ∪ forceExpand`): a
   search's force-expand paths must not erase the user's manual expand/collapse
   set, and a collapsed ancestor must not hide a search match. Extract this merge
   as a tiny pure function in `tree.js` so it is unit-testable here.

## Phase 2 — Rendering + expand/collapse state  (`app.js`)

Depends on Phase 1.

- **State:** add `state.expanded = { work: Set, taxonomy: Set, capabilities: Set }`
  (session memory; no localStorage — matches the md-editor split precedent).
  Default: on first data load, seed each axis's set with **all folder/parent
  paths** (everything expanded → initial parity with today's flat list).
- **`renderList()` rewrite:** build the tree from the **unfiltered**
  `state.data[view]` via the Phase-1 functions, then:
  - text filter → `pruneTree` predicate `JSON.stringify(item).includes(q)`;
  - work status filter → additional predicate `statusFilter[item.status] !== false`;
  - the combined prune returns force-expand paths merged (via the Phase-1
    effective-expansion helper) with `state.expanded[view]`, so matches/visible
    children are reachable without wiping the user's manual expand state.
  Render recursively with a new `treeHtml(nodes, depth, view)`; keep the trailing
  create button. Retire `groupedWorkHtml` **and** the now-unused
  `WORK_STATUS_GROUP_ORDER` constant (status headers gone; keep `WORK_STATUSES`,
  which still drives the toggle bar).
- **`treeHtml` rows:**
  - folder → `<button class="tree-toggle" aria-expanded=…>▸/▾</button>` + dim
    label; toggles membership in `state.expanded[view]` and re-renders.
  - selectable → existing `.item` button (unchanged `data-key` = `itemKey`), so
    selection/detail/routing are untouched; if it also has children, prepend a
    `tree-toggle`. Row title uses `itemTitle` (leaf name); drop the redundant full
    path from `itemMeta` in tree view, keep status/kind/origin.
  - work rows keep the copy-slug button (sibling of `.item`, as today).
  - a status-filtered-out ancestor kept only for a visible child gets an
    `ancestor-dim` class.
  - indentation by `depth` (inline `style="padding-left:…"` or a `--depth` var).
- **Wiring:** reuse existing `.item` click + `.copy-slug` + `.create-btn`
  handlers; add a `.tree-toggle` handler (guarded by `canLeaveEditor()` only if a
  toggle would change selection — it does not, so a bare toggle is safe while
  editing; verify it does not exit the editor).

## Phase 3 — Auto-expand ancestors on select / deep-link  (`app.js`)

- On item selection (list click handler) and in `applyRoute()` when a deep-linked
  key resolves, add `ancestorsOf(key)` to `state.expanded[view]` before render, so
  a selected/deep-linked nested node is always visible.

## Phase 4 — Styles  (`style.css`)

Independent of Phases 1–3 (can be built in parallel).

- `.tree-toggle` (disclosure triangle button — inherit the muted button look),
  `.tree-folder` (non-selectable label), depth indentation, `.ancestor-dim`
  (reduced opacity for filtered-out ancestors). Reuse existing `.item`/`.item.active`
  for selectable rows; **remove** the now-dead `.status-group` rules
  (`style.css:235-246`) since the headers are gone.

## Phase 5 — Documentation sync

Evaluate via `skill-cefailures:documentation-sync`. Expected to fire:

- `docs/changelogs/upcoming.md` **[Any-Code-Change]** — Added `tree.js` +
  Node test; Changed: web UI left column is a collapsible hierarchy tree across
  all axes (work board no longer status-grouped); include the commit hash range.
- `docs/release-notes/upcoming.md` **[Public-API]** — user-facing: "The web app's
  object list is now a collapsible tree that mirrors each axis's hierarchy."
- `README.md` **[Public-API]** — the `tcw serve` section (README:207–214) gains a
  one-line mention that the object list is a hierarchical tree.
- **No SKILL.md update** — the web app is not a skill-driven component (the
  `tcw-*` skills drive the CLI); confirm none references the flat list.

## Phase 6 — Verification

- `node --test tests/tree.test.mjs` — pure-model tests pass.
- `python -m pytest tests/test_serve.py` — server/static tests still pass; if a
  test asserts the exact `<script>` set in `index.html`, update it for `tree.js`.
- `python -m pytest` — full suite green.
- **Manual smoke** (via `tcw serve` / the `run` skill), extending the app.js
  smoke checklist: (a) capabilities folders non-selectable, `web` selectable +
  expandable; (b) taxonomy `store/adapter` nests; (c) work child nests under
  parent, copy-slug works, status toggles + dim-ancestor behave; (d) collapse/
  expand persists within session; (e) deep-link to `/capabilities/web/editing`
  selects it with ancestors expanded; (f) text search prunes to matches +
  ancestors; (g) editor/create flows unregressed.

## Touch points

| File | Change |
|---|---|
| `tcw/serve/__init__.py` | add `"/tree.js"` to the static-asset allowlist (`:423`) |
| `tcw/serve/static/tree.js` | **new** — pure tree build/prune/ancestors/merge + guarded export |
| `tests/tree.test.mjs` | **new** — `node --test` for the pure model |
| `tcw/serve/static/app.js` | expand state; `renderList` tree rewrite; `treeHtml`; retire `groupedWorkHtml`; auto-expand on select/route |
| `tcw/serve/static/style.css` | `.tree-toggle`, `.tree-folder`, indentation, `.ancestor-dim` |
| `tcw/serve/static/index.html` | load `tree.js` before `app.js` |
| `tests/test_serve.py` | **add** a `/tree.js` serves-own-bytes test (existing `<script>` substring assert is unaffected) |
| `docs/changelogs/upcoming.md`, `docs/release-notes/upcoming.md`, `README.md` | doc sync |

## Parallelization

- Phase 1 (`tree.js` + tests) and Phase 4 (CSS) are independent — parallelizable.
- Phases 2–3 depend on Phase 1; Phase 2 depends on Phase 4 only for final visual
  polish (can develop against draft CSS).
- Phase 5 docs can be drafted once behavior is settled (after Phase 2).
- Given the small surface, sequential execution by one agent is reasonable; the
  split above is for optional subagent parallelization.

## Out of scope / deferred (from review)

- Full ARIA `tree`/`treeitem` roles + roving-tabindex arrow navigation (basics —
  focusable toggle buttons with `aria-expanded` — are in scope).
- localStorage persistence of expand state across sessions.
- Adding `Feature=local-web-app` to the `web` capability (pre-existing gap).
- Wiring `node --test` into CI.
- Virtualization / perf tuning for the tree render. `renderList` rebuilds the
  tree from `state.data[view]` on each filter event; real nodes number in the
  tens, so this O(n) rebuild is fine. Mark the rebuild with a `ponytail:` comment
  naming the ceiling (revisit only if a node's list reaches thousands). Not doing
  speculative optimization now.
