# Spec — Resolve taxonomy refs against symlinks, not just lexically

## Capability changes

None. Every affected capability (`taxonomy/read-a-term`, `taxonomy/add-a-term`,
`taxonomy/remove-a-local-term`, `taxonomy/validate-the-taxonomy`, and the
capabilities-side equivalents) keeps its wording and its `Supported` status; this
restores the boundary those entries already imply. No taxonomy Vocabulary or
Feature entry changes either — "term ref" and "store" are already registered.

## Problem

`_safe_store_id` (`tcw/store/fs.py:553-567`) is a purely lexical guard: it
rejects `..`, absolute paths, backslashes, empty segments and NUL, and never
touches the filesystem. Every store id is then joined onto the store root
(`self.root / slug`, e.g. `tcw/store/fs.py:772`). A **directory symlink planted
inside the store** is lexically clean, so the join lands outside the store.

Reproduced in a scratch repo (`tcw` 0.18.0, all output below is real):

**1. Taxonomy read escapes.** `get_local` (`fs.py:772-782`) gates on
`(self.root / slug).is_dir()`, which follows symlinks:

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
checks its parent with `(self.root / parent).is_dir()` (`fs.py:854`), which the
symlink satisfies, so the node is written outside the store:

```
$ tcw taxonomy add "Planted" --slug planted --parent alpha/link
… subprocess.CalledProcessError … git add … exit status 128
$ ls docs/capabilities/secret/
planted   victim          # created outside docs/taxonomy/, and left behind
```

The files land; only the `git add` fails. This also contradicts the "fail closed
… a rejected write must leave no partial folder behind" contract at `fs.py:863`.

**3. The capabilities store has the same defect, read and write.**
`FsCapabilityStore.get_local` (`fs.py:1275-1277`) joins the same way, and
`set` writes through it:

```
$ ln -s ../outside docs/capabilities/link
$ tcw capabilities show link/thing          # exit 0, prints OUTSIDE BODY
$ tcw capabilities set link/thing --status Supported
… CalledProcessError … git add … exit status 128
$ grep Status docs/outside/thing/meta.yaml
Status: Supported                            # mutated outside the store
```

**4. The work store is _not_ affected** — verified. It discovers items with
`(self.root / status).rglob("state.yaml")` (`fs.py:1828`), and `rglob` does not
descend into symlinked directories; `tcw work show sneaky` and
`tcw work show wlink/sneaky` both fail as they should.

**5. Deletion still does not escape** — the request's finding holds. `git rm`
refuses to cross a symlink, so `tcw taxonomy rm alpha/link/victim` fails and the
target survives.

**6. Stack-trace leak.** `git` refuses to stage *anything* beyond a symlink, so
every write path above dies at `git_stage`/`git_rm` (`fs.py:262`, `fs.py:267`)
with a raw `CalledProcessError` traceback: `main()` (`tcw/cli.py:166-173`)
catches only `ValueError`. Pre-existing, and reproducible without any planted
symlink — a symlinked store root (`docs/taxonomy -> ../real/taxonomy`) fails
identically on `tcw taxonomy add`.

Severity stays low, for the request's reasons plus one: planting the symlink
requires repo write access, and anyone with that can read `docs/capabilities/`
directly. But the escape is not read-only as the request assumed — it writes and
mutates — and "refs are bounded to the store" is a stated property of the system.

## Goals

1. A store id that traverses a symlink out of its store resolves to **nothing**
   on every read path (`show`, `get`, ref validation, `check`), in taxonomy and
   capabilities alike.
2. The same ids are refused on the **write** paths before any file is written —
   no partial node outside the store, no mutated file outside the store.
3. `list` does not advertise an entry that `show`/`rm` refuse.
4. Fix containment once at shared filesystem-store chokepoints, not per CLI or
   HTTP caller.

## Non-goals

- **Making symlinked store roots work** (`docs/` or `docs/taxonomy` itself a
  symlink). Verified broken today at `git add`, independently of this fix, and
  it stays broken — this change neither fixes nor worsens it. If it is wanted as
  a deployment shape it is its own item.
- **Supporting symlinks inside a store as a feature.** Federation (`extends`) is
  the sanctioned way to reference another project's taxonomy, and git cannot
  track through a symlink anyway, so nothing that currently works is lost.
- The leaf-slug fallback matching `meta.yaml`-less directories (recorded in the
  request's Notes) — pre-existing, not an escape, separate item if wanted.
- Hardlinks, bind mounts, and case-insensitive filesystem aliasing. Symlinks are
  the reachable case; the others need privileges the threat model already grants.
- The work store — verified unaffected (Problem §4), no change.
- The abstract `TaxonomyStore`/`CapabilityStore` interfaces. Per the litmus test,
  path containment is a filesystem-adapter private detail (a remote store has no
  paths to contain), exactly like the lexical guard it extends.

## Design

**One helper on the shared base, `FsTreeStore` (`fs.py:615`)**, next to the other
root-aware plumbing:

```python
def _within_store(self, path: Path) -> bool:
    """True iff `path` is inside the store root once symlinks are resolved."""
    try:
        return path.resolve().is_relative_to(self.root.resolve())
    except OSError:
        return False
```

- **Both sides resolved.** A repo legitimately checked out under a symlinked
  path (macOS `/tmp` → `/private/tmp`, the default for `tmp_path` tests) would
  otherwise fail every check.
- **Non-strict `resolve()`** resolves the existing prefix and appends the rest,
  so it works for a path being *created* as well as one being read.
- It stays out of `_safe_store_id`, which is a pure string function shared with
  callers that have no root in hand.

Six call sites, three per store:

| Site | Behavior |
|---|---|
| `FsTaxonomyStore.get_local` (`fs.py:772`) | after the existing lexical guard and the `is_dir()` hit, return `None` if not `_within_store` |
| `FsTaxonomyStore.add` (`fs.py:847`) | check the target dir `d` **before** `d.exists()`; not within → the existing "parent term does not exist" `ValueError` (checking `d` covers the `--parent` case, since a non-existent leaf resolves through its parent) |
| `FsTaxonomyStore._local_slugs` (`fs.py:784`) | drop paths that are not `_within_store` |
| `FsCapabilitiesStore.get_local` (`fs.py:1304`) | return `None` if not `_within_store` |
| `FsCapabilitiesStore.add` (`fs.py:1379`) | refuse with `ValueError` before `_write_node` |
| `FsCapabilitiesStore._all_meta_dirs` (`fs.py:1200`) | drop paths that are not `_within_store` before listings, opaque-ID lookup, overrides, or attachment composition consume them |
| Both `_validation_resources` methods (`fs.py:1018`, `:1645`) | refuse the local-folder fast path when it escapes the store |

Guarding `get_local` is what makes this a one-place fix on the read side:
`get`, `get_inherited`, `search`, `remove`, `update_term`, `set`, `_ref_problem`,
`_require_ref`, `_resolve_vocab_ref` and `check` all route through it, in both
the CLI and the `tcw serve` HTTP writes. `get_local` returning `None` (rather
than raising) is the established contract for an out-of-store ref — `check`
catches only `AmbiguousRef`, so a raise would crash `check` on an affected
taxonomy. Consequence: an already-stored ref of this shape reports **dangling**,
matching how the lexical fix treats syntactic escapes.

**CLI error-boundary ownership:** the separate non-Git-writes item owns the
generic `subprocess.CalledProcessError` handler. This item neither implements nor
blocks on it; containment tests assert the store behavior directly and CLI
tests assert only errors produced by the containment guard itself.

**Cost.** Measured on this repo: `Path.resolve()` ≈ 8.4 µs vs `is_dir()` ≈
0.85 µs, against a `get_local()` hit of ≈ 138 µs (YAML parse + two file reads) —
about +6% on a hit, and zero on a miss because the guard sits behind the
existence check.

## Acceptance criteria

1. With `ln -s ../../capabilities/secret docs/taxonomy/alpha/link` planted:
   `tcw taxonomy show alpha/link/victim` exits 1 with "no such term", and
   `tcw taxonomy add F --kind Feature --vocab alpha/link/victim` is refused.
2. Same fixture: `tcw taxonomy add "Planted" --slug planted --parent alpha/link`
   exits 1 with an error message, and `docs/capabilities/secret/planted/` does
   not exist afterwards.
3. Same fixture: `tcw taxonomy list` does not list `alpha/link`.
4. A `vocabulary:` ref that traverses a planted symlink is reported by
   `tcw taxonomy check` as `dangling vocabulary ref`, and `check` exits 1 rather
   than raising.
5. With `ln -s ../outside docs/capabilities/link` planted:
   `tcw capabilities show link/thing` exits 1; `tcw capabilities set link/thing
   --status Supported` exits 1 **and** `docs/outside/thing/meta.yaml` is
   byte-identical to before; `tcw capabilities list` does not list `link/thing`.
6. A store whose root is itself reached through a symlink (`tmp_path` on macOS)
   still passes the full existing suite — no ordinary operation regresses.
7. `pytest` is green, including the existing lexical-escape regressions
   (`tests/test_taxonomy.py:244`, `:257`).

## Risks

- **Missed call site.** The store joins `self.root / <id>` in ~17 places. The
  mitigation is that all but the six above are downstream of `get`/`get_local`
  or of an `add` that already validated; the plan must verify that claim by
  walking each of the 17 rather than asserting it.
- **A user with a working symlink today.** Their entry disappears from `list`
  and `show`. Accepted: writes through it already fail, so it was never a
  supported shape. Worth a release-note line.
- **`resolve()` on a broken or looping symlink** raises `OSError` on some
  platforms — hence the `except OSError: return False`; a loop must not crash
  `list`.
- **Perf on large taxonomies.** `_local_slugs`/`_local_paths` add one `resolve()`
  per entry, on a path already `rglob`'d. Measured cost above says this is noise,
  but `list_all` on a big tree is the place to sanity-check it.
- **Resolver edge cases.** Broken and looping symlinks must fail containment
  without crashing; non-strict resolution must also contain not-yet-created
  write targets. The tests distinguish symlinks from ordinary lexical paths and
  confirm hardlinks remain outside this item's threat model.

## Notes

- Repo-wide sweep for siblings (stage-spec step 6): all three components were
  tested with a planted symlink; taxonomy and capabilities are affected, work is
  not (Problem §1-4). The scope widened from the request's taxonomy-only framing
  as a result.
- The request's "read-only in effect" severity note is superseded by Problem §2
  and §3: the escape writes. The overall low rating still stands on the
  repo-write-access argument.
