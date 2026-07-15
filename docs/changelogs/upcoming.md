# Upcoming

Developer changelog for the next version. Technical and precise; grouped by
category, with commit hash ranges so entries trace back to source.

## Fixed

- `FsCapabilitiesStore.set()` and `.update_capability()` resolved through
  `get_local()`, which matches only local, non-override folders, while
  `show`/`list` resolve the federated view through `get()`. Every inherited
  (federated) capability path was therefore printable but unwritable —
  `tcw capabilities set shared/<path> --status Supported` failed with
  `no such capability`, and the web editor's `PATCH /api/capabilities/<ref>`
  refused to save. Both write paths now route through a shared
  `_write_target()` / `_merge_meta()` pair: a local capability writes to its own
  folder; an inherited one writes to its existing override (wherever authored)
  or to a freshly materialized delta mirroring the upstream path, seeded
  `overrides: <alias>/<id>`. Refuses to clobber a local capability already
  occupying the mirrored path. (GitHub issue #3) (4958e5d..HEAD)
- `FsCapabilitiesStore.get_capability_detail()` computed an inherited
  capability's revision from the upstream `meta.yaml`/`description.md` only, so
  two successive edits to the same override hashed identically and
  `StaleRevision` never fired on that path. The revision now also covers the
  local override's files (upstream args first; local capabilities keep their
  two-argument revision unchanged). (4958e5d..HEAD)
- `AmbiguousRef` was raised with the bare ref as its only argument, so callers
  printing `str(e)` emitted an unexplained path (`tcw capabilities show: x/thing`).
  It now carries its own message; `show`, `set`, and the web app's 422 body all
  benefit. (4958e5d..HEAD)

## Added

<changes starting-hash="4958e5d" ending-hash="HEAD">
- On an override, a `None` field value writes an explicit YAML `null` (= clear
  the inherited field, per `_apply_override`) rather than popping the key, which
  would mean "re-inherit". Local nodes keep pop semantics. Reachable through the
  store/web `fields` API; the CLI's `--field K=` still yields `""`.
- Capability `capabilities/set-a-capabilitys-status` (`cap-03f1a5`) — `set` was
  never declared in this project's own ledger. Seeded `Partial` at the planning
  gate (local worked, inherited did not), flipped `Supported` at completion.
</changes>

## Internal

<changes starting-hash="4958e5d" ending-hash="HEAD">
- Federation write coverage in `tests/test_capabilities_federation.py`
  (materialization, in-place reuse of hand-authored overrides, idempotence,
  collision guard, ambiguity, null-clear), inherited web-path coverage in
  `tests/test_store_editor.py` (fields, body, stale revision), and CLI coverage
  in `tests/test_capabilities.py` (the reporter's transcript, ambiguity message).
</changes>
