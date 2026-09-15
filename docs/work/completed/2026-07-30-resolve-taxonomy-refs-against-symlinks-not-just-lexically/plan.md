# Plan — Resolve taxonomy refs against symlinks, not just lexically

## Review round 1 — what changed, and why it matters

This plan was adversarially reviewed at `5ddaa31` before implementation. It came
back **NOT DONE** with three confirmed blockers, all verified against the tree by
the coordinating session before acceptance. Read this section before the rest:
it supersedes parts of what follows.

1. **The helper is wrong on supported Pythons.** `except OSError` does not catch
   what a symlink loop actually raises. `requires-python = ">=3.11"`
   (`pyproject.toml:10`), and the behavior differs across that range: on the
   3.14.6 interpreter in use, `Path("loop/child").resolve()` **returns the
   unresolved lexical path** and raises nothing (reproduced directly); on 3.12 it
   raises `RuntimeError`, which is **not** an `OSError` subclass. Task 1 is
   rewritten below. The plan's stated test — "a symlink loop returns `False`
   rather than raising" — is also wrong as an expectation; see Task 1.
2. **The call-site walk missed a site — for the third time.** Targeted
   validation, `check(identifier=…)`, replaces the filtered `_all_meta_dirs()`
   result with `[selected.path]` and re-joins it under the **local** root. For an
   *inherited* hit that path was never filtered by anything local, so a local
   symlink shadow is followed and external YAML is parsed. The reviewer
   reproduced this while simulating this plan's own guards: `base/link/thing` was
   selected, the external `meta.yaml` was read, and `check()` returned no
   problems. **New Task 3b.**
3. **Guarding the directory does not stop the read.** The guards validate
   `self.root / identifier`, but `_load_node` then opens `meta.yaml` and
   `description.md` *inside* it, and `_compose_body` opens attachments. A
   directory legitimately inside the store whose `meta.yaml` is a symlink out is
   read in full. Spec Goal 1 ("without reading the external file first") and
   criterion 7 ("no external read") are **not met** by directory guards alone.
   The spec already caught this exact shape for the work store — a symlinked
   `state.yaml`, Problem §4 — and missed the symmetric case for taxonomy and
   capabilities. **Resolved by decision: guard the shared read chokepoint,
   `FsTreeStore._load_node`. New Task 1b.** Narrowing the spec instead was
   considered and rejected.

Two further corrections, neither a blocker:

- **Task 5 is historical, not pending.** The generic `CalledProcessError`
  handler it defers to has **landed** (`tcw/cli.py:190`), and was since hardened
  for string-valued commands. Its owning item is `completed`. The live
  consequence is the opposite of what the task says: because that handler now
  turns *any* git failure into exit 1, a containment test asserting only "exits
  1" can pass on an unrelated git error. See the criteria fixes.
- **The spec's symlinked-store-root non-goal is stale for work stores.**
  `FsWorkStore.open` deliberately resolves a symlinked root
  (`tcw/store/fs.py:2160`) and there is a passing fixture proving it
  (`tests/test_external_work_store.py:74`). Restrict that non-goal to taxonomy
  and capabilities roots.

**Every line number below the fold is stale**, by +117 to +163 lines. Verified
drift at `5ddaa31`: `_safe_store_id` `728`→`845`; `FsTreeStore` `790`→`907`;
taxonomy `get_local` `956/966`→`1077/1087`; taxonomy `add` `1031/1044`→
`1152/1165`; taxonomy `_validation_resources` `1202/1208`→`1325/1331`;
`_all_meta_dirs` `1384/1393`→`1507/1516`; capabilities `get_local` `1488`→`1611`;
`_write_target` `1622/1643/1648`→`1746/1767/1772`; capabilities
`_validation_resources` `1829/1835`→`1956/1962`; `FsWorkStore.__init__`
`2005`→`2133`; `_item_dirs` `2059/2075`→`2190/2206`; work `_validation_resources`
`2878`→`3022`; `inbox_accept` `3035`→`3192`; `create_work` `3345`→`3508`. The
guard-target functions **moved** rather than being rewritten, so the walk's
verdicts still hold — but `inbox_accept`'s title/slug logic and `create_work`'s
validation *were* rewritten, and the repository preflight is new. **Re-derive
every citation at `implement`; do not trust one below.**

**One consequence of the repository preflight for every new test in this item:**
it now runs inside `_write_node` (`tcw/store/fs.py:990`) and at the head of
capabilities `set` (`:1793`). A write-path fixture that is not a real
initialized git repository fails on the precondition *before* reaching the
containment guard under test — green, or red, for the wrong reason. The
proposed `tests/test_store_bounds.py` must `git init` its fixtures.

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

    `RuntimeError` as well as `OSError`: a symlink loop raises `RuntimeError`
    on Python < 3.13 and, since 3.13, raises nothing at all — `resolve()`
    returns the path unresolved. Neither is an `OSError`. The floor is 3.11
    (`pyproject.toml:10`), so both eras are live.
    """
    try:
        return path.resolve().is_relative_to(self._resolved_root)
    except (OSError, RuntimeError):       # broken symlink; loop on <3.13
        return False
```

Non-strict `resolve()` resolves the existing prefix and appends the rest, so it
is correct for a path being created as well as one being read.

**The loop case, stated correctly** *(review round 1, blocker 1)*. The original
plan asserted this helper "returns `False`" for a symlink loop and made that a
test. That is not true on 3.13+, and chasing it would be wasted work. Measured on
the 3.14.6 interpreter in use:

```
$ ln -s loopb loopa; ln -s loopa loopb
>>> Path('loopa/child').resolve()
PosixPath('…/looptest/loopa/child')      # unresolved, no exception
```

So a loop *inside* a store resolves to a path still lexically under the root, and
the helper answers `True`. **That is harmless and the test must say so rather
than demand `False`:** every read through a loop fails with `ELOOP` regardless,
and the callers all gate on `is_dir()`/`is_file()` first, which a loop fails. The
requirement this helper actually owes is **"never raises"** — on 3.12 the bare
`except OSError` would have let `RuntimeError` escape and crash `list`.

Write the test as: a looping candidate does not raise, and `list_all` over a
store containing one still returns the ordinary entries. Do not assert the
containment verdict for a loop; it is don't-care, and pinning it would pin a
Python-version detail.

`is_relative_to` needs no same-prefix guard: `/a/store-other` is correctly not
relative to `/a/store` (confirmed in review).

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

### 1b. Contain the node's *resources*, not just its folder — `_load_node`

**New in review round 1 (blocker 3), by explicit decision: guard the shared read
chokepoint.** The directory guards in Tasks 2-4 answer "is this folder inside the
store". They do not answer "is the file I am about to read inside the store", and
that is a live escape: a folder legitimately in-store whose `meta.yaml` is a
symlink pointing out passes every directory guard, and `get_local` reads the
external file in full. Reproduced by the reviewer against both stores.

This is the same defect the spec already found for the work store — Problem §4's
symlinked `state.yaml`, guarded in Task 4 — applied to the two components the
spec checked only at directory level. Fixing it there and not here would ship an
inconsistency the spec's own reasoning contradicts.

**Changes** `tcw/store/fs.py`, `FsTreeStore._load_node` (`:967`) — the one method
both `FsTaxonomyStore._term` (`:1062`) and `FsCapabilitiesStore._capability`
(`:1553`) read a node through, which is what makes this one edit rather than
several:

```python
def _load_node(self, d: Path) -> tuple[dict, str, list[str]]:
    # Containment per resource, not just per folder: an in-store folder can hold
    # a `meta.yaml` or `description.md` that is a symlink out of the store, and
    # the folder guard upstream cannot see it. A resource that escapes reads as
    # absent — the same fail-closed shape `get_local` uses for the folder.
    meta_path = d / "meta.yaml"
    meta = load_yaml(meta_path) if self._within_store(meta_path) else {}
    desc = d / "description.md"
    description = (desc.read_text(encoding="utf-8")
                   if desc.exists() and self._within_store(desc) else "")
    reserved = self._node_reserved()
    attachments = sorted(
        f.name for f in d.iterdir()
        if f.is_file() and f.name not in reserved and not f.name.startswith(".")
        and self._within_store(f))
    return meta, description, attachments
```

An escaped `meta.yaml` yielding `{}` is what makes the node fail closed without a
second mechanism: `_is_capability` and the `overrides` test both read falsey, and
a taxonomy node with no `meta.yaml` has no kind, so the entry stops resolving —
`None`, not a raise, matching the established contract.

**Also `_compose_body`** (`:1536-1548`), which reads attachment *contents* by
name from `prependedDocs`/`appendedDocs` and never goes through `_load_node`'s
filtered name list: add `and self._within_store(f)` to both `f.is_file()` tests.

**Verify, do not assume, the four sibling reads that bypass `_load_node`.** Each
reads `meta.yaml`/`description.md` directly and must be checked at `implement`
against the current tree — guard the ones reachable with a caller-supplied
identifier, and record a verdict for each in `outcome.md` either way:

| Site (at `5ddaa31`) | What it reads | Note |
| --- | --- | --- |
| `get_detail` `:1376-1377` | both, via `owner.root / term.slug` | `read_text` with no `exists()` guard — an escaped path raises rather than returning empty |
| `update_term` `:1412-1413` | both, local-only | write path; reached after a `get()` |
| `_apply_override` `:1588-1591` | upstream + child `description.md` | upstream root is already resolved (`:692`); the **child** side is local and is the one to check |

**Verified by** new tests in `tests/test_store_bounds.py`, one per store class:
an in-store node whose `meta.yaml` is a symlink out resolves to `None`/absent and
its external content never appears in any returned object; the same for a
symlinked `description.md` (body comes back empty, not external); the same for a
symlinked attachment named in `prependedDocs` (its text is absent from the
composed body). Each needs an **in-store control** in the same test — an ordinary
node whose `meta.yaml` and `description.md` are real files, asserted to still
read normally — or the test cannot distinguish "guard worked" from "fixture
broken".

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

### 3b. Targeted capability validation — the eleventh guard

**New in review round 1 (blocker 2).** This is the site the walk missed, and it
is the third time this walk has missed one — after `_validation_resources` at
plan time and `_write_target` at spec-review time. Treat the walk as evidence,
never as a discharge.

`check(identifier=…)` builds its meta-dir list by **replacing** the filtered
listing (`tcw/store/fs.py:1937-1938` at `5ddaa31`):

```python
meta_dirs = self._all_meta_dirs()
if selected is not None:
    meta_dirs = [selected.path]          # ← the filter is discarded
for p in meta_dirs:
    d = self.root / p                    # :1941
    meta = load_yaml(d / "meta.yaml")    # :1942 — external read
    …
    for f in d.iterdir():                # :1946 — external listing
```

The plan's table cleared this as "no — filtered listing; it `iterdir()`s `d`, so
the filter is load-bearing". True for the `_all_meta_dirs()` branch, **false for
the `selected` branch**, and false in exactly the case the guards create: Task 3's
`get_local` guard rejects a local symlink shadow, so `get()` falls through to the
**inherited** capability with the same `path` — and that inherited path is then
re-joined under the **local** root here. The reviewer reproduced it while
simulating this plan's own Task 3 guards: `base/link/thing` was selected, the
local external `meta.yaml` was loaded, and `check()` returned **no problems** —
a clean bill of health computed from a file outside the store.

**Changes** `tcw/store/fs.py`, `FsCapabilitiesStore.check` — guard `d` before the
`load_yaml`, skipping the entry rather than raising (`check` must not crash on
bad data; that is criterion 4's whole point):

```python
for p in meta_dirs:
    d = self.root / p
    if not self._within_store(d):
        continue
```

Placed before `load_yaml`, not appended to a later condition — the same
read-ordering rule the spec sets out for capabilities `get_local`.

Task 1b's `_load_node` guard does **not** cover this: the read here is a direct
`load_yaml`, not a node load.

**Verified by** a new test in `tests/test_capabilities_federation.py` (it needs
the `child_of` helper): a federated `base` → `child`, an upstream capability at
`link/thing`, a local `docs/capabilities/link -> ../../outside` shadow, and
`check(identifier="link/thing")` must not read `outside/thing/meta.yaml` — spied
with the same `load_yaml` recorder criterion 7 uses, plus an in-store control.
**This test fails on today's tree and on the tree with Tasks 1-3 applied**, which
is what distinguishes it from a test that merely passes.

The reviewer also notes the existing criteria test taxonomy `check` but never the
capability `check` path; this test closes that gap.

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

### 5. The CLI error boundary — satisfied, and now a trap to test against

**Changes** none — but the reason is the opposite of what this task used to say.
*(Rewritten in review round 1.)*

The original text treats the generic `CalledProcessError` handler as owned by an
in-flight sibling and asks this item to stay out of its way. That item is
**completed**, and the handler has **landed** at `tcw/cli.py:190` (since hardened
for a string-valued `error.cmd`). The dependency is satisfied; nothing to
coordinate.

What replaces it is a testing hazard, and it is sharper than the thing it
replaces. **Every git failure now exits 1 with a clean one-line message.** So an
assertion of the form "exits 1 with an error" no longer distinguishes:

- the containment guard refusing the ref — what these criteria mean to prove; and
- git refusing to stage *beyond a symlink* — which is how these same scenarios
  fail on the **unfixed** tree, per spec Problem §2, §3 and §6.

A criterion written that loosely therefore **passes before the fix**. Criteria 2,
5 and 6 are written that loosely. They must assert the containment diagnostic
specifically — the guard's own `ValueError` at the store level, or its exact
message at the CLI — alongside the existing "nothing outside the store was
created or mutated" assertions, which are the parts that carry real weight.

Prefer asserting at the **store API** for containment, and use CLI-level
assertions only where the criterion is about the CLI's own output.

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

## Criteria that pass before the fix — rewrite these before writing them

*(Review round 1. Every item here is a test that would be **green on the unfixed
tree**, for a reason unrelated to the guard. Watching a test fail red is the only
protection, and three of the spec's criteria cannot fail red as written.)*

The root cause is one property, worth stating once: **`Path.rglob` does not
descend into a symlinked directory.** The spec relies on that correctly for the
work store (Problem §4: only a symlinked *file* is discoverable) and then writes
three capability/taxonomy criteria whose fixtures depend on the opposite.

- **Criterion 3, descendant half.** `tcw taxonomy list` "lists neither
  `alpha/link` nor any descendant". `rglob` never walks into `alpha/link`, so the
  descendant assertion is already true today and proves nothing about
  `_local_slugs`. The direct `alpha/link` assertion is the real one — keep it,
  drop the descendant claim or mark it explicitly as a property of `rglob` rather
  than of this change.
- **Criterion 5, listing half.** Same defect: with `link -> ../outside` and the
  capability at `outside/thing`, `list_all` cannot see `link/thing` today either,
  because `link` itself holds no `meta.yaml` and `rglob` will not descend it. To
  test `_all_meta_dirs` filtering at all, the fixture must make **`link` itself
  resolve to a folder that contains `meta.yaml`** — then current `list_all`
  demonstrably includes it and the guard demonstrably removes it.
- **Criterion 7, `list_all` half.** Inherits the same broken fixture, so its
  "no external read" assertion passes vacuously. Additionally it cannot see
  `description.md` or attachment reads at all — a `load_yaml` spy only records
  YAML — which is precisely the gap Task 1b exists to close.

Rewritten, criterion 7 needs four things: a fixture where the symlink candidate
itself resolves to a capability folder; separate cases for symlinked `meta.yaml`,
`description.md` and attachments (spying `read_text` as well as `load_yaml`);
coverage of targeted `check` (Task 3b); and an **in-store control** asserting the
spy fires on an ordinary node, so a mis-installed spy reads as a pass.

- **Criterion 8** ("a store reached through a symlink still works") says "behave
  exactly as on the physical spelling" without naming a result, and two stores
  over one physical tree cannot both perform the same `add`. Pin it: a
  git-initialized fixture; `add` **succeeds** (not "both spellings fail
  identically"); exact expected `get` and `list_all` results; and either
  independent trees or a stated operation order.

- **Criteria 2, 5, 6** — see Task 5: "exits 1 with an error" is satisfied by the
  generic git handler on the unfixed tree. Assert the containment diagnostic.

**The blast-radius claim needs its own controls.** A green 1859-test suite is
weak evidence that the listing filters changed nothing, because almost none of
those tests exercise a store containing a symlink. The review found no regression
for ordinary terms, capability nodes, inherited stores, overrides, relators or
symlink-reached roots — but add explicit unchanged-behavior controls for
taxonomy `relators` and leaf-slug lookup, capability `get_by_id`, override
composition, reset, inherited-status review, attachment validation, and targeted
local + inherited `check`.

**One accepted edge, recorded rather than fixed.** `_parent_slug`
(`tcw/store/fs.py:2348`) independently treats any ancestor holding a `state.yaml`
as an item, so a valid nested child under a folder that Task 4 excluded can still
name that excluded folder as its parent. Confirmed code path; whether it violates
intent is a spec question, not a bug this item is required to close. Add a
nested-child test that pins whichever answer is chosen, and say which in
`outcome.md`.

## Documentation Sync

Evaluated all four declared entries. **Source correction (review round 1):**
they are configuration, not prose — they live in `tcw-config.yaml` under
`work.documentation` and are printed by `tcw work docs`. The line below used to
cite `CLAUDE.md`, which is where the *reasoning* lives, not the entries. The four
targets are unchanged: `README.md` `[Public-API]`,
`docs/release-notes/upcoming.md` `[Public-API]`, `docs/changelogs/upcoming.md`
`[Any-Code-Change]`, `skills/<component>/SKILL.md` `[Skill-Driven-Component]`.

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
