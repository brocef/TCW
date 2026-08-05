# Plan — Resolve taxonomy refs against symlinks, not just lexically

## Call-site walk (the spec's first risk, discharged)

The spec's Risks section required walking every `self.root / <id>` join rather
than asserting that six guards cover them. Done — and the walk found **two more
sites**, so the count is eight, not six:

| Site | Reached from | Needs its own guard? |
|---|---|---|
| `FsTaxonomyStore._term` (`fs.py:756`) | `get_local`, `_local_slugs` | no — callers guarded |
| `FsTaxonomyStore.get_local` (`fs.py:772`) | CLI, serve, every ref path | **yes** |
| `FsTaxonomyStore.add` (`fs.py:847`) | CLI, serve | **yes** — one guard on `d` covers parent and target |
| `FsTaxonomyStore._local_slugs` (`fs.py:784`) | `list_all`, `relators`, `check` | **yes** |
| `FsTaxonomyStore.remove` (`fs.py:859`) | `get()` | no |
| `FsTaxonomyStore._validation_resources` (`fs.py:1018`) | targeted validation | **yes** |
| `FsCapabilitiesStore._all_meta_dirs` (`fs.py:1200`) | local paths, override and ID indexes | **yes** — filter before consumers see escaped metadata |
| `FsCapabilitiesStore._local_paths` (`fs.py:1213`) | `list_all`, override index, ID lookup, `check` | no additional guard after `_all_meta_dirs` |
| `FsCapabilitiesStore._capability` (`fs.py:1244`) | `get_local`, local-path consumers | no — callers guarded |
| `FsCapabilitiesStore.get_local` (`fs.py:1304`) | CLI, serve, `set`, `remove` | **yes** |
| `FsCapabilitiesStore.add` (`fs.py:1379`) | CLI, serve | **yes** |
| `FsCapabilitiesStore.remove` (`fs.py:1370`), `set` (`fs.py:1421`), override writes (`fs.py:1430`, `:1435`) | `get()` | no |
| `FsCapabilitiesStore._validation_resources` (`fs.py:1645`) | targeted validation | **yes** |
| `FsWorkStore._validation_resources` (`fs.py:2314`) | `_find` (rglob) | no — verified unaffected |

Both `_validation_resources` take a `self.root / identifier` shortcut *before*
consulting `get()`, so `get_local`'s guard does not cover them. Verified against
the scratch repo — both return paths outside their store today:

```
tax : [docs/taxonomy/alpha/link/victim/meta.yaml, …/description.md]
cap : [docs/capabilities/link/thing/meta.yaml, …/description.md]
```

This does not contradict the spec — its Design table named the six sites it knew
and its Risks section deferred the walk to here. No spec change needed; the
guard, the behavior, and the acceptance criteria are unchanged, there are simply
two more places to apply it (`tcw validate --target taxonomy:<escaping-ref>`
must return no resources, which is the existing `return []` miss path).

## Ordering rationale

Every task leaves `pytest` green: each guard ships **with** its regression tests
in the same commit, rather than a red test-only commit. The helper lands first so
the two store tasks are pure call-site edits. The riskiest change is the
`_local_slugs`/`_all_meta_dirs` filtering — it feeds `check`, `relators` and the
capabilities override index, so it is isolated inside its own store's task with
those consumers' existing tests as the blast-radius check, and the two stores are
separate commits so a bisect names one. The separate CLI error-boundary work
must not be entangled with these containment commits.

## Tasks

### 1. `FsTreeStore._within_store` helper

**Changes** `tcw/store/fs.py` — add to `FsTreeStore` (`:615`), beside `_stage`/
`_rm`/`_mv`:

```python
def _within_store(self, path: Path) -> bool:
    """True iff `path` stays inside the store root once symlinks are resolved.

    Both sides are resolved: a repo can legitimately live under a symlinked
    path (macOS `/tmp` → `/private/tmp`, and every `tmp_path` test).
    """
    try:
        return path.resolve().is_relative_to(self.root.resolve())
    except OSError:                       # broken or looping symlink
        return False
```

Non-strict `resolve()` resolves the existing prefix and appends the rest, so it
is correct for a path being created as well as one being read.

**Verified by** new `tests/test_store_bounds.py`: an ordinary child is within; a
child reached through a symlink to a sibling store is not; a not-yet-created
child is within; a symlink loop returns `False` rather than raising; a store
whose root is itself reached through a symlink says `True` for its own children
(the `tmp_path` case).

### 2. Taxonomy guards

**Changes** `tcw/store/fs.py`:

- `get_local` (`:772`) — `return self._term(slug) if (self.root / slug).is_dir()
  and self._within_store(self.root / slug) else None`. Order matters: the guard
  sits behind the existence check so a miss pays nothing. Still returns `None`,
  never raises — `check` catches only `AmbiguousRef`.
- `add` (`:847`) — after computing `d`, before `d.exists()`: not
  `_within_store(d)` → `raise ValueError(f"parent term does not exist: {parent}")`
  (the existing wording; one guard covers both the `--parent` symlink and a
  symlinked leaf). Placed before the first `mkdir`, honoring the fail-closed
  contract documented at `:841`.
- `_local_slugs` (`:784`) — add `and self._within_store(p)` to the comprehension.
- `_validation_resources` (`:1018`) — take the `local_folder` fast path only when
  `_within_store(local_folder)`; otherwise fall through to the `get()` branch,
  which now returns `None` → `return []`.

**Verified by** new tests in `tests/test_taxonomy.py`, beside the existing
lexical-escape regressions (`:244`, `:257`), using a `plant_symlink` fixture that
creates `docs/capabilities/secret/victim` and links it in:

- `get("alpha/link/victim") is None`; `remove(...)` raises "no such term".
- `add(..., parent="alpha/link")` raises **and**
  `docs/capabilities/secret/planted/` does not exist afterwards.
- `list_all(local_only=True)` contains no slug under `alpha/link`.
- a stored `vocabulary: [alpha/link/victim]` makes `check()` report
  `dangling vocabulary ref` (mirrors `test_check_reports_escaping_ref_as_dangling`).
- `_validation_resources("alpha/link/victim") == []`.

### 3. Capabilities guards

**Changes** `tcw/store/fs.py`:

- `get_local` (`:1304`) — add `self._within_store(self.root / path)` to the
  condition.
- `add` (`:1379`) — refuse before `_write_node` with the existing-style
  `ValueError`.
- `_all_meta_dirs` (`:1200`) — filter before paths feed local listings, opaque-ID
  lookup, overrides, and attachment composition.
- `_validation_resources` (`:1645`) — gate the `local_folder` fast path the same
  way.

**Verified by** new tests in `tests/test_capabilities.py`, symmetric to task 2,
plus the one the spec's criterion 5 turns on: after
`set("link/thing", {"Status": "Supported"})` raises, `docs/outside/thing/meta.yaml`
is **byte-identical** to before — the current code mutates it. Existing
federation/override tests (`test_capabilities_federation.py`,
`test_capabilities_reset.py`) are the blast-radius check for the
`_all_meta_dirs` filter.

### 4. Work-store negative control

**Changes** none — a test only, in `tests/test_work.py`: with an item folder
symlinked into `docs/work/backlog/`, `list`/`show`/`locate` do not find it. Locks
in the `rglob`-does-not-follow-symlinks property the spec relied on, so a future
switch to `os.walk(followlinks=True)` fails loudly instead of silently opening a
third escape.

### 5. Preserve the CLI error-boundary ownership split

**Changes** none. The non-Git-writes item owns the generic
`CalledProcessError` handler. Keep containment regressions independent of that
handler so either item can land first; note the relationship in `outcome.md`.

### 6. Suite + measurement pass

Run `pytest` in full (criteria 6 and 7 — the whole suite already runs under
macOS `tmp_path`, i.e. a symlinked `/tmp`, so a green suite *is* the
resolve-both-sides check). Then sanity-check `list_all` on this repo's own
taxonomy against the spec's ≈ +6%-per-hit measurement; if the tree walk shows
worse, record the number in `outcome.md` rather than silently accepting it.

## Documentation Sync

Evaluated all four entries in `CLAUDE.md` (`documentation-sync` skill):

### 7. `docs/changelogs/upcoming.md` — `[Any-Code-Change]` **fires**

Behavior-affecting fix. Under **Fixed**: taxonomy and capabilities store ids no
longer resolve through a symlink planted inside the store — one
`FsTreeStore._within_store` guard applied at `get_local`, `add`, the local-path
listings and `_validation_resources` in both stores; note that the escape
affected writes (`taxonomy add --parent`, `capabilities set`), not only reads,
and that `FsWorkStore` was verified unaffected.

### 8. `docs/release-notes/upcoming.md` — `[Public-API]` **fires**

User-visible, so it gets one plain-language line: a term or capability reached
through a symlink inside `docs/taxonomy/` or `docs/capabilities/` is no longer
found or written — refs stay inside their own store, and such an entry stops
appearing in `list`. No module names.

### `README.md` — `[Public-API]` **does not fire**

No CLI surface change: no new command, flag, or argument, and README documents
neither ref resolution internals nor symlink behavior.

### `skills/<component>/SKILL.md` — `[Skill-Driven-Component]` **fires**

Update `skills/tcw-taxonomy/SKILL.md` and `skills/tcw-capabilities/SKILL.md` with
the resolved-containment guardrail and its fail-closed behavior. This changes a
filesystem-adapter guardrail driven by both skills even though the abstract
store interfaces remain unchanged.

## Verification

Beyond `pytest`:

- **The real CLI, by hand**, since the tests exercise the store API and `main()`
  but not the shipped binary end to end. Rebuild the scratch fixture from the
  spec's Problem section and confirm each acceptance criterion at the shell:
  `taxonomy show`/`add --parent`/`list`/`check`, `capabilities show`/`set`/`list`,
  and `tcw validate`. Criterion 2 and 5 are the ones that need eyes — the
  assertion is about a file **outside** the store being untouched.
- **Perf** (task 6) — not a suite check; a number in `outcome.md`.
- **Not verifiable here, stated instead:** whether any real user has a working
  symlink inside a store. The spec accepts the break because writes through one
  already fail; nothing in the suite can prove nobody relies on the read.

## Notes

- No blockers. This item does not depend on
  `2026-07-30-validate-taxonomy-vocab-refs-at-write-time-and-define-bare-slug-resolution`
  (completed), it extends it.
- Scratch reproduction fixture from the spec stage:
  `…/scratchpad/repro` (taxonomy + capabilities) and `…/repro2` (symlinked store
  root). Disposable — rebuild from the spec's Problem section rather than
  assuming they survive.
