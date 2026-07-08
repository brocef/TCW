# Upcoming

Developer changelog for the next version. Technical and precise; grouped by
category, with commit hash ranges so entries trace back to source.

## Web viewer improvements (`tcw/serve/`)

Commit range: `494d693..HEAD` (branch `web-viewer-improvements`).

### Added
- URL routing via the History API: the SPA reflects UI state in `location.pathname`
  (`/taxonomy`, `/work/<slug>`, descendant `/sub/proj/work/<slug>`), with
  deep-linking, Back/Forward, and a `popstate` handler that honors the dirty-editor
  guard. Scheme `/{namespace}/{axis}/{identifier}`; anchor namespace is empty; each
  segment is percent-encoded (capability refs contain `#`). `app.js`:
  `parsePath`/`pathFor`/`applyRoute`/`routedInit`.
- Server SPA fallback: any non-`/api/`, non-static GET serves `index.html`
  (`tcw/serve/__init__.py` `_get`), so deep links / reloads resolve.
- Resizable splits: the list/detail divider and the editor/preview split are
  drag-resizable via a shared `makeResizable` pointer-events helper; list width
  persists to `localStorage` (best-effort, `try/catch`). CSS vars `--list-width`,
  `--md-split`.
- Copy-slug button on each work-list row (`navigator.clipboard.writeText`, with a
  `.catch` failure toast).

### Changed
- `tcw serve` aggregates descendant node boards **by default** (previously behind a
  flag) — matches `tcw work list --include-descendants`.
- Work list is grouped under status headers in `active → backlog → inbox →
  completed` order (`WORK_STATUS_GROUP_ORDER`, distinct from the lifecycle-ordered
  `WORK_STATUSES`).
- Top-nav button order and the header counts are now taxonomy · capabilities ·
  work; the work count reads "{N} work items".
- List no longer auto-opens the first item; a bare list URL shows an empty detail
  pane until an item is selected (`selectedItem` drops its `items[0]` fallback).

### Fixed
- Inherited taxonomy term detail returned 500: `FsTaxonomyStore.get_term_detail`
  read `meta.yaml`/`description.md` under the extending store's root instead of the
  source store's, raising `FileNotFoundError`. It now reads from the owning store's
  root while preserving the term's `origin`/`qualified`. (`tcw/store/fs.py`)

### Removed
- `tcw serve --include-descendants` flag (now the default behavior).
