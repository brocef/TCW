# Upcoming

Developer changelog for the next version. Technical and precise; grouped by
category, with commit hash ranges so entries trace back to source.

<changes starting-hash="8449745" ending-hash="8449745">

### Added

- `CapabilitiesStore.reset(identifier)` (abstract) + `FsCapabilitiesStore.reset`
  (`tcw/store/fs.py`): drop a local override folder and re-inherit the upstream
  capability; fail-closed with distinct messages for a standalone-local path
  (use `remove`) vs. an un-overridden inherited path; resolves the override by
  upstream id (`_override_index`) so it finds bare or alias-qualified placements;
  never mutates the extended store.
- CLI `tcw capabilities reset <path>` (`tcw/capabilities/cli.py`).
- New capability `capabilities/reset-an-override`.

</changes>
