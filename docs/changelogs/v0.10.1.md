# Upcoming

Developer changelog for the next version. Technical and precise; grouped by
category, with commit hash ranges so entries trace back to source.

## Added

- ddfde06..HEAD — `tcw serve` work board: a status-filter toggle bar above the
  list (`tcw/serve/static/{index.html,app.js,style.css}`). One toggle per work
  status (`inbox`/`backlog`/`active`/`completed`); toggled on ⇒ that status is
  visible; `completed` hidden by default. Pure client-side filtering in
  `currentItems()` (the `/api/work` board already returns every status — no
  backend/API change); the toggle bar renders in the Work view only and composes
  with the existing text filter (AND). `state.statusFilter` is derived from a new
  `WORK_STATUSES` constant so it can't drift from the button set.
- ddfde06..HEAD — Per-status color coding in the same board: a `--st` accent per
  status (violet inbox / amber backlog / teal active / slate completed) shared by
  each list item's status badge and the matching filter toggle, so a status reads
  the same color in both. Falls back to muted for an unexpected status.
