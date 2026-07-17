# Upcoming

Developer changelog for the next version. Technical and precise; grouped by
category, with commit hash ranges so entries trace back to source.

## Added

- `tcw/serve/static/tree.js` — pure (no-DOM) tree-model module for the web UI:
  `buildPathTree` (taxonomy/capabilities path tries), `buildWorkTree`
  (parent-relation nesting with in-namespace resolution of qualified
  `sub/proj/<slug>` keys), `pruneTree` (match-or-visible-descendant filter that
  reports force-expand ancestor paths), `ancestorsOf`, and `mergeExpansion`.
  Exported both as `window.TCWTree` (classic script) and guarded CommonJS for
  `node --test tests/tree.test.mjs` (17 tests, zero new dependencies).
  (1aa7712..HEAD)

## Changed

- The web UI's left-column object list renders as a **collapsible hierarchy
  tree** on all three axes instead of a flat list. Content-less path segments
  (e.g. the `capabilities/`, `cli/` prefixes) are non-selectable folder labels;
  a node can be both selectable and a parent (`web` → `web/editing`).
  Expand/collapse state is per-axis session memory; new parents default to
  expanded; selection and deep links auto-expand ancestors. The text filter and
  work status toggles apply as a tree prune (match or has-visible-descendant),
  so a filtered-out parent of a visible child stays reachable, rendered dimmed
  (`.ancestor-dim`). The Work board no longer shows status group headers —
  status toggles and per-row badges remain; `groupedWorkHtml`,
  `WORK_STATUS_GROUP_ORDER`, and `currentItems` retired. (1aa7712..HEAD)
