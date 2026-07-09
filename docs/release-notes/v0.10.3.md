# Upcoming

User-facing release notes for the next version. Plain language — no jargon or
internal module names.

## A better local web viewer

The `tcw serve` web app got a round of improvements:

- **Shareable, bookmarkable URLs.** The address bar now reflects what you're
  looking at — `/taxonomy`, `/work/my-item`, and so on — so you can copy a link
  straight to an item, reload without losing your place, and use the browser's
  Back and Forward buttons.
- **Subprojects show up automatically.** When you serve a project that contains
  other TCW projects, their items now appear alongside the main project's, each
  clearly namespaced in its URL. (No flag needed — this used to require
  `--include-descendants`, which has been removed.)
- **Resizable panels.** Drag the divider between the list and the content area to
  widen either side; the Markdown editor's write/preview split is draggable too.
- **Work board grouped by status.** Work items are now grouped under headers in the
  order active → backlog → inbox → completed.
- **Copy a slug in one click.** Each work item in the list has a small button to
  copy its slug to your clipboard.
- **Tidier header.** The tabs and the counts under "TCW" now read in the natural
  order — Taxonomy, Capabilities, Work — and the work count says "work items".

### Fixed

- Opening a taxonomy term that a project **inherits** from another project no longer
  errors out — it now displays correctly.
- Working with epics in a multi-repo workspace no longer hangs. Completing,
  reconciling, or listing nodes across projects that have `node_modules` (or other
  dependency folders) is now fast, and completing an epic no longer needs `--force`
  to get past the slowdown — so its open-children safety check keeps working.
