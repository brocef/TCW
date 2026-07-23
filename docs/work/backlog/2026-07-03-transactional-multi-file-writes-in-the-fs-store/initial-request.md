# Transactional multi-file writes in the Fs store

## Origin

Dual-review finding #9 on `2026-07-02-interactive-local-web-editor-for-tcw-objects`
(accepted for v1). Only bites on mid-write I/O failure; inputs are prevalidated
first, so it does not fire on validation errors.

## Problem

Some store operations write two files sequentially, each atomically, but with no
transaction spanning both:

- `FsWorkStore.create_work` — `state.yaml` then `initial-request.md`
  (`tcw/store/fs.py`, still `mkdir` → `_atomic_write` → `_atomic_write` with no
  rollback on the second failure).
- **`FsTreeStore._write_node`** — `meta.yaml` then `description.md`. The
  original request named `FsTaxonomyStore.update_term`; that write now routes
  through this shared helper, which **both the taxonomy and capabilities stores
  use**. Fixing it there covers `update_term`, `update_capability`, and every
  other folder-node create/update in one place — do not patch `update_term`
  directly.

If the process fails between the two writes (disk full, permission, crash), the
object is left half-written (e.g. `state.yaml` present, body missing).

## Desired outcome

Make each multi-file object create/update leave the store either fully updated or
unchanged on a mid-write failure — e.g. write all temp files first, then atomically
promote them, and on `create_work` failure remove the partially-created directory.

## Notes

- Keep it inside the `Fs*` adapters (no abstract-interface change).
- Add fault-injection tests (mirror the existing `_atomic_write` failure tests):
  fail the second write and assert the object is absent/unchanged, not partial.
