# Add a vendored rich Markdown editor to the local web app

## Context

Split out of `2026-07-02-interactive-local-web-editor-for-tcw-objects`. That
item makes `tcw serve` write-capable and ships Markdown editing as a plain
raw-Markdown editor with live preview (reusing the already-vendored
`marked.js`) — deliberately no build pipeline and no new runtime dependency.

This item is the deferred "rich editing" upgrade: replace the raw
textarea+preview with a vendored WYSIWYG-ish Markdown editor.

## Product changes

Provide a richer Markdown editing experience (toolbar, formatting affordances,
optionally WYSIWYG) for the Markdown lifecycle artifacts and body surfaces in
the local web app, without regressing packaging or security.

## Technical changes

- Vendor the editor as static assets served from the installed Python package
  (the `marked.min.js` / `VENDOR.md` pattern); `tcw serve` must work offline
  with **no runtime npm/CDN dependency**.
- Prefer a single-file UMD editor (e.g. EasyMDE / Toast UI Editor) over a React
  package that needs an npm build in the release flow. A build pipeline is only
  acceptable if it emits package-data static assets and is documented. MDX
  Editor was the original candidate; its React/build cost is why this was
  deferred.
- Reuse the write API, revision tokens, dirty-state, and validation surfaces the
  parent item builds — swap the editor widget, not the plumbing.
- Markdown files stay stored as `.md` text; the editor is a presentation layer.

## Meta changes

- Keep the strict `default-src 'self'` CSP; document and narrowly scope any
  unavoidable relaxation (e.g. `style-src 'unsafe-inline'`).
- No new capability is expected — this refines the existing
  `web/editing#edit-tcw-content-in-a-local-web-app` capability's editing surface.

## Open questions for spec

- Which vendored editor best fits the CSP and offline constraints (EasyMDE vs
  Toast UI vs other)?
- Is any CSP relaxation required, and can it be kept narrow?

## Prerequisite

Blocked on the parent item shipping the write API and the raw editor it upgrades.
