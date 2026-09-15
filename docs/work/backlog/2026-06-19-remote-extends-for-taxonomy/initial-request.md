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

## Discarded 2026-09-15 as superseded (backlog audit)

The Git-sourced half of this request shipped through other items:
`2026-08-26-generalize-the-store-declaration-to-taxonomy-and-capabilities`,
`2026-09-03-connected-project-entries-declare-where-they-come-from-so-tcw-provision-can-obtain-a-node`
and `2026-09-04-override-where-a-connected-project-lives-on-this-machine`. A
`connected-projects` entry can carry `repository: {url, ref, path, checkout}`,
`tcw provision` clones it into a per-machine cache (`--refresh` updates it), and
`extends` resolves through that same project registry.

Four gaps were still real at discard time. File a fresh item if one is needed:

1. `extends` only reaches projects in the validated parent/child graph, and every
   connection must be declared from both sides (`tcw/store/project.py`, the
   "nonreciprocal connection" check). A project cannot inherit a shared
   vocabulary from a repository that does not list it as a child.
2. No immutable pin or integrity check: `ref` is any string passed to
   `git checkout`, so a branch name is accepted.
3. No source other than Git (no plain URL source).
4. Source-relative resolution transitivity (phase-2-taxonomy B.6) is still marked
   "deferred to remote extends" in `docs/plan/phase-2-taxonomy.md` B.9.
