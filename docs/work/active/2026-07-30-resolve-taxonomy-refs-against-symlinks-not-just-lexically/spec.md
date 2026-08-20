# Spec — Resolve taxonomy refs against symlinks, not just lexically

## Capability changes

None. Every affected capability (`taxonomy/read-a-term`, `taxonomy/add-a-term`,
`taxonomy/remove-a-local-term`, `taxonomy/validate-the-taxonomy`, and the
capabilities-side equivalents) keeps its wording and its `Supported` status; this
restores the boundary those entries already imply. No taxonomy Vocabulary or
Feature entry changes either — "term ref" and "store" are already registered.

## Problem

`_safe_store_id` (`tcw/store/fs.py:728-742`) is a purely lexical guard: it
rejects `..`, absolute paths, backslashes, empty segments and NUL, and never
touches the filesystem. Every store id is then joined onto the store root
(`self.root / slug`, e.g. `tcw/store/fs.py:940`). A **directory symlink planted
inside the store** is lexically clean, so the join lands outside the store.

Reproduced in a scratch repo (`tcw` 0.18.0, all output below is real):

**1. Taxonomy read escapes.** `get_local` (`fs.py:956-966`) gates on
`(self.root / slug).is_dir()` (`:966`), which follows symlinks:

```
$ ln -s ../../capabilities/secret docs/taxonomy/alpha/link
$ tcw taxonomy show alpha/link/victim
Victim  (alpha/link/victim, local)
kind: Vocabulary

SECRET BODY
exit=0
$ tcw taxonomy check
taxonomy OK
```

`--vocab alpha/link/victim` is accepted and stored by the same route
(`_resolve_vocab_ref` → `_require_ref` → `get`), so a ref pointing outside the
store passes write-time validation and `check` reports clean.

**2. Taxonomy _write_ escapes too — the request did not test this.** `add`
(`fs.py:1031-1056`) checks its parent with `(self.root / parent).is_dir()`
(`:1038`), which the symlink satisfies, so the node is written outside the store:

```
$ tcw taxonomy add "Planted" --slug planted --parent alpha/link
… subprocess.CalledProcessError … git add … exit status 128
$ ls docs/capabilities/secret/
planted   victim          # created outside docs/taxonomy/, and left behind
```

The files land; only the `git add` fails. This also contradicts the "fail closed
… a rejected write must leave no partial folder behind" contract at
`fs.py:1047-1049`.

**3. The capabilities store has the same defect, read and write.**
`FsCapabilitiesStore.get_local` (`fs.py:1488-1490`) joins the same way, and
`set` (`fs.py:1669`) writes through it via `_write_target` (`fs.py:1622-1634`):

```
$ ln -s ../outside docs/capabilities/link
$ tcw capabilities show link/thing          # exit 0, prints OUTSIDE BODY
$ tcw capabilities set link/thing --status Supported
… CalledProcessError … git add … exit status 128
$ grep Status docs/outside/thing/meta.yaml
Status: Supported                            # mutated outside the store
```

Note the shape of that read: `get_local` calls `_is_capability()` **and**
`load_yaml()` on the joined path before returning anything. Any containment
guard appended to the end of that expression parses the external YAML first.

**3b. A guard on `get_local` alone does not close the capabilities write path.**
Found by this spec's own join walk, after review. `set` on an *inherited*
capability that has no local override yet routes through `_write_target`
(`fs.py:1622-1653`), which mirrors the upstream path locally — `d = self.root /
cap.path` (`:1643`) — and never consults `get_local`. If a planted local symlink
shadows the first segment of that upstream path, the mirror lands outside the
store. Reproduced against the store API (federated `base` → `child`, upstream
capability at `link/thing`, local `docs/capabilities/link -> ../../outside`):

```
$ tcw capabilities set link/thing --status Partial
… CalledProcessError … git add … 'beyond a symbolic link' … exit status 128
$ cat child/outside/thing/meta.yaml
overrides: base/cap-1
Status: Partial                              # created outside the store
```

The folder and `meta.yaml` are **created**, not merely mutated; only the `git
add` fails. This one needs its own guard — it is the counter-example to the
otherwise-true claim that every capabilities write is downstream of `get_local`.

**4. The work store escapes through a symlinked _file_, not a symlinked
directory.** `_item_dirs` scans each status folder with
`(self.root / status).rglob("state.yaml")` (`fs.py:2059-2076`, the scan at
`:2075`), and `Path.rglob` does not descend into a symlinked **directory** — so
a symlinked item folder is invisible, as originally tested (`tcw work show
sneaky` and `tcw work show wlink/sneaky` both fail as they should). But a
symlink **named `state.yaml`**, sitting in an ordinary in-store item folder,
matches the glob by name. `p.parent` is then accepted as an item folder and
`_read_item` reads the file through `_safe_yaml(d / "state.yaml")`
(`fs.py:2512-2513`), following the link out of the store. Verified directly
against `Path`, not inferred:

```
$ ln -s ../../../outside/state.yaml store/backlog/item/state.yaml
rglob hits:            ['backlog/item/state.yaml']
p.is_symlink():        True
p.read_text():         slug: sneaky / title: OUTSIDE
p.resolve() in store:  False
```

The rest of the work store is narrow by construction and needs no guard:
`_validation_resources` starts from `_find` (`fs.py:2878-2881` → `:2224`), so it
inherits `_item_dirs`' discovery; `inbox_list` skips symlinked entries outright
(`fs.py:2988-2999`, the test at `:2994`); and the recursive folder walk skips
every symlink it meets (`fs.py:2956-2964`, the test at `:2960`).

**5. Deletion still does not escape** — the request's finding holds. `git rm`
refuses to cross a symlink, so `tcw taxonomy rm alpha/link/victim` fails and the
target survives.

**6. Stack-trace leak.** `git` refuses to stage _anything_ beyond a symlink, so
every write path above dies at `git_stage`/`git_rm` (`fs.py:299`, `fs.py:309`)
with a raw `CalledProcessError` traceback: `main()` (`tcw/cli.py:174-182`)
catches only `ValueError`, as does the taxonomy `rm` handler
(`tcw/taxonomy/cli.py:117-121`). Pre-existing, and reproducible without any
planted symlink — a symlinked store root (`docs/taxonomy -> ../real/taxonomy`)
fails identically on `tcw taxonomy add`.

Severity stays low, for the request's reasons plus one: planting the symlink
requires repo write access, and anyone with that can read `docs/capabilities/`
directly. But the escape is not read-only as the request assumed — it writes and
mutates — and "refs are bounded to the store" is a stated property of the system.

## Threat model

The threat is a **statically planted symlink** — one that already exists on disk
when a `tcw` command runs, committed by someone with repo write access or left
by a checkout. Containment is checked by resolving a path and comparing it to
the resolved store root; nothing binds the later `open()`/`mkdir` to the object
that was resolved, so the guard is **TOCTOU-racy by construction**. An attacker
who can swap a directory for a symlink *between* the check and the use defeats
it. That is out of scope and the guard is explicitly **not** a race-safe
security boundary — an attacker with write access to the store during command
execution has cheaper attacks available (editing `meta.yaml` directly). What the
guard restores is the stated property that a store id never names a file outside
its own store.

## Goals

1. A store id that traverses a symlink out of its store resolves to **nothing**
   on every read path (`show`, `get`, ref validation, `check`), in taxonomy and
   capabilities alike, **without reading the external file first**.
2. The same ids are refused on the **write** paths before any file is written —
   no partial node outside the store, no mutated file outside the store.
3. `list` does not advertise an entry — or any descendant of one — that
   `show`/`rm` refuse.
4. A `state.yaml` that is a symlink out of the work store is not discovered as
   an item.
5. Fix containment once at shared filesystem-store chokepoints, not per CLI or
   HTTP caller.

## Non-goals

- **Making symlinked store roots work** (`docs/` or `docs/taxonomy` itself a
  symlink). Verified broken today at `git add`, independently of this fix, and
  it stays broken — this change neither fixes nor worsens it. If it is wanted as
  a deployment shape it is its own item. (Distinct from a store *reached*
  through a symlinked ancestor, which must keep working — see Design.)
- **Supporting symlinks inside a store as a feature.** Federation (`extends`) is
  the sanctioned way to reference another project's taxonomy, and git cannot
  track through a symlink anyway, so nothing that currently works is lost.
- **Race-safe containment.** See Threat model: static symlinks only.
- The leaf-slug fallback matching `meta.yaml`-less directories (recorded in the
  request's Notes) — pre-existing, not an escape, separate item if wanted.
- Hardlinks, bind mounts, and case-insensitive filesystem aliasing. Symlinks are
  the reachable case; the others need privileges the threat model already grants.
- **Work-store surfaces other than item discovery.** The `state.yaml` filter in
  `_item_dirs` is in scope (Problem §4, Goal 4); the inbox needs no change
  because it already rejects symlinks, and no other work-store path joins a
  caller-supplied id onto the root without going through `_find`.
- The abstract `TaxonomyStore`/`CapabilityStore`/`WorkStore` interfaces. Per the
  litmus test, path containment is a filesystem-adapter private detail (a remote
  store has no paths to contain), exactly like the lexical guard it extends.

## Design

**One helper on the shared base, `FsTreeStore` (`fs.py:790`)**, next to the other
root-aware plumbing:

```python
@cached_property
def _resolved_root(self) -> Path:
    """The store root with symlinks resolved. Cached: a store instance lives
    for one command, and the root does not move under it."""
    return self.root.resolve()

def _within_store(self, path: Path) -> bool:
    """True iff `path` is inside the store root once symlinks are resolved."""
    try:
        return path.resolve().is_relative_to(self._resolved_root)
    except OSError:
        return False
```

- **Both sides resolved.** `self.root` is _not_ normalized the same way across
  the three stores, so comparing a resolved path to an unresolved root would
  fail on ordinary inputs:
    - `FsTreeStore.__init__` (`fs.py:805-808`) stores `root` **as given** —
      `FsTaxonomyStore.open`/`FsCapabilitiesStore.open` hand it the lexical
      `<node>/docs/<component>`, so a repo checked out under a symlinked
      ancestor keeps that lexical spelling.
    - Inherited (federated) roots arrive **already resolved**:
      `_extended_component_roots` returns `target.resolve()` (`fs.py:692`).
    - `FsWorkStore.__init__` (`fs.py:2005-2010`) does **not** call
      `super().__init__()`; it resolves `root`, `node_root` and
      `store_git_root` itself.
- **`_resolved_root` must exist for all three stores.** Making it a
  `cached_property` rather than an `__init__` assignment is what achieves that:
  `FsWorkStore` skips the base `__init__`, so anything set there would be
  missing on it, while an inherited descriptor resolves through normal MRO
  lookup and computes on first use. (`FsWorkStore.root` is already resolved, so
  its `_resolved_root` is a cheap no-op.) Cost: the helper does **one**
  resolution per candidate instead of two.
- **Non-strict `resolve()`** resolves the existing prefix and appends the rest,
  so it works for a path being _created_ as well as one being read.
- It stays out of `_safe_store_id`, which is a pure string function shared with
  callers that have no root in hand.

**Guard placement is part of the design, not an implementation detail.** Two
orderings matter:

- On a **lookup**, the cheap existence stat comes first (so a miss pays no
  `resolve()`), containment second, and **any read third**. Taxonomy
  `get_local` already has that shape once the guard is appended. Capabilities
  `get_local` (`fs.py:1488-1490`) does **not**: its existing expression calls
  `load_yaml()` inside the condition, so a guard appended to the end parses
  external YAML before rejecting the path. It must be reordered, not extended.
- On a **listing**, containment comes first, before the `meta.yaml` probe:
  `_all_meta_dirs` (`fs.py:1384-1395`) tests `_is_capability(p)` at `:1393`,
  which stats a file under the symlink target. There is no miss to optimize
  there — every candidate pays containment anyway — so the guard goes in front.

Call sites (the plan walks every `self.root / <id>` join and records a verdict
for each; these are the ones that get a guard):

| Site                                                          | Behavior                                                                                                                                              |
| ------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `FsTaxonomyStore.get_local` (`fs.py:956`)                     | after the lexical guard and the `is_dir()` hit, return `None` if not `_within_store`                                                                  |
| `FsTaxonomyStore.add` (`fs.py:1031`)                          | check the target dir `d` (`:1044`) **before** `d.exists()` (`:1045`); not within → the existing "parent term does not exist" `ValueError`              |
| `FsTaxonomyStore._local_slugs` (`fs.py:968`)                  | drop paths that are not `_within_store`                                                                                                               |
| `FsTaxonomyStore._validation_resources` (`fs.py:1202`)        | refuse the `local_folder` fast path (`:1208`) when it escapes the store                                                                                |
| `FsCapabilitiesStore.get_local` (`fs.py:1488`)                | reordered: stat, containment, **then** `load_yaml` — see above                                                                                         |
| `FsCapabilitiesStore.add` (`fs.py:1563`)                      | refuse `d` (`:1568`) before `d.exists()` and before `_write_node`                                                                                      |
| `FsCapabilitiesStore._write_target` (`fs.py:1622`)            | refuse the resolved write target before returning it — the fresh-override mirror (`:1643`, `:1648`) bypasses `get_local` entirely (Problem §3b)         |
| `FsCapabilitiesStore._all_meta_dirs` (`fs.py:1384`)           | containment **before** `_is_capability(p)` (`:1393`), so listings, opaque-ID lookup, the override index and attachment composition never see an escape |
| `FsCapabilitiesStore._validation_resources` (`fs.py:1829`)    | refuse the `local_folder` fast path (`:1835`)                                                                                                          |
| `FsWorkStore._item_dirs` (`fs.py:2059-2076`)                  | drop a discovered `state.yaml` that is not `_within_store` (Problem §4)                                                                                |

Guarding `get_local` is what makes this a one-place fix on the read side:
`get`, `get_inherited`, `search`, `remove`, `update_term`, `_ref_problem`,
`_require_ref`, `_resolve_vocab_ref` and `check` all route through it, in both
the CLI and the `tcw serve` HTTP writes. The one write that does **not** is
capabilities `set` when it materializes a fresh override (Problem §3b), which is
why `_write_target` is on the list. `get_local` returning `None` (rather
than raising) is the established contract for an out-of-store ref — `check`
catches only `AmbiguousRef`, so a raise would crash `check` on an affected
taxonomy. Consequence: an already-stored ref of this shape reports **dangling**,
matching how the lexical fix treats syntactic escapes.

**CLI error-boundary ownership:** the separate non-Git-writes item owns the
generic `subprocess.CalledProcessError` handler. This item neither implements nor
blocks on it; containment tests assert the store behavior directly and CLI
tests assert only errors produced by the containment guard itself.

**Cost — a lookup number and a listing number, and they are different.**
Measured on this repo (macOS, warm cache): `Path.resolve()` ≈ 7.1 µs and
`is_dir()` ≈ 1.0 µs, against a `get_local()` hit of ≈ 138 µs (YAML parse + two
file reads, the earlier draft's figure and not re-measured here) — so **for a
`get_local` hit** the guard is about **+5%**, and zero
on a miss because it sits behind the existence check. That number characterizes
lookups **only**. Listings (`_local_slugs`, `_all_meta_dirs`, `_item_dirs`) pay
one containment test per discovered directory, i.e. O(directories × path depth)
resolutions with no miss to skip: the full helper measures **17.9 µs** per
candidate with the root resolved on every call and **10.4 µs** with
`_resolved_root` cached, which is why the cache is in the design rather than an
optimization deferred to later. The listing figure is a per-candidate cost, not
a percentage; the plan measures it on a synthetic large tree before the change
is accepted.

## Acceptance criteria

1. With `ln -s ../../capabilities/secret docs/taxonomy/alpha/link` planted:
   `tcw taxonomy show alpha/link/victim` exits 1 with "no such term", and
   `tcw taxonomy add F --kind Feature --vocab alpha/link/victim` is refused.
2. Same fixture: `tcw taxonomy add "Planted" --slug planted --parent alpha/link`
   exits 1 with an error message, and `docs/capabilities/secret/planted/` does
   not exist afterwards.
3. Same fixture: `tcw taxonomy list` lists neither `alpha/link` nor any
   descendant reached through it (`alpha/link/victim`, and a nested
   `alpha/link/victim/deeper` planted for the test).
4. A `vocabulary:` ref that traverses a planted symlink is reported by
   `tcw taxonomy check` as `dangling vocabulary ref`, and `check` exits 1 rather
   than raising.
5. With `ln -s ../outside docs/capabilities/link` planted:
   `tcw capabilities show link/thing` exits 1; `tcw capabilities set link/thing
--status Supported` exits 1 **and** `docs/outside/thing/meta.yaml` is
   byte-identical to before; `tcw capabilities list` lists neither `link/thing`
   nor any descendant of `link`.
6. **No external write through a fresh override.** With a federated `base` →
   `child` pair, an upstream capability at `link/thing`, and
   `child/docs/capabilities/link` a symlink to `../../outside`:
   `tcw capabilities set link/thing --status Partial` exits 1 **and**
   `child/outside/thing/` does not exist afterwards (today the folder and its
   `meta.yaml` are created — Problem §3b).
7. **No external read.** With `tcw.store.fs.load_yaml` wrapped by a recording
   spy for the duration of the call, `FsCapabilitiesStore.get_local("link/thing")`
   returns `None` **and** the spy recorded no path that resolves outside
   `docs/capabilities/`. (Byte identity in criterion 5 proves no mutation; this
   is the separate claim that the file was never opened.) The same assertion
   holds for `list_all(local_only=True)`.
8. **A store reached through a symlink still works.** An explicit fixture — make
   a real directory `real/`, `ln -s real link`, open the store at
   `link/docs/taxonomy` — satisfies `_within_store(<store root>/alpha)` for an
   ordinary child, and `add`/`get`/`list_all` behave exactly as they do on the
   physical spelling. This is asserted by a dedicated test, **not** inferred
   from the suite passing under `tmp_path`: pytest hands over an already-physical
   path here (measured: `tmp_path` is `/private/var/folders/…`, its own
   `realpath`), so a green suite proves nothing about symlinked roots.
9. **Work store.** With a symlink named `state.yaml` planted inside an ordinary
   in-store item folder and pointing outside `docs/work/`, `tcw work list` does
   not list it, `tcw work show <slug>` fails, and `_validation_resources` returns
   no path outside the store. A symlinked item *directory* stays undiscovered
   too (the pre-existing `rglob` property, locked in by the same test).
10. `pytest` is green, including the existing lexical-escape regressions
    (`tests/test_taxonomy.py:319` — `test_rm_refuses_ref_escaping_the_store` —
    and `:333` — `test_check_reports_escaping_ref_as_dangling`). Green alone is
    not evidence for criteria 1–9; each of those is its own test.

## Risks

- **Missed call site.** The store joins `self.root / <id>` in ~25 places. The
  mitigation is that all but the ten above are downstream of `get`/`get_local`,
  of a filtered listing, or of an `add` that already validated; the plan
  enumerates **every** join with a verdict rather than asserting the claim. This
  risk has already paid out twice — the walk found `_validation_resources` at
  `plan` time and `_write_target` (Problem §3b) at review time, both of which the
  "downstream of `get_local`" argument had wrongly covered.
- **A user with a working symlink today.** Their entry disappears from `list`
  and `show`. Accepted: writes through it already fail, so it was never a
  supported shape. Worth a release-note line.
- **`resolve()` on a broken or looping symlink** raises `OSError` on some
  platforms — hence the `except OSError: return False`; a loop must not crash
  `list`.
- **Perf on large trees.** Listings add one `resolve()` per discovered directory
  (see Cost). `_resolved_root` halves the per-candidate cost; if the synthetic
  measurement still shows a material regression, the fallback is to resolve only
  when the candidate is itself a symlink — sound because `rglob` never descends
  into a symlinked directory, so within a listing walk only the final component
  can be one. Not taken pre-emptively.
- **Cached root lifetime.** `_resolved_root` is computed once per store
  instance. A store is constructed per CLI command and per HTTP request
  (`tcw/serve/__init__.py:396-402`), so the window is one operation; a
  longer-lived store whose root is replaced mid-life would hold a stale value.
  Recorded rather than defended against — the same window the TOCTOU note
  already describes. Note the sibling non-git-writes item deliberately made its
  `require_repository` check **stateless** for the opposite reason: whether a
  repository exists can change under a live store, whereas the store's own root
  identity cannot. Dropping the cache if a reviewer disagrees costs one extra
  `resolve()` per candidate and changes nothing else.
- **TOCTOU.** See Threat model: the guard is not race-safe and does not claim
  to be.
- **Resolver edge cases.** Broken and looping symlinks must fail containment
  without crashing; non-strict resolution must also contain not-yet-created
  write targets. The tests distinguish symlinks from ordinary lexical paths and
  confirm hardlinks remain outside this item's threat model.

## Notes

- Repo-wide sweep for siblings (stage-spec step 6): all three components were
  tested with a planted symlink. Taxonomy and capabilities are affected through
  directory symlinks; the work store is affected only through a symlinked
  `state.yaml` file (Problem §1-4). The scope widened from the request's
  taxonomy-only framing as a result, twice — the second time in review, after
  the original "the work store is verified unaffected" claim turned out to hold
  only for directory symlinks.
- The request's "read-only in effect" severity note is superseded by Problem §2
  and §3: the escape writes. The overall low rating still stands on the
  repo-write-access argument.
- Every `file:line` in this document was re-verified against `tcw/store/fs.py`
  as committed at **`c0b340e`**. The first draft's citations were written against
  a much older revision and were off by roughly 150 lines; they were re-derived
  at `dabf829` during this revision and then shifted again when the sibling
  non-git-writes item landed `c0b340e` (+28 lines) mid-revision. That item is
  still `active` on the same file, so re-check every line number at `implement`
  rather than trusting these.
