# A dangling bare work slug resolves `ok`, so `tcw validate` never flags it

## Origin

Found at the `implement` stage of
`2026-08-19-render-an-unhosted-tcw-reference-as-a-visibly-distinct-non-link-naming-its-project`
while building a fixture for that item's visual check. Pre-existing; unrelated to
that change, which only touched presentation of failures.

## Problem

`resolve_tcw_ref` checks existence for two of the three axes and not for the
third (`tcw/refs.py`):

- `T` → `FsTaxonomyStore.get(ref)`, `None` → `ok: false`
- `C` → `FsCapabilitiesStore.get(ref)`, `None` → `ok: false`
- `W` → `resolve_qualified_work_ref(...)`, which answers **which store** the ref
  belongs to, not whether the item is in it. For a bare slug it returns
  `(local store, slug)` unconditionally, and `resolve_tcw_ref` then returns
  `ResolveResult(True, "W", bare, "")` without a `get()`.

So any bare work slug resolves:

```
tcw://W/nope                    -> {"ok": true, "axis": "work", "key": "nope"}
tcw://W/2026-01-01-nope         -> {"ok": true, "axis": "work", "key": "..."}
tcw://W/backlog/2026-01-01-nope -> {"ok": false, ... "no such work item: ..."}   # caught
tcw://W/ghost/2026-01-01-x      -> {"ok": false, ... "no such project ..."}      # caught
```

Only the _qualified_ spellings are checked. The bare one — the spelling people
actually write for a local item — is not.

## Consequences

- **`tcw validate` does not flag a dangling local work reference.** It reports a
  problem only when `not r.ok` (`tcw/validate.py`), so a typo'd or deleted work
  slug passes validation silently. This is the check's headline purpose.
- **The viewer hands the SPA a key that dead-ends.** `/api/resolve` answers
  `ok: true`, so the anchor is rewritten to `/work/<slug>` and clicking it 404s —
  the exact "dead-end link" failure `resolve_tcw_ref`'s own docstring says the
  design exists to prevent.

## Fix shape

Make the `W` branch symmetric with `T`/`C`: after locating the store, confirm the
item exists (`store.get(bare)`), and on `None` return `ok: false` with the
message `qualified_work_ref_problem` already produces. Worth checking whether
`resolve_qualified_work_ref`'s other caller (`tcw/serve/__init__.py`
`_work_store_for`) depends on the current permissive behavior — it routes to a
404 by a different path, so it probably does not, but that is the thing to
verify before changing the shared helper rather than the `refs.py` branch.

A test belongs with it: `tests/test_refs.py` covers the two qualified dangling
spellings and not the bare one, which is how this survived.
