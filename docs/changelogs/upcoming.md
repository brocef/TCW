# Upcoming

Developer changelog for the next version. Technical and precise; grouped by
category.

## Added

- **`work.tracker` inherits from parent nodes, opt-in.** A node whose own
  `work.tracker` is a non-empty mapping takes every key it leaves out from its
  ancestors, direct parent first, including ancestors with no work store.
  - `tcw/store/base.py`: `merge_tracker_blocks` (pure; nearest-first
    `(label, raw)` blocks → merged mapping, a key-path → source-label record, and
    the label of an ancestor block that is not a mapping),
    `tracker_credentials_problem`, and `attribute_tracker_problems`.
  - `FsWorkStore.tracker_config` / `tracker_problems` share `_resolved_tracker`,
    which reads ancestors' `work.tracker` through `FsProjectRegistry.ancestors()`
    and `.config()`. A node whose own block is absent, null or `{}` reads no
    ancestors. On registry `ValueError` it uses the node's own block only.
  - Mappings merge recursively; any other value replaces. A nearer `null` is
    skipped when a farther value exists (and does not move that key's source); a
    lone `null` is kept for the parser to report.
  - `credentials` must come from the same block as `base-url` or a nearer one,
    compared by source, not value. Otherwise no config and one problem.
  - A problem about an ancestor's value is prefixed
    `<ancestor config path> (project '<id>'):`; a problem about the node's own file
    keeps `tcw-config.yaml:`. Matching is on the exact key path, so a required key
    nobody set is blamed on the node being checked.
  - When the merged result has problems and `ancestors()` stopped at a declared
    parent this checkout lacks (at any depth), one more problem names it.
  - New capability `work/inherit-tracker-settings-from-parent-nodes`.

## Changed

- **Upgrade effects of tracker inheritance**, all confined to nodes whose own
  `work.tracker` block is non-empty:
  - A problem in an ancestor's `work.tracker` now disables every such node beneath
    it and is reported by `tcw validate` there. Before, an ancestor without a work
    store was never checked, so a stale or damaged block there went unnoticed.
  - A node that omits `timeout-seconds` now takes an ancestor's value instead of
    the default 15.
  - A node's own `null` value for a key an ancestor sets now takes the ancestor's
    value instead of being reported.
  - A child block holding only some keys (for example only `candidate-query`) is
    rejected as incomplete by v2.1.2 and earlier, which do not inherit.

## Fixed

- **`parse_tracker_config` raised `TypeError` on a block mixing string and
  non-string keys**, from `sorted()` over the unknown keys. It now sorts with
  `key=str` and reports each key. `FsProjectRegistry` had the same defect in its
  unknown `connected-projects` keys message (`tcw/store/project.py`), reachable from
  `tracker_config()` now that it opens the registry; fixed the same way. Six other
  config parsers with the same shape are filed as
  `docs/work/inbox/2026-09-14-config-parsers-crash-on-a-non-string-key.md`.
- **`tcw work tracker import` and `link` could crash after claiming a ticket**
  (released in v2.1.2). `_binding_for` re-read `tracker_config()` after the claim had
  already moved the ticket; if the settings stopped resolving mid-run (with
  inheritance, a parent node's file changing), `None.provider` escaped as an
  `AttributeError` — in `link` outside any handler — leaving the item unbound, and a
  re-run of `import` created a second item. `_binding_for(provider, project, …)` now
  takes the provider and project id the claim was looked up and made with. Tests in
  `tests/test_tracker_import.py`.
- **Docs promised one item per ticket without saying "per node"** (released in
  v2.1.2). `find_binding` searches the current node's store, so importing one ticket
  in two nodes gives two items. `README.md`, `docs/guide/work.md`,
  `skills/tcw-work/references/commands.md` and the
  `work/manage-external-tracker-intake` capability description now scope the promise
  to one node and list the two-node case as an accepted limit.
