# Status filter toggle buttons in the serve web UI

Small, client-side-only frontend tweak — planning compressed into this one
artifact (no separate spec.md; the plan is below).

## Requested outcome

Make it easy to filter the `tcw serve` work board by status. Above the left
column of work items, show a row of **toggle buttons — one per status**
(`inbox`, `backlog`, `active`, `completed`). A status toggled **on** means items
with that status are visible. **Default: `completed` hidden** (the other three
on).

## Approach (compact plan)

Pure client-side filtering — the `/api/work` board already returns every status;
no backend/API change, so no abstraction-litmus concern.

- **`index.html`** — add a `#status-filters` container between `.list-head` and
  `#list`.
- **`app.js`** —
  - `state.statusFilter = { inbox: true, backlog: true, active: true, completed: false }`
    plus a `WORK_STATUSES` constant.
  - `currentItems()` — for the work view, also drop items whose
    `statusFilter[item.status] === false` (unknown statuses stay visible).
  - `renderStatusFilters()` — render the toggle bar for the work view only
    (hidden for taxonomy/capabilities); each button reflects/flips
    `state.statusFilter[status]` and re-renders. Called from `render()`.
- **`style.css`** — `.status-filters` row + `.status-toggle` pill styled off the
  existing `.tab` pattern (on = accent fill, off = ghosted/muted).

Non-goals: persisting toggle state across reloads (resets to completed-hidden);
per-status counts; server-side status filtering; taxonomy/capabilities filtering.

## Verification

Drive `tcw serve` in a browser against this repo's own board (has items across
backlog/completed): toggles present in Work view only; completed hidden by
default; toggling `completed` on reveals completed items; text filter still
composes (AND).

## Docs

Frontend behavior of `tcw serve` → README `tcw serve` section + changelog /
release notes at closeout.
