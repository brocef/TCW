Work completed successfully.

## Result

- Added the storage-neutral `ProjectRegistry` contract and filesystem
  `FsProjectRegistry` implementation with canonical project IDs, opaque
  locators, reciprocal parent/child relations, ID lookup, ancestors,
  descendants, strict YAML shapes, duplicate-key rejection, deterministic
  validation, and per-registry config caching.
- Replaced directory/git discovery in topology operations with declared graph
  traversal. Registered projects can be nested, siblings, absolute-path
  out-of-tree nodes, or any mixture; valid unregistered nodes and decoy trees are
  not visited.
- Added explicit `--id` behavior to top-level and component init commands,
  including legacy marker backfill, configuration preservation, idempotence,
  conflict rejection, and fail-closed command bootstrapping.
- Migrated descendant work addressing, boards, node display, initiative
  coordination, delegation/escalation metadata, reconciliation, web hosting, and
  `tcw://` work resolution to canonical project IDs.
- Migrated taxonomy and capability federation from alias/path maps to explicit
  registered project-ID lists. The source ID is the inherited namespace;
  connections do not imply inheritance.
- Made `tcw validate [path]` validate the complete current project graph before
  bounded YAML, reference, and component checks.
- Added the `connected-project-registry` taxonomy Feature over `node`,
  `namespace`, and `reference`; linked all eight changed capabilities and
  updated their bodies.
- Updated the README, breaking migration guide, release notes, changelog,
  taxonomy descriptions, and the `tcw-work`, `tcw-taxonomy`, and
  `tcw-capabilities` skills.

## Verification

All checks passed on 2026-07-20:

```text
python -m pytest -q
648 passed in 132.97s

tcw capabilities check
capabilities OK

tcw taxonomy check
taxonomy OK

tcw validate
validate OK

python -m pytest tests/test_plugin_manifests.py -q
4 passed in 0.01s

git diff --check
passed
```

Focused coverage includes ID creation/backfill/conflicts, invalid and reserved
IDs, malformed/duplicate YAML, missing and mismatched targets, nonreciprocal
edges, multiple relation shapes, cycles, relative/absolute/arbitrary layouts,
transitive ancestry/descendants, unregistered decoys, no-scan topology,
project-ID-qualified work flows, web routes and actions, explicit federation,
overrides, `tcw://` resolution, and narrowed validation that still checks the
whole graph.

All eight paths in `capabilities.yaml` resolve and carry
`Feature=connected-project-registry`. Documentation Sync triggers were
evaluated: `README.md`, upcoming release notes, upcoming developer changelog,
and all three changed component-driving skills were updated.

## Deviations from plan

- The filesystem registry lives in the focused `tcw/store/project.py` module
  rather than adding more topology code to `tcw/store/fs.py`.
- Existing adapter-level test helpers retain a stable fixture ID when invoked
  directly without one. The public `tcw init` and all component mirrors still
  require `--id` for new or legacy markers and never infer an ID.
- The planned major release has not been cut. Per the lifecycle and user
  instruction, completion and release remain gated on explicit acceptance.

## Follow-up notes

- Project ID renames remain a coordinated manual migration with no alias.
- Remote/URL locators and version-pinned remote inheritance remain out of scope.
- Historical completed work and versioned release notes retain their original
  descriptions of behavior at those versions; live guidance is migrated.
