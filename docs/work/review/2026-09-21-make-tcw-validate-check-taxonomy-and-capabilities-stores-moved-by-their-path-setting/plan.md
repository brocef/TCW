# Plan: make tcw validate check taxonomy and capabilities stores moved by their path setting

## Tasks

1. **Presence helper and `_taxonomy`.** Tests first in
   `tests/test_capabilities.py` (criterion 4: check and set against a moved
   taxonomy). Add `tree_store_present` to `tcw/store/fs.py`; rewrite
   `FsCapabilitiesStore._taxonomy` to use it. Proof: red → green; capabilities
   and taxonomy test files green.
2. **validate.** Tests first in a new `tests/test_validate_moved_stores.py`
   (criteria 1, 2, 3, 5, 6, 8), each asserting the specific problem line and, for
   5, no traceback. Then in `tcw/validate.py`: `_tree_roots`, rework
   `_scan_roots` / `_components_to_check` to use it, guard `check()` in
   `_run_check`, shrink block (d) to the YAML-problem case and drop `checked`.
   Proof: red → green; `tests/test_legacy_store_config.py` unchanged and green
   (criterion 7); full suite (criterion 9).

## Documentation Sync

- `docs/changelogs/upcoming.md` [Any-Code-Change], `docs/release-notes/upcoming.md`
  [Public-API]: Fixed entries.
- `docs/guide/linking-and-validation.md` [Guide-Topic-Change]: check whether it
  says validate looks only in `docs/<component>`; update if so.
- README / skills / configure: re-checked on the finished diff.

## Verification

Hands-on: scratch node with a moved taxonomy holding a bad term; compare
`tcw validate` from the installed build (reports nothing) with the worktree's
(reports the term), and the `taxonomy.path`-missing crash before and after.
