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

## Changed

- fde8c28..HEAD — Refactored work-board stage-letter rendering to use the new
  work-store artifact surface while preserving the visible `tcw work list`
  output.
