# Plan — Resolve taxonomy refs against symlinks, not just lexically

## Call-site walk

The spec's first risk requires walking **every** join that puts a runtime
identifier under a store root, rather than asserting that a handful of guards
cover them. Below is that walk, redone against `tcw/store/fs.py` as committed at
**`c0b340e`** after a review found the first pass both mis-cited and incomplete.
It is **not** a closed proof: it found one more escape (`_write_target`, spec
Problem §3b) that the "downstream of `get_local`" argument had wrongly cleared,
so the walk is evidence, not a discharge. Re-run it at `implement` — the sibling
non-git-writes item is `active` on this file and already moved every line below
`:314` once during this revision.

Config joins (`self.root / self.CONFIG_NAME`, `self.root / "config.yaml"` —
`:932`, `:1069`, `:1084`, `:1089`, `:1097`, `:1162`, `:1374`, `:1691`, `:1704`,
`:1709`, `:1717`, `:1743`) are excluded: the trailing component is a constant
filename, not an identifier, and the root itself is not caller-supplied.

### Taxonomy

| Join                                            | Reached from                            | Guard?                                                                            |
| ----------------------------------------------- | --------------------------------------- | --------------------------------------------------------------------------------- |
| `_term` — `self.root / slug` (`:940`)           | `get_local`, `_local_slugs`, `add`      | no — every caller is guarded below                                                |
| `get_local` — `(self.root / slug).is_dir()` (`:966`) | CLI, serve, every ref path         | **yes**                                                                            |
| `_local_slugs` — `self.root.rglob("*")` (`:970`) | `list_all`, `relators`, `check`         | **yes**                                                                            |
| `add` — `(self.root / parent).is_dir()` (`:1038`) | CLI, serve                            | no — a stat, no read; the `d` guard two lines later refuses the same input        |
| `add` — `d = self.root / full` (`:1044`)        | CLI, serve                              | **yes** — one guard covers a symlinked `--parent` and a symlinked leaf            |
| `remove` — `self.root / term.slug` (`:1065`)    | `get()`                                 | no                                                                                 |
| `_validation_resources` — `local_folder` (`:1208`) | `tcw validate --target taxonomy:<ref>` | **yes** — the fast path bypasses `get_local`                                     |
| `_validation_resources` — `owner.root / term.slug` (`:1219`) | `get()`                    | no — term came from a guarded lookup; inherited roots are already resolved (`:692`) |
| `get_detail` — `owner.root / term.slug` (`:1252`) | `get()`                               | no — same reasoning, though note it `read_text()`s both files directly            |
| `update_term` — `self.root / term.slug` (`:1268`) | `get()`, local-only                   | no                                                                                 |

### Capabilities

| Join                                                          | Reached from                                | Guard?                                                                     |
| ------------------------------------------------------------- | ------------------------------------------- | -------------------------------------------------------------------------- |
| `_all_meta_dirs` — `self.root.rglob("*")` (`:1387`)           | every local listing                         | **yes**, and **before** `_is_capability(p)` at `:1393`                     |
| `_local_paths` — `load_yaml(self.root / p / "meta.yaml")` (`:1401`) | `_all_meta_dirs`                    | no — but it is a **read**, so the `_all_meta_dirs` filter must precede it   |
| `_override_index` — `:1407` (read), `:1410` (folder)          | `_all_meta_dirs`                            | no — same                                                                   |
| `_capability` — `self.root / path` (`:1429`)                  | `get_local`, `_local_paths`, `add`          | no — callers guarded                                                        |
| `_apply_override` — `self.extends[alias].root / base.path` (`:1464`) | inherited store's own listing        | no — inherited roots resolved at `:692`, `base.path` from that store's filtered listing |
| `get_local` — `:1489-1490`                                    | CLI, serve, `set`, `remove`                 | **yes**, reordered — see task 3                                             |
| `add` — `d = self.root / path` (`:1568`)                      | CLI, serve                                  | **yes**                                                                     |
| `remove` — `self.root / cap.path` (`:1583`)                   | `get()`                                     | no                                                                          |
| `_write_target` — `self.root / local.path` (`:1634`)          | `get_local`                                 | no — guarded lookup                                                         |
| `_write_target` — `self.root / cap.path` (`:1643`), `self.root / cap.origin / cap.path` (`:1648`) | inherited `get()` + local mirror | **yes** — the escape in spec Problem §3b; nothing upstream guards it        |
| duplicate-id scan — `load_yaml(self.root / path / "meta.yaml")` (`:1767`) | `_local_paths`                  | no — filtered listing                                                       |
| override/attachment validation — `d = self.root / p` (`:1814`) | `_all_meta_dirs` or a `get()` hit           | no — filtered listing; it `iterdir()`s `d`, so the filter is load-bearing    |
| `_validation_resources` — `local_folder` (`:1835`)            | `tcw validate --target capabilities:<ref>`  | **yes** — bypasses `get_local`                                              |
| `_validation_resources` — `owner.root / cap.path` (`:1843`)   | `get()`                                     | no                                                                          |

### Work

| Join                                                | Reached from                | Guard?                                                                 |
| --------------------------------------------------- | --------------------------- | ---------------------------------------------------------------------- |
| `_item_dirs` — `(self.root / status).rglob("state.yaml")` (`:2075`) | every read      | **yes** — a symlinked `state.yaml` matches by name (spec Problem §4)   |
| `_find` (`:2224`) and everything downstream of it — `start` (`:2101`, `:2103`), `.claiming` (`:2143`, `:2167`, `:2187`), `transition` (`:3159-3160`), `set_field`, `_validation_resources` (`:2878`) | `_item_dirs` | no — the folder was already discovered and filtered |
| item creation / re-parenting — `self.root / "backlog" / slug` (`:3035` `inbox_accept`, `:3064` its temp dir, `:3345` `create_work`) and `self.root / self._status_of(d) / slug` (`:3468` denest) | CLI, serve | no — the slug is minted by `slugify`/`_unique_slug` (`:672`), never a caller path, and the status folder above it is an ordinary directory; a denest target comes from `_find` |
| `inbox` — `inbox_root` (`:2895`) and its walks (`:2956-2964`, `:2988-2999`) | CLI, serve  | no — both walks skip symlinks outright today                           |

Two conclusions the previous draft got wrong and this one states plainly: the
capabilities write path is **not** entirely downstream of `get_local`, and the
work store is **not** entirely unaffected.

## Ordering rationale

Every task leaves `pytest` green: each guard ships **with** its regression tests
in the same commit, rather than a red test-only commit. The helper lands first so
the store tasks are pure call-site edits. The riskiest change is the
`_local_slugs`/`_all_meta_dirs` filtering — it feeds `check`, `relators` and the
capabilities override index, so it is isolated inside its own store's task with
those consumers' existing tests as the blast-radius check, and the three stores
are separate commits so a bisect names one. The separate CLI error-boundary work
must not be entangled with these containment commits.

## Tasks

### 1. `FsTreeStore._within_store` helper + cached resolved root

**Changes** `tcw/store/fs.py` — `from functools import cached_property` at the
top, and two members on `FsTreeStore` (`:790`), beside `_stage`/`_rm`/`_mv`:

```python
@cached_property
def _resolved_root(self) -> Path:
    """The store root with symlinks resolved.

    A `cached_property` rather than an `__init__` assignment on purpose:
    `FsWorkStore.__init__` (`:2005`) does not call `super().__init__()`, so
    anything set in the base initializer would be missing there. Cached for the
    life of the store instance — one CLI command / one HTTP request.
    """
    return self.root.resolve()

def _within_store(self, path: Path) -> bool:
    """True iff `path` stays inside the store root once symlinks are resolved.

    Both sides are resolved: taxonomy and capabilities roots keep the lexical
    spelling they were opened with, so a checkout under a symlinked ancestor
    would otherwise fail every check. Not race-safe — see the spec's threat
    model.
    """
    try:
        return path.resolve().is_relative_to(self._resolved_root)
    except OSError:                       # broken or looping symlink
        return False
```

Non-strict `resolve()` resolves the existing prefix and appends the rest, so it
is correct for a path being created as well as one being read.

**Verified by** new `tests/test_store_bounds.py`: an ordinary child is within; a
child reached through a symlink to a sibling store is not; a not-yet-created
child is within; a symlink loop returns `False` rather than raising; and — the
explicit fixture that replaces the discredited `tmp_path` inference (spec
criterion 8) — a store **opened through a symlinked spelling** (`real/` +
`ln -s real link`, store opened at `link/docs/taxonomy`) says `True` for an
ordinary child, and `add`/`get`/`list_all` behave as on the physical spelling.
One case per store class, since `_resolved_root` must exist on all three:
instantiate `FsTaxonomyStore`, `FsCapabilitiesStore` and `FsWorkStore` and assert
`_within_store` works on each — `FsWorkStore` is the one that would raise
`AttributeError` if the cache were moved into `FsTreeStore.__init__`.

### 2. Taxonomy guards

**Changes** `tcw/store/fs.py`:

- `get_local` (`:966`) — `return self._term(slug) if (self.root / slug).is_dir()
and self._within_store(self.root / slug) else None`. Order matters: the guard
  sits behind the existence check so a miss pays nothing, and `_term` (the read)
  runs only after both. Still returns `None`, never raises — `check` catches
  only `AmbiguousRef`.
- `add` (`:1044`) — after computing `d`, before `d.exists()` (`:1045`): not
  `_within_store(d)` → `raise ValueError(f"parent term does not exist: {parent}")`
  (the existing wording; one guard covers both the `--parent` symlink and a
  symlinked leaf). Placed before the first `mkdir`, honoring the fail-closed
  contract documented at `:1047-1049`.
- `_local_slugs` (`:970`) — add `and self._within_store(p)` to the comprehension.
- `_validation_resources` (`:1208`) — take the `local_folder` fast path only when
  `_within_store(local_folder)`; otherwise fall through to the `get()` branch,
  which now returns `None` → `return []`.

**Verified by** new tests in `tests/test_taxonomy.py`, beside the existing
lexical-escape regressions (`test_rm_refuses_ref_escaping_the_store` at `:319`,
`test_check_reports_escaping_ref_as_dangling` at `:333`), using a
`plant_symlink` fixture that creates `docs/capabilities/secret/victim` plus a
nested `victim/deeper` and links it in:

- `get("alpha/link/victim") is None`; `remove(...)` raises "no such term".
- `add(..., parent="alpha/link")` raises **and**
  `docs/capabilities/secret/planted/` does not exist afterwards.
- `list_all(local_only=True)` contains no slug under `alpha/link` — asserted for
  the link itself **and** for `alpha/link/victim/deeper` (spec criterion 3).
- a stored `vocabulary: [alpha/link/victim]` makes `check()` report
  `dangling vocabulary ref`.
- `_validation_resources("alpha/link/victim") == []`.

### 3. Capabilities guards

**Changes** `tcw/store/fs.py`:

- `get_local` (`:1488-1490`) — **reordered, not extended.** Today the condition
  is `self._capability(path) if path and self._is_capability(self.root / path)
and not load_yaml(self.root / path / "meta.yaml").get("overrides") else None`;
  appending `_within_store` leaves `load_yaml` parsing external YAML first.
  Replace with:

    ```python
    def get_local(self, path: str) -> Capability | None:
        d = self.root / path
        # Containment before any read: `load_yaml`/`_capability` would otherwise
        # parse a meta.yaml outside the store. The stat stays first so a miss
        # pays no `resolve()`.
        if not (path and self._is_capability(d) and self._within_store(d)):
            return None
        return None if load_yaml(d / "meta.yaml").get("overrides") else self._capability(path)
    ```

- `_all_meta_dirs` (`:1384-1395`) — `if not self._within_store(p): continue`
  **before** the `self._is_capability(p)` test at `:1393`, which would otherwise
  stat a `meta.yaml` under the symlink target. No miss to optimize here: every
  candidate pays containment either way.
- `add` (`:1568`) — refuse `d` before `d.exists()` and before `_write_node`, with
  the existing-style `ValueError`.
- `_write_target` (`:1622`) — guard the folder it is about to hand back: before
  the final `return d, {...}, True` (`:1653`), not `_within_store(d)` →
  `raise ValueError(f"no such capability: {identifier}")`. This is spec Problem
  §3b — the fresh-override mirror never consults `get_local`, and today it
  **creates** a folder and `meta.yaml` outside the store. Guarding the returned
  `d` covers both mirror branches (`:1643` and the origin-qualified `:1648`); the
  `_is_capability(d)` collision probes above it still stat through the link,
  which is acceptable (a stat, not a read) and is what keeps the local
  fast path cheap.
- `_validation_resources` (`:1835`) — gate the `local_folder` fast path the same
  way as taxonomy.

**Verified by** new tests in `tests/test_capabilities.py`, symmetric to task 2,
plus two the spec turns on:

- criterion 5 — after `set("link/thing", …)` raises,
  `docs/outside/thing/meta.yaml` is **byte-identical** to before (the current
  code mutates it), and `list_all(local_only=True)` lists no descendant of `link`.
- criterion 7, the **no-external-read** assertion: monkeypatch
  `tcw.store.fs.load_yaml` with a wrapper that appends each path to a list, call
  `get_local("link/thing")` and `list_all(local_only=True)`, and assert no
  recorded path resolves outside the store root. Byte identity proves no
  mutation; only this proves the file was never opened.

A third test in `tests/test_capabilities_federation.py` (it needs the `child_of`
helper) covers criterion 6: upstream capability at `link/thing`, local
`docs/capabilities/link -> ../../outside`, `set("link/thing", {"Status":
"Partial"})` raises **and** `child/outside/thing/` does not exist afterwards.
That test fails on today's tree — the reproduction is in spec Problem §3b.

Existing federation/override tests (`test_capabilities_federation.py`,
`test_capabilities_reset.py`) are the blast-radius check for the
`_all_meta_dirs` filter.

### 4. Work-store guard

**Changes** `tcw/store/fs.py` — `_item_dirs` (`:2059-2076`): filter the scan with
`if self._within_store(p)`, so a `state.yaml` that is a symlink out of the store
is not treated as an item folder. One line inside the existing comprehension;
`FsWorkStore.root` is already resolved (`:2005-2010`), so `_resolved_root` costs
nothing there.

**Verified by** new tests in `tests/test_work.py`:

- a symlink named `state.yaml`, planted in an ordinary in-store item folder and
  pointing at a `state.yaml` outside `docs/work/`, is not listed by `list`, is
  not found by `show`/`locate`, and yields no external path from
  `_validation_resources` (spec criterion 9). This test fails on today's tree.
- an item folder that is itself a symlink stays undiscovered — the pre-existing
  `rglob` property, locked in so a future switch to `os.walk(followlinks=True)`
  fails loudly instead of silently reopening the escape.

### 5. Preserve the CLI error-boundary ownership split

**Changes** none. The non-Git-writes item owns the generic
`CalledProcessError` handler (`tcw/cli.py:174-182`) and is `active` on `fs.py`
(it landed `require_repository` in `c0b340e`, `fs.py:314-327`). Keep containment
regressions independent of that handler so either item can land first; rebase on
it rather than merging the two diffs, and note the relationship in `outcome.md`.

### 6. Measurement pass

Not "run the suite and assume". Two separate numbers, both recorded in
`outcome.md`:

1. **Lookup** — `get_local` hit and miss, taxonomy and capabilities, before and
   after. The spec's ≈ +5%-per-hit figure is the baseline to confirm or correct;
   its 138 µs denominator is inherited from the first draft and unverified.
2. **Listing** — `list_all(local_only=True)` for taxonomy and for capabilities,
   **separately**, on a **synthetic** tree built by the benchmark script (script
   lives in the scratchpad, not the repo): ~2,000 nodes at depth 5, since this
   repo's own taxonomy is too small to show an O(directories) cost. Report
   cold-cache and warm-cache timings, before and after. Include `_item_dirs` on
   a synthetic work store for the same reason.

Reference points already measured on this repo (macOS, warm): `resolve()`
≈ 7.1 µs, `is_dir()`/`is_symlink()` ≈ 1.0 µs, `_within_store` ≈ 17.9 µs with the
root resolved every call and ≈ 10.4 µs with `_resolved_root` cached.

**If the listing regression is material** (the threshold to beat: listing stays
within 15% of its pre-change time), the fallback — and only then — is to resolve
only when the candidate is itself a symlink (`if p.is_symlink() and not
self._within_store(p): continue`). That is sound because `rglob` never descends
into a symlinked directory, so inside a listing walk only the final component can
be one. Do not take it pre-emptively; record the number that justifies it.

Then run `pytest` in full. Note explicitly what a green suite does **not** prove:
it is not the symlinked-root check (task 1's fixture is), because `tmp_path` on
this machine is already a physical path (`/private/var/folders/…`, equal to its
own `realpath`).

## Documentation Sync

Evaluated all four entries in `CLAUDE.md` (`documentation-sync` skill):

### 7. `docs/changelogs/upcoming.md` — `[Any-Code-Change]` **fires**

Behavior-affecting fix. Under **Fixed**: taxonomy, capabilities **and work**
store ids no longer resolve through a symlink planted inside the store — one
`FsTreeStore._within_store` guard applied at `get_local`, `add`,
`_write_target`, the local-path listings, `_validation_resources` and
`_item_dirs`; note that the escape affected writes (`taxonomy add --parent`,
`capabilities set`, including a fresh federated override that created files
outside the store), not only reads, and that the work-store exposure is a
symlinked `state.yaml` file rather than a symlinked item directory.

### 8. `docs/release-notes/upcoming.md` — `[Public-API]` **fires**

User-visible, so it gets one plain-language line: a term, capability or work
item reached through a symlink inside `docs/taxonomy/`, `docs/capabilities/` or
`docs/work/` is no longer found or written — entries stay inside their own store,
and such an entry stops appearing in `list`. No module names.

### `README.md` — `[Public-API]` **does not fire**

No CLI surface change: no new command, flag, or argument, and README documents
neither ref resolution internals nor symlink behavior.

### `skills/<component>/SKILL.md` — `[Skill-Driven-Component]` **fires**

Update `skills/tcw-taxonomy/SKILL.md`, `skills/tcw-capabilities/SKILL.md` **and
`skills/tcw-work/SKILL.md`** with the resolved-containment guardrail and its
fail-closed behavior. The work skill is now in scope because task 4 changes what
that component discovers. This changes a filesystem-adapter guardrail driven by
the skills even though the abstract store interfaces remain unchanged.

## Verification

Beyond `pytest`:

- **The real CLI, by hand**, since the tests exercise the store API and `main()`
  but not the shipped binary end to end. Rebuild the scratch fixture from the
  spec's Problem section and confirm each acceptance criterion at the shell:
  `taxonomy show`/`add --parent`/`list`/`check`, `capabilities show`/`set`/`list`,
  `work list`/`show`, and `tcw validate`. Criteria 2, 5 and 6 are the ones that
  need eyes — the assertion is about a file **outside** the store being untouched
  or uncreated.
- **Perf** (task 6) — not a suite check; two numbers in `outcome.md`.
- **Not verifiable here, stated instead:** whether any real user has a working
  symlink inside a store. The spec accepts the break because writes through one
  already fail; nothing in the suite can prove nobody relies on the read.
- **Out of reach by design:** the TOCTOU window (spec's Threat model). No test
  is proposed for it because the guard does not close it.

## Notes

- No blockers. This item does not depend on
  `2026-07-30-validate-taxonomy-vocab-refs-at-write-time-and-define-bare-slug-resolution`
  (completed), it extends it. It **overlaps in file** with
  `2026-07-30-fix-non-git-write-paths-work-new-and-init-fail-outside-a-git-repository`,
  which is `active` on `tcw/store/fs.py` and has already landed one commit there
  (`c0b340e`); land after it or rebase, and re-verify the line numbers above
  either way.
- **`_resolved_root` vs. that item's stateless `require_repository`.** The two
  items make opposite caching choices on the same class, deliberately. Its check
  must stay stateless because *whether a repository exists* can change under a
  live store; the store's own root **identity** cannot — and both `tcw serve`
  (`tcw/serve/__init__.py:396-402`, a fresh `_stores()` per request) and the CLI
  build a store per operation. The stale-cache window is recorded in the spec's
  Risks rather than defended against; if a reviewer prefers symmetry, dropping
  the cache costs one extra `resolve()` per candidate (≈ 7 µs) and nothing else.
- Scratch reproduction fixtures from the spec stage:
  `…/scratchpad/repro` (taxonomy + capabilities), `…/repro2` (symlinked store
  root). Disposable — rebuild from the spec's Problem section rather than
  assuming they survive. The Problem §3b and §4 reproductions are store-API
  scripts, not scratch repos; both are reproduced verbatim in the spec.
