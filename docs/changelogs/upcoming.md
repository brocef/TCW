# Upcoming

Developer changelog for the next version. Technical and precise; grouped by
category, with commit hash ranges so entries trace back to source.

## Added

<changes starting-hash="73f50c8" ending-hash="d961c6e">
- Added storage-neutral plan-stage metadata and bounded revision-aware store
  operations, with a filesystem realization under `plan/<id>.md`.
- Added staged-plan manifest and document validation for safe IDs, metadata,
  registered tags, dependency DAGs, headings, presence, and undeclared files.
- Added plan-stage detail payloads and authenticated read, write, delete, and
  open routes, plus React work-detail controls and focused regression tests.
</changes>
