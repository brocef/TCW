# Spec: Transactional multi-file writes in the Fs store

## Capability changes

**None.** This is a durability property of writes that already happen behind
existing capabilities (`work/create-a-work-item`, `taxonomy/add-a-term`,
`capabilities/add-a-capability`, …). No new verb, no flag, no status flip. The
observable difference is confined to a failure path the ledger does not
describe.

## Problem

Several `Fs*` store operations create or update an object out of **two files**,
written sequentially. Each individual write is atomic (or, in one case, is not),
but nothing spans the pair. A mid-write failure — ENOSPC, EACCES, crash — leaves
the object half-written: `state.yaml` present with no body, or a `meta.yaml`
updated against a stale `description.md`.

Four sites, verified in `tcw/store/fs.py`:

| Site | Lines | Files written | Individually atomic? |
|---|---|---|---|
| `FsTreeStore._write_node` | 625–631 | `meta.yaml`, `description.md` | yes (`_atomic_write` ×2) |
| `FsWorkStore.create` | 2277–2295 | `initial-request.md`, `state.yaml` | **no** — plain `write_text` + `dump_yaml` |
| `FsWorkStore.create_work` | 2410–2503 (writes at 2499–2502) | `state.yaml`, `initial-request.md` | yes |
| `FsWorkStore.update_work` | 2507–2638 (writes at 2623–2626) | `state.yaml`, body | yes |

`update_work` was not named in the initial request; it is the same shape and is
found by the same grep (`_atomic_write` at `fs.py:2624` and `2626`), so it is in
scope.

`_write_node` is the shared helper behind **both** the taxonomy and capabilities
adapters — call sites at `fs.py:748`, `977`, `1229`, `1614`. Fixing it there
covers `add`/`update` for terms and capabilities in one place; `update_term` is
not patched directly.

`FsWorkStore.create` has **no caller under `tcw/`** — verified by grep; both
production create paths go through `create_work` (`cli.py:216`,
`serve/__init__.py:773`). It is nonetheless a duplicate, and worse, copy of
`create_work`'s create path: same `_unique_slug` call, same parent resolution,
same directory choice, same body template — with weaker durability.

Prior art already in the repo: `FsWorkStore.accept_inbox` (`fs.py:2246–2269`)
solves the create shape correctly — `mkdtemp` beside the destination, populate,
`os.replace` to promote, `shutil.rmtree` in the `except`.

## Goals

1. An **I/O or serialization failure while producing content** (ENOSPC, EACCES,
   a YAML dump error) in any of the four sites leaves the store fully updated or
   unchanged — never partial. This is the failure class that is reachable today
   and that the fix closes; a process death during the final renames is *not*
   covered, and is stated as a ceiling in Risks rather than claimed away.
2. `_write_node`'s fix is made once in the shared helper and inherited by every
   taxonomy and capability write.
3. `FsWorkStore.create` stops being a second, weaker create path.
4. Fault-injection tests cover each site, mirroring the existing
   `_atomic_write` failure tests in `tests/test_store_editor.py:815–864`.

## Non-goals

- **No abstract-interface change.** `WorkStore.create` (`base.py:931`) stays
  declared; nothing is removed from `base.py`. The prime-directive question the
  initial request flagged is therefore not opened.
- **No test-surface migration.** The 262 `.create(` call sites across 17 test
  modules keep working unchanged.
- **No crash-durability guarantee.** `fsync`, write-ahead journalling, and
  `O_DIRECT`-style ordering are out of scope; see Risks for the residual window.
- **No concurrency guarantee.** Two agents writing the same object concurrently
  is a separate backlog item
  (`2026-06-22-concurrency-safe-work-claims-for-multi-agent-repos-…`).
- **No change to `accept_inbox`.** It already has the property.

## Design

### 1. `_atomic_write_all(pairs)` — the update shape

A module-level sibling of `_atomic_write` (`fs.py:546`) in two phases:

- **Stage:** write every `path.tmp` for the whole batch. Any exception here
  unlinks all temps and re-raises — nothing was promoted, the store is untouched.
- **Promote:** `tmp.replace(path)` for each in turn.

Temp files sit **beside their targets** (`path.with_suffix(suffix + ".tmp")`,
as `_atomic_write` already does) — same directory, therefore same filesystem,
which is what makes `os.replace` atomic. It catches `BaseException`, matching
`_atomic_write`, so a `KeyboardInterrupt` mid-batch still cleans up its temps.

This replaces the paired `_atomic_write` calls in `_write_node` and
`update_work`. It moves the failure window from "between two full writes" to
"between two renames", which is where the content-producing failures (ENOSPC,
EACCES, serialization errors) can no longer reach.

### 2. Directory rollback — the create shape

`create_work` calls `d.mkdir(parents=True)` on a directory it therefore knows did
not exist. Wrapping the writes in `try` / `except: shutil.rmtree(d, ignore_errors=True)`
/ `raise` makes the create all-or-nothing: on failure the item directory is gone,
not half-populated.

`_write_node` serves both create and update: it captures `existed = d.exists()`
before `mkdir`, and rolls back with `rmtree` only when it created the directory.
When the node already existed, phase-1 staging is the protection.

`mkdir(parents=True)` may also create intermediate directories (e.g. a missing
`backlog/`); rollback removes only the leaf. An empty `backlog/` is inert — git
does not track it and every read path tolerates it.

### 3. `FsWorkStore.create` → delegate

`create` becomes a thin call into `create_work` — the same slug, directory, body
template, and staging, with `create_work`'s already-atomic write path — and
returns `self.get(slug)` to preserve its `WorkItem` return type. The duplicate
write path is deleted rather than separately hardened.

Two behavioral deltas this introduces, both accepted:

- `create_work` **rejects an empty title**; `create` did not. No test passes an
  empty title (verified by grep), and an empty title produces an unusable slug.
- `create` always wrote a `priority:` key, `null` when unset; `create_work` omits
  it. `state.yaml` is read through `load_yaml` + `.get()`, so a missing key and a
  null key are equivalent to every reader, and no test asserts on the raw
  `state.yaml` text (verified by grep).

### 4. Tests

New fault-injection tests, patterned on
`test_atomic_write_preserves_prior_on_failure` — patch to raise on the *second*
file's write and assert:

- `create_work` — the item directory does not exist afterwards.
- `create` — same, through the delegate.
- `_write_node` on a new node — the node directory does not exist.
- `_write_node` on an existing node — both `meta.yaml` and `description.md` hold
  their **prior** contents.
- `update_work` with a body change — `state.yaml` and the body are both
  unchanged.
- `_atomic_write_all` — no `.tmp` files survive a staging failure, and the
  original exception (not a rollback error) is what reaches the caller.
- `_atomic_write_all` failing *during the promote loop* — pins the documented
  ceiling: earlier files are promoted, later ones are not, and the exception
  propagates. This test exists so the limit is a recorded decision rather than
  an accident someone later "fixes" without noticing it was known.

## Acceptance criteria

1. `FsWorkStore.create_work` raising on its second file write leaves no
   directory at the item's path.
2. `FsWorkStore.create` raising on its second file write leaves no directory at
   the item's path, and `create` contains no `write_text`/`dump_yaml` write path
   of its own.
3. `FsTreeStore._write_node` raising on the `description.md` write, against a
   node that **already existed**, leaves `meta.yaml` byte-for-byte as it was.
4. The same failure against a node that did **not** exist leaves no node
   directory.
5. `FsWorkStore.update_work` raising on the body write leaves `state.yaml`
   byte-for-byte as it was.
6. After any of the above failures, no `*.tmp` file remains anywhere under the
   store root, and the exception the caller sees is the injected one — the
   rollback never replaces or masks it.
7. `tcw/store/base.py` is unchanged.
8. The full suite passes with **no edits to existing test call sites**.

## Risks

- **Residual promote window.** A process death between the two `replace()` calls
  still leaves a partial update on a pre-existing node. Closing it needs a
  journal or a whole-directory swap, neither of which is worth its cost here;
  the code carries a `ponytail:` comment naming the ceiling and the upgrade path.
- **`create` delegation changes error behavior.** An empty title now raises
  `ValueError` where it previously produced a degenerate item. Mitigated: no
  caller does this, and it is strictly better behavior.
- **Rollback masking the original error.** `rmtree(..., ignore_errors=True)` in
  the `except` must not swallow or replace the exception being propagated —
  covered by the tests asserting the original exception type reaches the caller.
  `ignore_errors=True` is chosen precisely for this: if rollback itself cannot
  proceed, the caller still sees the real failure, at the price of a leftover
  partial directory. That trade is deliberate — an unremovable directory means
  something is wrong that a masked exception would only hide.
- **`_write_node`'s `existed` check is TOCTOU-racy** under concurrent writers.
  Stated precisely, because the earlier "no worse than today" framing was too
  generous: if a second writer creates the node between our `d.exists()` check
  and our write failure, `existed` is `False` and the rollback removes a
  directory we did not create. That is a *new* failure mode — today the same
  race corrupts the node, whereas after this change it can delete it.

  Accepted anyway. The race needs another process to create *and* populate the
  node inside the microseconds between our check and our `mkdir`, and then needs
  our own write to fail. Closing it properly means an ownership signal that
  survives the check-to-write gap — `mkdir(exist_ok=False)` on a create-only
  path, or a lock — which is exactly the concurrency work already tracked in
  `2026-06-22-concurrency-safe-work-claims-for-multi-agent-repos-…`. Doing it
  here would be that item's design, half-built, in the wrong place.
