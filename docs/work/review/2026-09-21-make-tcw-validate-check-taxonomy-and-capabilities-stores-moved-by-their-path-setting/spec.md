# Spec: make tcw validate check taxonomy and capabilities stores moved by their path setting

## Capability changes

None. `tcw validate` checks what it always claimed to; no capability wording
depends on the default folders.

## Problem

`tcw/validate.py` finds the two tree stores by their default folder only:

- `_scan_roots` (`validate.py:70-78`) scans `docs/taxonomy` and
  `docs/capabilities` literally for YAML syntax and `tcw://` links.
- `_components_to_check` (`validate.py:105-133`) runs a tree component's check
  only when `docs/<c>` is a directory, and in path mode matches a path only under
  the default folder.
- Block (d) (`validate.py:335-356`) was added as a stopgap: for each tree store
  whose check did not run, it opens the store and reports an open failure or a
  leftover pre-2.5.0 config file.

So a store moved by `<c>.path` or declared by `<c>.repository` is never checked
unless a stray default folder exists.

The same default-folder test sits in `FsCapabilitiesStore._taxonomy`
(`tcw/store/fs.py:3039-3049`), used by the capabilities check (`fs.py:3057`) and
by capability writes (`fs.py:2921`). With the taxonomy moved and no
`docs/taxonomy`, capability Subject/Feature references are silently never
checked, on write or in `check`. With a stray `docs/taxonomy` and a broken
`taxonomy.path`, `FsTaxonomyStore.open` raises `StoreLocationUnusable` from
inside `check()`, and `_run_check` (`validate.py:189-208`) guards only the
capabilities store's own `open`, so `tcw validate` crashes with a traceback (the
folded-in defect).

## Goals

1. A tree store is **present** when its default folder exists **or** the config
   sets `<c>.path` or `<c>.repository` to anything but null (the rule
   `_claims_work` already applies to work). One helper answers this for both
   `validate` and `_taxonomy`.
2. `validate` scans and checks each present tree store at its **resolved** root
   (`STORE_CLASSES[c].open(node_root).root`), resolved once per run; a store that
   cannot open is reported as `<c> check: <reason>`. Path mode matches paths
   under the resolved roots.
3. `_run_check` reports a `ValueError` raised inside `check()` as a problem
   instead of crashing.
4. `_taxonomy` returns the resolved taxonomy store whenever the taxonomy is
   present by rule 1, so Subject/Feature references are checked against a moved
   taxonomy.
5. Block (d) keeps only its YAML-problem half: when a YAML problem skipped the
   component checks, it still reports each present tree store's open failure or
   leftover config, so malformed YAML cannot hide the migration message
   (`tests/test_legacy_store_config.py:255-278`). The "not selected" half and the
   `checked` set go.

## Non-goals

- De-duplicating a store shared by two projects across `tcw validate`'s
  recursion: each project is validated on its own terms (links resolve against
  that node), so each reports it. A test pins this.
- Skipping a scan root that contains the node or its work store (a `<c>.path: .`
  would rescan other files); unusual configuration, left as is.
- A tree store with only `extends` and no folder: still not present, as today.

## Design

In `tcw/store/fs.py`: `tree_store_present(node_root, component) -> bool`
(default folder is a directory, or `<c>.path` / `<c>.repository` set). `_taxonomy`
uses it and then returns the opened store (letting an open failure raise — a
configured taxonomy that cannot open is an error, not "no taxonomy").
In `validate.py`: one `_tree_roots(node_root)` pass returns, per present tree
component, its resolved root or the open error; `_scan_roots`,
`_components_to_check` and block (d) read from it.

## Acceptance criteria

1. A node with `taxonomy.path: tax` (no `docs/taxonomy`) holding a term with a
   problem: `validate` reports that problem, prefixed `taxonomy check:`.
2. Same node, a malformed YAML file under `tax/`: `validate` reports it by path.
3. Same for a capabilities store at `capabilities.path`.
4. With the taxonomy moved and no `docs/taxonomy`, a capability whose Subject
   names an unknown term fails `tcw capabilities check` and `validate`, and
   `tcw capabilities set` with that Subject is refused as it is for a default
   taxonomy.
5. `docs/taxonomy` and `docs/capabilities` present, `taxonomy.path` pointing
   nowhere: `validate` exits 1 listing a problem, no traceback.
6. A node with only `taxonomy.extends` and no taxonomy folder, and a work-only
   node: `validate` output unchanged.
7. The leftover tests in `tests/test_legacy_store_config.py` pass unchanged,
   including the two YAML-skip tests.
8. Two projects whose `taxonomy.path` points at one shared folder: recursive
   `tcw validate` reports that folder's problem once per project.
9. Full suite passes.

## Risks

- `tcw capabilities set`/`update` in a node whose configured taxonomy cannot
  open now fails with that reason instead of skipping the taxonomy check.
  Intended: the same rule as `find_node`.

## Notes

- Design refined with two advisors (Codex, Opus); see `outcome.md`.
