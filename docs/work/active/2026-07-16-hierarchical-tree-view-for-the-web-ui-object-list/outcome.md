# Outcome — Hierarchical tree view for the web UI object list

Work completed successfully.

## What changed

- **`tcw/serve/static/tree.js` (new)** — pure data→data tree model, no DOM:
  `buildPathTree` (trie of `/`-split path keys; a node is selectable iff its
  exact path is a real item, else a folder; federated `<alias>/…` items nest
  under a non-selectable origin folder), `buildWorkTree` (nests by the `parent`
  relation; resolves a bare `parent` within the child's `sub/proj/` namespace
  prefix first, falling back to bare; missing parent promotes the child to
  root; work keys are never split), `pruneTree` (keep a node iff it matches or
  has a visible descendant; reports force-expand ancestor paths),
  `ancestorsOf` (path prefixes / namespace-aware parent chain with a cycle
  guard), `mergeExpansion`. Dual-exported: `window.TCWTree` for the classic
  `<script>` path and guarded CommonJS for `node --test`.
- **`tcw/serve/static/app.js`** — `renderList()` rebuilt: tree built from the
  **unfiltered** `state.data[view]`; the text filter and work status toggles
  apply as a tree prune so a filtered-out parent of a visible child stays
  reachable, rendered dimmed (`.ancestor-dim`) and still selectable. Per-axis
  expand/collapse Sets in `state` (session memory); unseen parent paths default
  to expanded; selection and deep links auto-expand ancestors
  (`expandAncestors` in the click handler and `applyRoute`). Only the transient
  text filter force-expands ancestors of matches — the standing status toggles
  do not override a manual collapse. Work board status group headers removed
  (toggle bar + per-row badges remain). Retired: `groupedWorkHtml`,
  `WORK_STATUS_GROUP_ORDER`, `currentItems`. Redundant full path dropped from
  `itemMeta` (the tree conveys it).
- **`tcw/serve/static/style.css`** — `.tree-row`, `.tree-toggle`,
  `.tree-spacer`, `.tree-folder`, `.tree-indent`, `.ancestor-dim`; dead
  `.status-group` rules removed.
- **`tcw/serve/static/index.html`** — loads `/tree.js` before `/app.js`.
- **`tcw/serve/__init__.py`** — `"/tree.js"` added to the static allowlist
  (without it the SPA fallback serves index.html as JS).
- **`tests/tree.test.mjs` (new)** — 17 `node --test` cases over the pure model.
- **`tests/test_serve.py`** — `/tree.js` serves-own-bytes + content-type test.
- **Docs** — README `tcw serve` section, `docs/changelogs/upcoming.md`,
  `docs/release-notes/upcoming.md`.

## Verification performed

- `node --test tests/tree.test.mjs` — 23/23 pass (path folders vs selectable
  nodes, deep nesting, federated origin folders, work parent nesting,
  missing-parent promotion, qualified `sub/proj/<slug>` in-namespace
  resolution, substring-vs-namespace parent, parent-cycle reachability,
  self-parent, prototype-named keys, prune reachability + force-expand,
  ancestors incl. cycle termination and qualified keys, expansion merge).
- `python -m pytest` — full suite, 605 passed.
- In-browser smoke against the live repo (Chrome, `tcw serve --port 8901`):
  capabilities folders (`capabilities/`, `cli/`, `plugin/`, `taxonomy/`,
  `work/`) non-selectable; `web` selectable **and** expands to `web/editing`;
  taxonomy `store/adapter` and `work-item/*` nest; a work child nests indented
  under its parent (verified with a temporary child item, removed after);
  collapse/expand persists across tab switches; deep link
  `/capabilities/web/editing` selects with ancestors expanded; deep link to a
  nested work child selects it; text filter prunes to match + dimmed ancestor
  and clearing restores; status toggles hide/show correctly; folder clicks
  never change the URL; copy-slug buttons and the create button intact; zero
  console errors.

## Review round (dual review: subagent + bllm-review-many)

Applied:

- **Cycle-safe work tree** (both reviewers): a malformed parent cycle left its
  members unreachable from every root — silently dropped from the render.
  Cycle members are now promoted to root; `ancestorsOf` already had a visited
  guard.
- **Prototype-key hardening** (subagent, MEDIUM): a slug named `constructor`
  crashed `renderList`; `__proto__` polluted `Object.prototype`; other
  prototype-named keys were silently dropped. All tree.js lookup tables are
  `Object.create(null)`.
- **O(n) key lookups** (bllm): `items.find()` inside per-key loops replaced
  with prebuilt maps.
- **Shared `resolveParentKey`** (bllm): the in-namespace qualified-slug parent
  resolution was duplicated between `buildWorkTree` and `ancestorsOf`.
- `pruneTree` doc comment: consumes its input, build a fresh tree per call.
- Test hygiene: renamed a test whose name contradicted its assertion; added
  work-mode unknown-key, qualified-key ancestors, cycle, self-parent, and
  prototype-key tests.

Dismissed (with reasons):

- "`itemVisible` throws on null item" (gemma4, claimed blocking) — false
  positive: `pruneTree` and `treeHtml` only pass non-null items.
- "`esc()` may be undefined / needs tests" (qwen25) — defined at `app.js:161`,
  outside the reviewer's diff window; all interpolations verified routed
  through it.
- Test error-handling / backward-compat concerns (qwen25) — pytest failing
  loudly is intended; removed functions have zero remaining references.
- `seenPaths` reset on refresh (gemma4 question) — specced v1 behavior
  (session memory only, no localStorage).
- Filter-time collapse being a visual no-op on force-expanded ancestors
  (subagent nit) — consistent with the "search forces visibility" spec intent.

## Deviations from plan

- **Indentation**: the plan suggested `style="padding-left:…"` or a `--depth`
  var; the server's CSP (`default-src 'self'`) blocks inline style attributes,
  so depth renders as repeated fixed-width `.tree-indent` spans instead.
  (Caught live in the browser — computed width was 0.)
- **Status-toggle force-expand**: the plan had all prune force-expands merged
  into the expand state; live testing showed the standing status filter
  (completed hidden by default) made every collapse instantly re-expand. Only
  the transient text filter force-expands now; behavior verified in-browser.
- `ancestorsOf(key, mode, items)` takes an explicit mode/items instead of
  auto-detecting, keeping tree.js DOM- and state-free.

## Follow-ups (user requested these be done now — implemented in refinement)

All four deferred items were implemented during verification/refinement
(commit `c3f2ade`):

- **ARIA tree navigation**: `#list` is `role="tree"`; each row's primary
  control is a `treeitem` with `aria-level`/`aria-expanded`/`aria-selected`;
  roving tabindex (exactly one tabbable row); arrow-key navigation
  (Up/Down/Right/Left/Home/End) with focus restore across the re-render on
  keyboard expand/collapse. Disclosure toggles left the tab order
  (`tabindex="-1" aria-hidden` — mouse-only affordance).
- **localStorage persistence** of expand/collapse state
  (`tcw.treeExpanded`/`tcw.treeSeen`), best-effort like the list-width split.
- **`node --test` under pytest**: `tests/test_tree_js.py` shells out to node
  (skipped when absent) — 606 tests total.
- **`web` capability** gains its missing `Feature=local-web-app` link.

Verified in-browser: arrow navigation including keyboard collapse/expand with
focus restore, single tabbable treeitem, collapse persisting across a reload,
mouse selection + `aria-selected` intact, zero console errors.

A second dual review of the follow-up diff (subagent + bllm-review-many)
produced two applied fixes — `70e667d` (keyboard toggle left two tabbable
treeitems when the toggled node wasn't the selected one) and `1f9a0f9`
(toggles during an active text filter silently mutated and persisted expand
state; now frozen while filtering, both keyboard and mouse) — plus dismissed
items: the esc()/CSS.escape selector-mismatch claim (verified false — HTML
parsing decodes entities), aria-hidden on the mouse-only toggle (deliberate,
the treeitem carries aria-expanded), unbounded `tcw.treeSeen` growth
(accepted — tens of bytes per path, local tool), cross-tab last-writer-wins
(accepted — single-user localhost), and localStorage error-handling/test
suggestions (best-effort persistence is the established pattern; browser
interaction testing is the existing 2026-07-03 backlog item).
