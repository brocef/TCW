# Make web UI tree-view column scroll independently

## Requested outcome

In the `tcw serve` web interface, the left column holding the object tree view
should **scroll independently** rather than growing the whole page. Today a long
tree grows the page height, forcing you to scroll the entire page to reach
lower items in the tree. Instead the left column should have its own scroll
region (fixed/viewport-bounded height with internal overflow) so you can scroll
down within the tree without moving the rest of the page.

## Constraints / notes

- Web-UI-only change (CSS/layout in `tcw/serve/`); no model or store change.
- Keep the main content pane behavior intact; only the tree column gets its own
  overflow.

## Status

Captured during the tags planning session (2026-07-17). Not yet planned —
separate from the tags work item. Plan with `/tcw-plan-work` when ready.
