# Rework (pass 4): close the same gap on `FsCapabilitiesStore.set`

Supersedes the pass-2 rework instructions, which are done and recorded in
`outcome.md` (git history keeps them). Verification accepted the work; this pass
is **user-directed scope growth**, chosen over filing a follow-up item.

## Origin

Dogfooding through the real CLI surfaced that `tcw capabilities set` does **not**
route through `update_capability` — that method's only caller is the web editor
(`tcw/serve/__init__.py:1070`). The CLI goes through `FsCapabilitiesStore.set`
(`fs.py:1618-1623`), which:

- calls `_write_target(...)`, materializing a **fresh override directory** for an
  inherited capability, then
- `d.mkdir(parents=True, exist_ok=True)`, then
- `_write_meta(d, ...)` — a single-file write, with **no rollback at all**.

Strictly this is outside the item's spec, which is about *multi-file* writes:
`set` writes one file, so it cannot leave a *partial* object. What it can leave is
an **empty override directory** when the write fails — the same inert residue
`_write_node` and `create_work` now roll back. Same class, path the item did not
reach.

## What to do

**1. Give `set` the same guard `update_capability` has.** Capture `existed`
before the `mkdir`, wrap the write, and roll back only a directory this call
materialized *and* only when nothing landed:

```python
if not existed and not (d / "meta.yaml").exists():
    shutil.rmtree(d, ignore_errors=True)
```

The second clause is not optional. `_write_meta` calls `self._stage(...)`
internally, so staging runs inside any guard wrapping it — exactly the trap that
produced commit `f2c5f9b`. A failed `git add` must leave the written `meta.yaml`
alone.

**2. Warn the next caller.** Add a short comment on `_write_node` and
`_write_meta` noting that they stage internally, so any caller wrapping them in a
rollback must key that rollback on whether content landed rather than on
directory ownership. This trap has now been hit twice; the comment is cheaper
than a third time.

**3. Tests.** Two, mirroring the `update_capability` pair:

- a failed `set` on a fresh override leaves no override directory;
- a `set` whose `git add` fails keeps the written `meta.yaml`.

Both must fail before the fix. `tests/test_store_editor.py` already has the
`_fail_writing` helper and the `child_of` federation import.

## Not in scope

No abstract-interface change. No change to `set`'s signature or return. The
`_write_meta`-only branches of `update_capability` are already covered by that
method's own guard.
