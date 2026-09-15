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
- **`FsTreeStore._write_node`** (`fs.py:625-631`) — `meta.yaml` then
  `description.md`. The original request named `FsTaxonomyStore.update_term`; that
  write now routes through this shared helper, which **both the taxonomy and
  capabilities stores use**. Fixing it there covers `update_term`,
  `update_capability`, and every other folder-node create/update in one place —
  do not patch `update_term` directly. Five call sites today: `fs.py:748`, `977`,
  `1229`, `1614`.
- **`FsWorkStore.create`** (`fs.py:2288-2295`) — added 2026-07-28. Worse than the
  two above: it uses plain `write_text` + `dump_yaml`, not even `_atomic_write`,
  so neither file is individually atomic. Declared abstract at `base.py:931`.

If the process fails between the two writes (disk full, permission, crash), the
object is left half-written (e.g. `state.yaml` present, body missing).

### On `FsWorkStore.create` specifically

It has **no caller under `tcw/`** — both production create paths go through
`create_work` (`cli.py:216`, `serve/__init__.py:773`). So "collapse it into
`create_work` and delete it" is a live alternative to protecting it, and probably
the smaller end state.

Price that option honestly before choosing it: `.create(` appears across 17 test
modules, every one of which constructs an `FsWorkStore`, so the collapse is a
test-surface migration rather than a one-file change. (An earlier note here said
the sole caller was `tests/test_recursion.py` — that was wrong.) The abstract
declaration at `base.py:931` also means removing it changes the store interface,
not just the adapter, which is a prime-directive question and not a refactor.

## Desired outcome

Make each multi-file object create/update leave the store either fully updated or
unchanged on a mid-write failure — e.g. write all temp files first, then atomically
promote them, and on `create_work` failure remove the partially-created directory.

## Prior art in this repo

`FsWorkStore.accept_inbox` (`fs.py:2246-2269`) **already solves this shape** —
`mkdtemp` into the destination's parent → populate the temp dir → `os.replace` to
promote → `shutil.rmtree` in the `except`, which also unwinds a partially
promoted destination. Start there rather than designing a new helper; the desired
outcome below is a description of what `accept_inbox` already does.

## Notes

- Keep it inside the `Fs*` adapters (no abstract-interface change) — except that
  deleting `create` would touch `base.py:931`, so that variant is a scope
  decision for the spec, not an implementation detail.
- Add fault-injection tests (mirror the existing `_atomic_write` failure tests):
  fail the second write and assert the object is absent/unchanged, not partial.
