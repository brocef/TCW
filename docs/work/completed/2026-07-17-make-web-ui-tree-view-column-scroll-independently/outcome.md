# Outcome: tree-view column scrolls independently

Work completed successfully. CSS-only change to `tcw serve`; verified in-browser.

## What changed

`tcw/serve/static/style.css` only:

- `.shell` — `min-height: calc(100vh - 78px)` → `height: calc(100vh - 78px)` +
  `overflow: hidden`, so the two-pane grid is viewport-bounded instead of growing
  the page.
- `.list-pane` — `display: flex; flex-direction: column; overflow: hidden`, so the
  head (title/filter/status) stays fixed above the tree.
- `.list` — `flex: 1; overflow-y: auto; align-content: start`, giving the tree its
  own scroll region packed at the top.
- `.detail-pane` — `overflow-y: auto`, so long detail content scrolls in its own
  column (necessary once the shell is viewport-bounded).
- `@media (max-width: 760px)` — reverts `.shell`/`.list-pane`/`.list`/`.detail-pane`
  to `overflow: visible` / `height: auto` so the single-column layout keeps natural
  page scroll on narrow screens.

## Verification performed

In-browser (`tcw serve` on this repo's 58-item board):

- The tree scrolls **inside the left column** to "+ Create Work" while the app
  header, the "Work / Filter" head, and the status toggles stay pinned; the column
  shows its own scrollbar. ✓
- Opening a long item detail and scrolling the right pane moves only the detail
  content — the tree column keeps its own scroll position and the header stays
  fixed; nothing clips. ✓
- No console errors.

Not re-tested at the narrow breakpoint, but the added `overflow: visible` /
`height: auto` overrides restore the pre-change single-column behavior.

## Deviations from plan

None. `.detail-pane { overflow-y: auto }` was included as the spec/plan already
anticipated (necessary consequence of the viewport-bounded shell), plus
`align-content: start` on `.list` so the grid rows don't stretch to fill the
now-taller scroll container.

## Follow-up notes

None. No model/store/JS change, no capability delta, no docs trigger fires
(internal CSS layout only).
