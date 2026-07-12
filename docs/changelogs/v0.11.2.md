# Upcoming

Developer changelog for the next version. Technical and precise; grouped by
category, with commit hash ranges so entries trace back to source.

## Added

<changes starting-hash="23fd7f1" ending-hash="HEAD">
- `tcw work inbox list|show|accept` and abstract inbox entry/resource operations,
  with atomic filesystem acceptance into generated backlog artifacts and bounded
  attachments.
</changes>

## Removed

<changes starting-hash="23fd7f1" ending-hash="HEAD">
- `inbox` from `WORK_STATUSES`, legal work-item transitions, start/drop behavior,
  and the web board's formal status controls.
</changes>
