# Plan: tree-view column scrolls independently

Single-phase, CSS-only edit to `tcw/serve/static/style.css`. No tests (pure
layout); verified visually in-browser.

## Changes (`tcw/serve/static/style.css`)

1. `.shell` — `min-height: calc(100vh - 78px)` → `height: calc(100vh - 78px)`;
   add `overflow: hidden`.
2. `.list-pane` — add `display: flex; flex-direction: column; overflow: hidden;`
   (keeps `border-right`, `background`, `min-width: 0`).
3. `#list` (`.list`) — add `flex: 1; overflow-y: auto;` (its own scroll region).
4. `.detail-pane` — add `overflow-y: auto;` so long detail content scrolls in its
   own column rather than clipping under the fixed shell.
5. Verify the `@media` single-column breakpoint (`.shell { grid-template-columns:
   1fr }`) still yields natural page scroll on narrow viewports; relax the fixed
   height there if needed (`height: auto; overflow: visible`).

## Verification

- `tcw serve` on a node with a long board; confirm acceptance criteria 1–3
  in-browser (tree scrolls internally; header/filter/detail fixed; detail scrolls
  on long content; resizer works; narrow-viewport reflow intact).
- Re-check `documentation-sync` triggers (expected: none fire).
