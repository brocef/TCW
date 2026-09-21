# Upcoming

Developer changelog for the next version. Technical and precise; grouped by
category.

The `v2.5.0` tag was pushed but never published: the release workflow's test job
failed, so the PyPI upload never ran. `v2.5.1` is the first published release
carrying everything listed under `v2.5.0`.

### Added

- `capability_gate` (`tcw/work/recursion.py`) checks child-qualified
  `capabilities.yaml` paths: a first segment naming a project declared under
  `connected-projects.children` routes the rest of the path to that child's
  ledger, via `get` for `new:`/`changed:` and `get_local` for `removed:`. The
  rule lives in the new public `route_capability_path` (returns a `Route` or a
  problem string), intended for reuse by the early sidecar check (GitHub #27).
  Order: an `extends` alias of the node's own ledger wins; then a declared child
  (refused as ambiguous when the node's resolved view, inherited entries
  included, lists anything under that namespace); then the node's own ledger.
- `tcw work complete`'s remedy line and discard hint say to reconcile a
  child-qualified path inside the child.

### Changed

- An unqualified path on a node with no ledger is refused (it used to pass
  silently); the message lists the node's declared children.
  `test_complete_gate_work_only_node_unaffected` is now
  `test_complete_gate_work_only_node_refuses_an_unqualified_path`.
- A `removed:` path whose first segment is an `extends` alias of the routed
  ledger is refused, since `rm` deletes only local capabilities; it used to pass
  because `get_local` found nothing at the literal path.
- The gate reads `capabilities.yaml` before opening the registry or any store,
  and turns every `ValueError` from `FsCapabilitiesStore.open` or
  `FsProjectRegistry.require_valid` into one problem line per declared path, so a
  discard is never aborted by a store failure.

### Fixed

- `capability_gate` found a ledger only at `<node root>/docs/capabilities`, so a
  ledger moved by `capabilities.path` or declared by `capabilities.repository`
  was never checked. It now asks the resolved store, as `find_node` does (part 1
  of `2026-09-15-make-the-capability-gate-honor-a-configured-ledger`).
- `tests/test_tracker_cli.py`'s `node` fixture sets `TCW_WORK_OWNER`.
  `test_an_owed_item_can_still_be_started` and
  `test_one_owed_item_does_not_break_lifecycle_moves_on_every_other_item` run
  `tcw work start`, which needs a claimant and otherwise falls back to the git
  identity. The CI runner has none, so both failed there and passed locally.
- `docs/release-notes/v2.5.0.md` linked #43 under the wrong repository.
