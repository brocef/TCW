# Upcoming

Developer changelog for the next version. Technical and precise; grouped by
category, with commit hash ranges so entries trace back to source.

## Added

- fde8c28..HEAD — Added `tcw serve`, a loopback-only read-only HTTP viewer with
  JSON endpoints for work, taxonomy, and capabilities plus packaged static
  assets.
- fde8c28..HEAD — Added `WorkStore.artifacts()` and
  `WorkStore.artifact_locator()` so lifecycle artifact presence and openable
  handles are available through the abstract work-store surface.
- 14371ca..HEAD — Added abstract store edit surfaces: `create_work`/`update_work`
  (composite, prevalidated), `update_term` (taxonomy), `update_capability` and
  `add_entry` (capabilities), plus per-resource revision tokens and stale-write
  rejection. Introduced `WORK_SIDECARS` and `TAXONOMY_EDITABLE_FIELDS` registries
  to bound editable resources.
- 14371ca..HEAD — Added `tcw serve` write API: POST/PATCH/PUT/DELETE routes for
  all three axes; artifact and sidecar read/write with JSON envelopes; lifecycle
  action routes (start/complete/drop); sidecar discovery endpoint; `dodChecklist`
  in work detail responses; post-write `check()` warnings for taxonomy and
  capability writes. All writes enforce `Content-Type: application/json` +
  loopback `Host`/`Origin`, 1 MiB `MAX_BODY_BYTES` pre-parse guard, and 409 on
  stale revision tokens.
- 14371ca..HEAD — Added interactive frontend editor framework: view/edit/create
  state machine with dirty state and save-in-progress tracking; raw-Markdown
  `<textarea>` + live `marked.js` preview pane; generic structured-field renderer;
  revision tokens carried in editor state with 409 conflict recovery (draft
  preserved, server version fetched); `beforeunload` + app-level dirty-navigation
  guards. Axis-specific flows: work create/edit forms (all fields + blocked-by),
  lifecycle artifact and `capabilities.yaml` sidecar editors, lifecycle action
  buttons (complete modal with DoD acks + capabilities reconciliation reminder,
  drop confirmation, blocker/force handling); taxonomy and capability create/edit
  forms with post-write check warnings surfaced inline.

## Changed

- 14371ca..HEAD — Refactored CLI `tcw work new` and `tcw work edit` to use the
  shared store `create_work`/`update_work` methods so CLI and web validation
  cannot diverge.
- fde8c28..HEAD — Refactored work-board stage-letter rendering to use the new
  work-store artifact surface while preserving the visible `tcw work list`
  output.
