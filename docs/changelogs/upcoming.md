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

<changes starting-hash="9fb3cba" ending-hash="9fb3cba">

### Added

- `WorkStore.epic_completable(item)` (`tcw/store/base.py`): an epic is completable
  when it is `type: epic`, not completed, and has ≥1 initiative child all
  completed — built on `initiative_children` (cross-node), so the signal and the
  `complete` gate share one source of truth.
- `tcw work reconcile --complete-when-ready` (`recursion.py` + `cli.py`):
  auto-completes a ready epic after writing the rollup; the rollup gains a
  "Ready to close" line when completable.
- `tcw work list` annotates a completable epic row with `ready-to-close`.

### Changed

- `WorkStore.complete` (`tcw/store/base.py`): a completable epic may complete
  **directly from `backlog`** (scoped exception — not added to the global
  `LEGAL_TRANSITIONS`; effected via `_effect_transition`). Non-epics and
  non-completable epics are still refused from `backlog`; the open-children and
  blocker gates still run.

</changes>
