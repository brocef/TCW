# Spec — web viewer improvements

Scope: `tcw/serve/` (backend `__init__.py`, frontend `static/app.js`,
`static/index.html`, `static/style.css`), `tcw/cli.py`, and the taxonomy fs
adapter `tcw/store/fs.py` (item 2 only).

Capabilities: no new capability entries. All changes refine the two existing
Supported capabilities `web#browse-tcw-content-in-a-local-web-app` and
`web/editing#edit-tcw-content-in-a-local-web-app`, or restore broken browse
behavior (item 2). Both stay Supported.

The changes group into three buckets: **trivial UI** (3, 8-abridged, 9, 10, 11),
**layout** (1, 8), **one bug fix** (2), and **one coupled feature** — URL routing
+ descendant nodes (4, 5, 6, 7). The coupled feature carries all the design risk.

---

## 1 + 8 · Resizable dividers

Two draggable dividers, same mechanism:

- **List ↔ detail** (`main.shell`, a CSS grid `grid-template-columns: <list> 1fr`).
- **Editor textarea ↔ preview** (`.md-editor`, a CSS grid `1fr 1fr`).

Behavior: a thin grab handle sits on the divider; pointer-drag adjusts the first
track width. Width is driven by a CSS custom property (`--list-width`,
`--md-split`) so the grid template reads from it. Constrained to sane min/max
(the existing `minmax(260px, …)` for the list; ~15–85% for the editor split).
The list width persists across reloads via `localStorage`; the editor split does
not need to persist (it is re-created per edit session). Both `localStorage`
read and write are wrapped in `try/catch` — a `SecurityError` in restrictive
private-browsing modes must degrade to "don't persist", never crash init. On the mobile breakpoint
(`max-width` where `.shell`/`.md-editor` collapse to one column) the handles are
hidden and the CSS var is ignored.

Non-goals: no resize library, no double-click-to-reset, no keyboard resize.

## 3 · Nav button order

`index.html`: reorder the three `.tab` buttons to **Taxonomy · Capabilities ·
Work**. The default active view stays **Work** (unchanged landing behavior — see
routing below; `/` resolves to the Work board).

## 9 · Copy-slug button

Each work-list entry gets a small button that copies the item's **slug** (the
bare slug for local items; the qualified `sub/proj/<slug>` for descendants — i.e.
`itemKey(item)`) to the clipboard via `navigator.clipboard.writeText`, with a
toast confirmation. The returned promise is `.catch()`-ed → a failure toast (the
existing conflict-copy code at app.js already does this — reuse the pattern).
Clicking it must **not** select the item (stop propagation). Work view only.
(127.0.0.1 is a secure context, so `writeText` needs no permission prompt.)

## 10 · Group work list by status

The work list is grouped under status headers in the fixed order **active →
backlog → inbox → completed**. This ordering is distinct from the existing
`WORK_STATUSES` lifecycle order (`inbox, backlog, active, completed`) used by the
status-filter toggles — introduce a separate `WORK_STATUS_GROUP_ORDER` constant so
the two don't get conflated. Within a group, keep the current server order (board
order: priority, then topological). A group with no visible items (all filtered
out, or none exist) renders no header. Status filtering and text filtering still
apply before grouping. Unknown statuses (should not occur) sort after the known
groups.

## 11 · Summary counts

`render()` currently builds: `"{W} work · {T} taxonomy · {C} capabilities"`.
Change to order **taxonomy · capabilities · work** and pluralize work:
`"{T} taxonomy · {C} capabilities · {W} work items"`.

---

## 2 · Fix 500 on inherited taxonomy term (bug)

**Root cause (confirmed):** `FsTaxonomyStore.get_term_detail` (`tcw/store/fs.py`)
does:

```python
term = self.get(ref)          # for an inherited ref, returns a Term with
                              # origin=<alias>, slug=<bare slug in the source store>
d = self.root / term.slug     # BUG: self.root is the *extending* store's root
meta_text = (d / "meta.yaml").read_text(...)   # → FileNotFoundError
```

For an inherited term the meta/description files live under the **source** store's
root (`self.extends[alias].root`), not `self.root`. The missing file raises
`FileNotFoundError` (an `OSError`, not a `ValueError`), which `_map_store_error`
maps to **500**.

**Fix (minimal):** keep the `term` that `self.get(ref)` already returned — it
carries the correct `origin`, `qualified`, and `attachments` — and only redirect
the *file read* to the owning store's root:

```python
term = self.get(ref)
if term is None:
    return None
owner = self if term.origin == "local" else self.extends[term.origin]
d = owner.root / term.slug
...  # read meta.yaml / description.md from d as today
return TermDetail(term=term, core_revision=_revision_multi(...))
```

No recursion into the source store, no re-wrapping / `dataclasses.replace` — the
Term's `origin`/`qualified` are preserved for free, so the UI still renders the
qualified ref and (correctly) refuses to edit it. `update_term` already guards
inherited terms with a clear `ValueError` → 422, so no read/write asymmetry is
introduced. (No other read path has this bug: `list_all`/`get`/`get_inherited`
all read via `_term_via` → the owning `store._term`, and capabilities have no
`extends` federation.)

**Regression test:** a `tmp_path` extending-taxonomy fixture; assert
`get_term_detail("<alias>/<slug>")` returns a `TermDetail` (not raising) with the
inherited term's content and `origin == "<alias>"`, and that the serve route
returns 200 for the qualified ref.

---

## 4 + 5 + 6 + 7 · URL routing & descendant nodes (coupled feature)

### 4 · Auto-include descendants

`tcw serve` includes descendant nodes by default. Implementation: default
`include_descendants` to on (the server already branches on this flag in
`_board`/`_resolve_work`). Remove the now-redundant `--include-descendants` CLI
flag. Bare `tcw serve` at an orchestrator root now shows the anchor board plus
every descendant board, each descendant item's slug qualified as
`sub/proj/<slug>` — identical to `tcw work list --include-descendants`.

Rationale for removing rather than keeping the flag: it becomes a no-op once the
behavior is default, and the tool is young (v0.10.2) with no stable-flag contract
to preserve. The `TcwServer(include_descendants=...)` constructor param stays
(tests and the anchor-only code path still exercise it); only the CLI surface
drops the flag.

### URL scheme

Pattern: `/{namespace}/{axis}/{identifier}` where `{axis}` ∈
`work | taxonomy | capabilities` and `{namespace}` is a (possibly multi-segment)
subproject path or **empty** for the anchor.

| UI state | URL |
|---|---|
| Work board (default) | `/` **and** `/work` |
| Taxonomy list | `/taxonomy` |
| Capabilities list | `/capabilities` |
| Local work item `foo` | `/work/foo` |
| Local taxonomy term `store/adapter` | `/taxonomy/store/adapter` |
| Descendant work item, qualified `sub/proj/foo` | `/sub/proj/work/foo` |

The mapping is exactly: **qualified object ref = namespace + "/" + identifier**,
with the axis keyword inserted between them. Local objects have an empty
namespace. The identifier may itself contain `/` (taxonomy refs like
`store/adapter`) — that's fine, it's simply "everything after the axis keyword".

### Per-segment encoding (required — capability refs contain `#`)

Capability refs carry a `#` heading (e.g. `web#browse-tcw-content-in-a-local-web-app`).
`#` in a URL path starts the *fragment*, which `location.pathname` drops — so a
naive `/capabilities/web#browse-…` would silently lose the heading on reload.
**`pathFor` must `encodeURIComponent` each path segment** (encoding `#`, `%`, `?`),
while joining segments with a *literal* `/` (so a taxonomy ref like `store/adapter`
still renders pretty as `/taxonomy/store/adapter`). **`parsePath` must
`decodeURIComponent` each segment** before use. This mirrors the existing API
layer, which already `encodeURIComponent`s refs (app.js:1585, 1546) and
percent-decodes them server-side. The axis keyword itself is never encoded.

### Parsing (client-side)

`app.js` parses `location.pathname` into `{namespace, axis, identifier}`:

1. Split the path into segments.
2. Scan for the first segment equal to an axis keyword → that's `axis`; segments
   before it are `namespace`; segments after it joined by `/` are `identifier`.
3. No axis keyword found (`/` or empty) → default to `axis = "work"`, no
   identifier (board view).

**Accepted ambiguity (documented):** if a subproject directory is literally named
`work`, `taxonomy`, or `capabilities`, its namespace segment collides with the
axis keyword and the parser would mis-split. This is a pathological naming choice;
we accept it and note it. (Guarding it would mean disallowing those directory
names or adding a sigil, which the user explicitly chose against.)

### Server (History-API fallback)

The server must return `index.html` (200) for GET requests to app routes so a deep
link / reload works. Today unknown GET paths 404. Change: after the static-asset
block and **before** any `/api/` handling (i.e. right after the `/app.js` etc.
branch, before `self._stores()`), add: `if not path.startswith("/api/"): serve
index.html; return`. This is placed early so app-route GETs don't needlessly open
three stores, and it's strictly less code than threading a fallback past every API
branch. Known static assets are matched *before* this line, so they keep serving
their own bytes. API paths keep their existing 404s. Accepted side effect: a
typo'd asset path or `/favicon.ico` returns `index.html` (harmless for a
loopback dev tool). CSP `default-src 'self'` is unaffected.

The mapping between URL identifier and API ref: for a work item the API already
addresses descendants by qualified slug (`sub/proj/foo`), which equals
`namespace + "/" + identifier` — so the frontend reconstructs the API ref by
re-joining namespace and identifier. Taxonomy/capabilities are anchor-only today
(no descendant federation exposed in the URL for those axes in this change);
their namespace is always empty.

### Frontend state ↔ URL sync

- **On load:** parse `location.pathname` into `{axis, selectedKey}`, `await
  load()`, **then** apply the deep-linked selection. Note `load()` currently sets
  `state.selected = null` (app.js:2653) — the deep-linked key must be applied
  *after* `load()` resolves, or `load()` reworked to accept/preserve it; otherwise
  the selection is clobbered. Same ordering applies on the `popstate` path.
- **Missing object:** if the identifier names an object not present, fall back to
  the **list** view for that axis (don't hard-error, and don't auto-open the first
  item). `selectedItem()` today returns `items[0]` on a missed key (app.js:1338) —
  that must not fire for an unresolved deep-link; only default to `items[0]` when
  there is no pending deep-link identifier.
- **On navigation** (tab switch, item select, item deselect): call
  `history.pushState` with the new path so Back/Forward work. `popstate` re-parses
  and re-renders (respecting the dirty-editor guard — a blocked navigation must
  not leave the URL out of sync; restore the URL if the user cancels).
- Creating/dropping/completing items updates the URL to match the resulting view.

Non-goals: no query-string state (filters, status toggles stay in-memory); no
per-axis descendant federation for taxonomy/capabilities beyond what exists.

---

## Cross-cutting

- **No new dependencies.** Dividers, clipboard, routing all use platform APIs
  (pointer events, `navigator.clipboard`, History API, CSS custom properties).
- **CSP** stays `default-src 'self'`; nothing here needs to loosen it.
- **Manual smoke checklist** in `app.js` header comment is extended with the new
  interactions (resize, copy-slug, deep-link load, Back/Forward, grouped list).
