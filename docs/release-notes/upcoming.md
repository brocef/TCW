# Upcoming

User-facing release notes for the next version. Plain language — no jargon or
internal module names.

## Changed

- Structured reference fields in the local web editor now search Work,
  Taxonomy, and Capability objects as you type. Results show names and canonical
  identifiers, support keyboard and pointer selection, and retain free-form
  entry where it was already allowed.
- Every object, lifecycle artifact, and sidecar saved in the web editor is now
  checked immediately. Validation issues are shown without pretending the save
  failed, and the notice clears after a later clean save.
- `tcw serve` now uses a packaged Fastify server and React client while keeping
  the same command options and local editing experience. It requires Node.js
  22.12 or newer; all other TCW commands remain Python-only.
- The three-pane browser editor is now implemented entirely in TypeScript and
  React, including navigation, filters, Markdown previews, editing, lifecycle
  actions, validation, dirty-draft protection, and stale-write recovery.
- Taxonomy and Capability entries now fill the list-column width consistently
  with Work entries and use the same vertical spacing instead of rendering as
  awkward narrow or crowded buttons.
- The create control now appears above the object list in the Taxonomy,
  Capabilities, and Work views, so it stays in a consistent, easy-to-find place.
- The local web app still works offline after installation. Users do not need
  pnpm, `node_modules`, or a frontend build because the web assets ship with TCW.
- Startup and shutdown now supervise a private authenticated Python API and the
  browser-facing server together, with clearer errors for missing Node, old
  Node versions, missing assets, port conflicts, and child-process failures.
