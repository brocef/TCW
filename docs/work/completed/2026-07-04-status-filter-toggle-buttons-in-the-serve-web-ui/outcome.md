# Outcome — Status filter toggle buttons in the serve web UI

Work completed successfully. Client-side-only change to the `tcw serve` web board;
no backend/API change (no abstraction-litmus concern).

## What changed

- **Toggle bar** (`index.html`, `app.js`, `style.css`): a row of per-status toggle
  buttons above the work list (`inbox`/`backlog`/`active`/`completed`). On ⇒ that
  status is visible; `completed` hidden by default. `currentItems()` filters by
  `state.statusFilter` (derived from a new `WORK_STATUSES` constant); the bar
  renders in the Work view only and composes with the text filter (AND).
- **Per-status colors** (follow-on in the same item): a `--st` accent per status
  (violet inbox / amber backlog / teal active / slate completed) shared by each
  item's status badge and the matching toggle; muted fallback for an unexpected
  status.

## Verification

- Driven live in the browser against this repo's board (44 items): default shows
  13 (12 backlog + 1 active), 0 of 31 completed; toggling `completed` on → 44;
  bar hidden in Taxonomy/Capabilities; composes with text filter (0 completed
  leaked while text-filtering); badge/toggle classes + resolved colors confirmed
  (violet/amber/teal/slate).
- `pytest tests/test_serve.py tests/test_serve_descendants.py` → 16 passed
  (static assets serve; no Python behavior touched).
- `bllm-review-many` run twice (toggle logic, then colors). Applied one
  improvement (derive `statusFilter` from `WORK_STATUSES`); other findings
  dismissed as misreads / pre-existing patterns / graceful degradation, all
  confirmed against the browser (e.g. the meta string is inserted via `.innerHTML`,
  so badges render styled).

## Notes / deferred (not TCW items)

- No JS test harness exists in the repo; frontend verified by browser drive.
- Deferred (not requested): persisting toggle state across reloads; per-status
  counts on the toggles.
- No capability delta: `web#browse-tcw-content-in-a-local-web-app` already covers
  viewing the board; status filtering + coloring is a UI refinement within it.

## Closeout (user-approved)

Complete the item, then cut a **patch** (0.10.0 → 0.10.1).
