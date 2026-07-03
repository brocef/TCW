# Upcoming

User-facing release notes for the next version. Plain language — no jargon or
internal module names.

## Added

- Added `tcw serve`, a local read-only web app for browsing a node's Work board,
  Taxonomy tree, and Capabilities ledger from a browser.

## Changed

- The `tcw serve` web app is now fully interactive — you can create and edit
  Work items (including Markdown bodies, lifecycle artifacts, and the
  `capabilities.yaml` sidecar via a Markdown editor with live preview), Taxonomy
  entries, and Capabilities directly from the browser. Work lifecycle actions
  (start, complete, drop) are available in the UI. The server remains loopback-only;
  all writes require JSON content-type and a loopback origin for safety.
  Concurrent stale edits are rejected to prevent accidental overwrites.
