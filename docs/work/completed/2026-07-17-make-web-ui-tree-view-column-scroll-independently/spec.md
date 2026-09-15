# Spec: Make the web UI tree-view column scroll independently

Small, CSS-only change to `tcw serve`. No capability delta (this refines the
*presentation* of the existing "browse the object list" capability; it doesn't
change what a user can do), so no `capabilities.yaml`.

## Problem

`.shell` (the two-pane grid) uses `min-height: calc(100vh - 78px)` and grows
with its tallest cell. A long object tree therefore grows the whole page, so
reaching lower tree items means scrolling the entire page — the header and the
detail pane scroll away too.

## Goal

The left list column (`#list`, the tree) gets its own scroll region so a long
tree scrolls **inside the column**. The `.list-head` (title + text filter) and
the status-filter row stay pinned above it. The detail pane keeps working.

## Approach (decided)

App-shell layout — bound the shell to the viewport and let each pane manage its
own overflow:

- `.shell`: `min-height: calc(100vh - 78px)` → `height: calc(100vh - 78px)` +
  `overflow: hidden` so the grid no longer grows the page.
- `.list-pane`: `display: flex; flex-direction: column; overflow: hidden` so its
  head stays fixed and only the tree scrolls.
- `#list`: `flex: 1; overflow-y: auto` — the tree's own scroll region.
- `.detail-pane`: `overflow-y: auto` — **necessary consequence** of a
  viewport-bounded shell: without it, long detail content would clip. This keeps
  the detail pane fully usable (its header/actions scroll with its content, as
  today), it just scrolls within its own column instead of the page. The mobile
  breakpoint (single column, `.shell` → `grid-template-columns: 1fr`) reverts to
  natural page scroll so small screens are unaffected.

Rejected the `position: sticky` + `max-height` alternative (touches only
`.list-pane`): it leaves the page scrolling for the detail pane and pins the tree
column, but the sticky offset interacts awkwardly with the visible header and the
column resizer. The app-shell is the conventional, robust layout and a comparably
small diff.

## Acceptance

1. With a tree taller than the viewport, the tree scrolls inside the left column;
   the header, list-head/filter, and detail pane do not move.
2. The detail pane scrolls independently for long content; nothing clips.
3. The column resizer and existing responsive (single-column) breakpoint still work.
4. No JS, model, or store change.

## Documentation sync

None expected — internal CSS layout only, no public CLI/API/behavior surface
that README/release-notes/changelog/skills describe. (Confirm at completion.)
