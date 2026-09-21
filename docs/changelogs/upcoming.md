# Upcoming

Developer changelog for the next version. Technical and precise; grouped by
category.

The `v2.5.0` tag was pushed but never published: the release workflow's test job
failed, so the PyPI upload never ran. `v2.5.1` is the first published release
carrying everything listed under `v2.5.0`.

### Changed

- `FsTaxonomyStore.check` and `FsCapabilitiesStore.check`, when not scoped to
  one identifier, report a pre-2.5.0 `config.yaml` / `.config.yaml` left at the
  store root, through the new `FsTreeStore._legacy_config_problems`. It tests
  only that the file exists — never opens, rewrites or deletes it — and names
  the file (relative to the node root, or absolute outside it) and
  `_extends_label()` as where any `extends` belongs. This reverses v2.5.0's
  "not reported by the component `check()`": a project that never moved its
  `extends` silently lost every inherited entry. A retained copy now fails
  `check` and `validate`, and so `tcw work complete` wherever `tcw validate` is
  a `pre` check.
- `validate()` reports that leftover directly for each tree store whose
  `check()` it did not run — a store outside `docs/<component>`, or any run
  whose component checks were skipped after a YAML problem — and, when such a
  store will not open, the open failure once in `_run_check`'s
  `<component> check: <error>` shape. Consequence: a tree store `validate` did
  not check before is now opened on every whole-node run, and any failure to
  open it is reported. On a node with no `docs/<component>` that includes a
  store declared in `<component>.repository` and not yet provisioned (naming
  `tcw provision`, as the work store already did), a `<component>.path` that
  does not exist — for example `../missing-tax` in a CI or cloud clone without
  the sibling checkout (`taxonomy.path is not a directory`) — and an
  inherit-only node whose `<component>.extends` names a project that is not
  reachable (`project 'ghost' is not reachable through connected-projects`).
  Any of these can refuse `tcw work complete` in a project whose `pre` hook
  runs `tcw validate`. The block is marked temporary, to be removed once
  `validate` covers relocated stores generally.
- `FsCapabilitiesStore._override_problem`: `overrides → unknown alias '<alias>'`
  gains `(not declared in <path>/tcw-config.yaml: capabilities.extends)`.

### Fixed

- `tests/test_tracker_cli.py`'s `node` fixture sets `TCW_WORK_OWNER`.
  `test_an_owed_item_can_still_be_started` and
  `test_one_owed_item_does_not_break_lifecycle_moves_on_every_other_item` run
  `tcw work start`, which needs a claimant and otherwise falls back to the git
  identity. The CI runner has none, so both failed there and passed locally.
- `docs/release-notes/v2.5.0.md` linked #43 under the wrong repository.
- `tests/test_taxonomy.py`: the malformed-leftover test asserts the YAML
  parser's own line; `any("config.yaml" in p)` would also have matched the new
  leftover report. The well-formed-leftover test now expects the report.
