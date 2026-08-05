# Remote extends for taxonomy

## Product changes

## Technical changes

## Meta changes

Remote `extends` locator types (Git / URL) with version pinning and a bounded
fetch/cache lifecycle.

**Model note (refreshed 2026-07-23):** the original "purely additive on the
existing local-path federation model" framing is stale. Federation no longer
resolves local paths directly — `extends` is a list of **registered project IDs**
resolved through the project graph, and the legacy map form is hard-rejected
(`tcw/store/fs.py` `_extends_ids`, which also fails closed on an ID that is not
reachable in the graph). So this item is not "add a new path kind"; it is "add
git/URL as new **locator kinds** backing a registered project ID", with the
fetch/cache layer sitting between the graph lookup and the `FsTaxonomyStore`
construction.

`2026-07-01-transitive-taxonomy-inheritance` completed the transitive read
behavior. It is prior art, not remaining scope for this item.

Before implementation, specify:

- the locator schema attached to a registered project ID and compatibility with
  existing local locators;
- immutable pinning and explicit update semantics;
- fetch, cache, invalidation, and offline fallback behavior;
- authentication without credentials entering tracked configuration;
- trust boundaries and integrity verification for fetched content;
- deterministic errors for unavailable, untrusted, or invalid sources.

Spec: docs/plan/phase-6-beyond.md; phase-2-taxonomy A.5, B.9.
