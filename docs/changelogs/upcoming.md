# Upcoming

Developer changelog for the next version. Technical and precise; grouped by
category, with commit hash ranges so entries trace back to source.

## Added

<changes starting-hash="de17dee" ending-hash="HEAD">
- `tcw capabilities drift` — read-only report distinguishing inherited-but-
  unreviewed capabilities (status is the federated master's default, never
  locally ruled on) from decided ones, plus local `Missing` capabilities whose
  `Planning doc` names a **completed** work item (declared, shipped, never
  flipped). Exits non-zero when any drift is found. The `Planning doc` scan is a
  read-only follow of an existing capability→work forward pointer and degrades to
  silence when no work node is present. Kept out of `check` so a correctly-
  federated-but-unreviewed node stays structurally valid. (GitHub issue #4)
- `CapabilitiesStore.unreviewed_inherited()` on the abstract interface; the FS
  adapter keys detection on the override index (an override keeps `origin=alias`)
  and requires the override to set `Status`, since one editing only a body/field
  re-inherits the master's status.
- `declared_capabilities()` in `tcw.store.base` — canonical read of a work item's
  `capabilities.yaml` into `{new, changed}`, `added:` read as `new:`, raising
  `SidecarError` on the `_tcw_parse_error` sentinel.

## Changed

<changes starting-hash="de17dee" ending-hash="HEAD">
- `tcw work complete` now **enforces** the DoD "capabilities reconciled" item
  instead of self-attesting it: it fails closed (unless `--force`) when a
  capability the item declared `new:` in its `capabilities.yaml` still reads
  `Missing`, or when any declared `new:`/`changed:` path doesn't resolve.
  `changed:` entries are checked only for resolution (routine body/wording edits
  legitimately leave status alone). Enforced in the CLI `_complete` orchestrating
  an `FsCapabilitiesStore` on the work node — `WorkStore.complete` gains no
  capabilities handle, preserving the loose-pointer boundary. The gate runs
  **after** worktree merge-back, so a flip made on the work branch counts.
  (GitHub issue #4)
</changes>

## Internal

<changes starting-hash="de17dee" ending-hash="HEAD">
- New `tests/test_capabilities_sidecar.py`; drift + gate coverage in
  `test_capabilities.py`, `test_capabilities_federation.py`, and `test_work.py`
  (including a worktree-branch-flip test that pins the gate's post-merge ordering).
- Scope trim vs plan: the `WORK_SIDECARS` validation was **not** tightened —
  `capabilities.yaml` is the only registered sidecar and existing tests use it as
  a generic mapping; the gate's tolerant parser is the real protection.
</changes>
