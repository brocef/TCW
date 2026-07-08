# Implementation plan — web viewer improvements

Ordered so the isolated, low-risk changes land first and the coupled routing
feature (which touches the most surface) lands last. Each phase is a coherent
commit. `tcw work start <slug>` before the first code edit (that transition is the
first commit).

Files in play: `tcw/store/fs.py`, `tcw/serve/__init__.py`,
`tcw/serve/static/{index.html,app.js,style.css}`, `tcw/cli.py`, plus tests under
`tests/` and the docs listed in Phase 6.

---

## Phase 1 · Taxonomy inheritance 500 fix (item 2)

1. `tcw/store/fs.py` `get_term_detail`: pick the owning store's root for the file
   read (`owner = self if term.origin == "local" else self.extends[term.origin]`;
   `d = owner.root / term.slug`) and keep the already-correct `term` from
   `self.get(ref)` — no re-wrap. See spec §2 for the snippet.
2. Test: `tests/` — build a genuine federation fixture (an extending taxonomy whose
   `config.yaml` declares `extends: {<alias>: <relative-repo-path>}` pointing at a
   second node's `docs/taxonomy`). The existing `get_term_detail` tests are
   local-only, so this inherited fixture is new. Assert `get_term_detail(
   "<alias>/<slug>")` returns detail (no raise) with the source term's content and
   `origin == "<alias>"`; add a serve-route test asserting 200 (not 500) for
   `GET /api/taxonomy/<alias>%2F<slug>`.

Self-check (ponytail): the new test is the runnable check — it fails if the root
resolution regresses.

## Phase 2 · Trivial UI (items 3, 9, 11)

3. `index.html`: reorder `.tab` buttons → Taxonomy · Capabilities · Work.
4. `app.js` `render()`: summary string → `"{T} taxonomy · {C} capabilities · {W}
   work items"`.
5. `app.js` `renderList()`: add a copy-slug button per work entry (work view
   only); `navigator.clipboard.writeText(itemKey(item)).then(toast).catch(toast)`
   (reuse the conflict-copy pattern); stop click propagation so it doesn't select
   the row. Minimal CSS for the button.
6. Test: none required (presentational). Manual smoke covers it.

## Phase 3 · Grouped work list (item 10)

7. `app.js`: add `WORK_STATUS_GROUP_ORDER = ["active","backlog","inbox",
   "completed"]` (distinct from `WORK_STATUSES`). In `renderList()`, when
   `state.view === "work"`, render items under status-group headers in that order;
   skip empty groups; preserve server order within a group; status + text filters
   apply first. Non-work views unchanged.
8. Minimal CSS for the group header.
9. Manual smoke: toggle statuses, filter, confirm grouping + order.

## Phase 4 · Resizable dividers (items 1, 8)

10. `style.css`: drive `.shell` first track from `--list-width` and `.md-editor`
    from `--md-split`; add grab-handle styling; hide handles at the mobile
    breakpoint.
11. `app.js`: a small `makeResizable(gridEl, cssVar, {min,max,persistKey})` helper
    using pointer events (pointerdown/move/up, pointer capture). Wire the list
    handle (persist `--list-width` to `localStorage`, both read and write wrapped
    in `try/catch` so a `SecurityError` degrades to no-persist, never crashes) and
    the editor handle (no persistence; re-wired each time an editor renders).
    Clamp to min/max.
12. Self-check: a tiny assert-style DOM check is impractical headless; rely on the
    manual smoke checklist entry (drag list handle; drag editor handle; reload
    restores list width; mobile hides handles).

## Phase 5 · URL routing & descendant auto-include (items 4, 5, 6, 7)

13. **CLI/default (item 4):** `tcw/cli.py` — remove the `--include-descendants`
    argument **and** the `args.include_descendants` read at `_cmd_serve`
    (cli.py:57, else `AttributeError`); `_cmd_serve` passes
    `include_descendants=True`. Keep the `TcwServer(include_descendants=…)`
    constructor param. `tests/test_serve_descendants.py` drives the constructor
    directly (both states), so it stays green — verify no test invokes
    `main(["serve", "--include-descendants"])`.
14. **Server SPA fallback:** `tcw/serve/__init__.py` `_get()` — right after the
    static-asset block and **before** `self._stores()`, add `if not
    path.startswith("/api/"): serve index.html (200); return`. Static assets are
    matched above this line (keep their own bytes); `/api/` 404s unchanged.
15. **Frontend router:** `app.js` —
    - `parsePath(pathname) -> {axis, namespace, identifier}` per spec: split, scan
      for the first axis keyword, `decodeURIComponent` each segment; none → work
      board.
    - `pathFor(view, selectedKey) -> string` inverse: `encodeURIComponent` each
      segment, join with literal `/`, insert the axis keyword between namespace and
      identifier; anchor namespace empty. (Encoding is required — capability refs
      carry `#`; see spec.)
    - On load: parse → `await load()` → **then** apply the deep-linked selection
      (`load()` resets `state.selected` to null, so order matters). If the
      identifier resolves to no object, show that axis's list (do not auto-open
      `items[0]`; guard `selectedItem()`'s fallback against a pending deep-link).
    - Replace tab-click / item-select / deselect handlers to `history.pushState`
      the new path; add a `popstate` handler that re-parses and re-renders,
      honoring the dirty guard (restore the prior URL if the user cancels a
      blocked navigation).
    - Create/drop/complete update the URL to the resulting view.
16. Tests: server tests — a non-API, non-asset GET (`/work/foo`, `/taxonomy`)
    returns 200 with the `index.html` body; `/app.js` and `/style.css` still
    return their own bytes (not index.html); `/api/does-not-exist` still 404s.
    Frontend routing is covered by the manual smoke checklist round-trips:
    taxonomy `store/adapter`, descendant `sub/proj/work/foo`, and capability
    `web#…` (the `#`-encoding case). (Repo is pytest-only; no JS test runner, so
    `parsePath`/`pathFor` rely on the checklist — call that out explicitly.)
17. Manual smoke: load `/taxonomy` directly; load `/work/<slug>` directly; select
    a descendant item and confirm URL `/sub/proj/work/<slug>` + reload restores it;
    Back/Forward; dirty-editor guard keeps URL in sync on cancel.

## Phase 6 · Docs sync (documentation-sync gate)

Run the `skill-cefailures:documentation-sync` skill; expected triggers:

18. `README.md` [Public-API] — `tcw serve` now includes descendants by default;
    the `--include-descendants` flag is removed. This is a definite edit: the flag
    is documented at README ~214/217/219 (a paragraph, not one line). (Leave the
    separate `tcw work list --include-descendants` docs at README ~350/394
    untouched — different, unchanged CLI.)
19. `skills/tcw-work/SKILL.md` [Skill-Driven-Component] — definite edit: the quick
    reference at SKILL.md:82 mentions `tcw serve --include-descendants`. Update to
    reflect the now-default behavior / removed flag.
20. `docs/release-notes/upcoming.md` [Public-API] — plain-language notes:
    resizable panes, shareable/deep-linkable URLs, subproject items shown
    automatically, copy-slug button, status-grouped board, fixed inherited-term
    view.
21. `docs/changelogs/upcoming.md` [Any-Code-Change] — technical, grouped
    (Added/Changed/Fixed/**Removed** — the flag), with the commit-hash range.

## Verification (before completion)

- `pytest` green (new Phase 1 + Phase 5 server tests included).
- Run `tcw serve` against a fixture orchestrator+subproject repo; walk the full
  manual smoke checklist (extended in the `app.js` header comment).
- Capabilities: `web#browse-…` and `web/editing#edit-…` stay Supported — no ledger
  flip needed; confirm at completion.

## Sequencing notes

- Phases 1-4 are independent and could be reordered; 5 depends on nothing but is
  the riskiest, so it's last.
- Only Phase 5 changes the public CLI surface (flag removal) and server routing —
  the parts most worth a careful review.
