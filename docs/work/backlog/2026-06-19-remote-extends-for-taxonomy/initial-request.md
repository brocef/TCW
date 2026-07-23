# Remote extends for taxonomy

## Product changes

## Technical changes

## Meta changes

Remote `extends` source types (git / URL) with version-pinning + fetch/cache, and
the source-relative resolution transitivity rules.

**Model note (refreshed 2026-07-23):** the original "purely additive on the
existing local-path federation model" framing is stale. Federation no longer
resolves local paths directly — `extends` is a list of **registered project IDs**
resolved through the project graph, and the legacy map form is hard-rejected
(`tcw/store/fs.py` `_extends_ids`, which also fails closed on an ID that is not
reachable in the graph). So this item is not "add a new path kind"; it is "add
git/URL as new **locator kinds** backing a registered project ID", with the
fetch/cache layer sitting between the graph lookup and the `FsTaxonomyStore`
construction.

Related: `2026-07-01-transitive-taxonomy-inheritance` covers the transitivity
rules for the local case; that behavior should land first (or together), since
remote sources only make the depth problem more visible.

Spec: docs/plan/phase-6-beyond.md; phase-2-taxonomy A.5, B.9.
