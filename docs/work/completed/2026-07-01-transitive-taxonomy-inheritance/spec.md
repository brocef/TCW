# Transitive taxonomy inheritance

## Capability changes

- Change `taxonomy/federate-shared-vocabulary` so its existing `Partial` capability includes transitive local-project inheritance; keep it `Partial` because remote sources and version pinning remain unsupported.
- Remove only the transitive-inheritance clause from the capability's `Gaps` field.

## Problem

`FsTaxonomyStore` constructs nested stores recursively, but its public reads inspect
only each directly extended store's local slugs (`tcw/store/fs.py:743-751`,
`tcw/store/fs.py:788-816`). Therefore, if A extends B and B extends C, A cannot
list, search, or resolve C's terms.

The model already gives inherited terms a stable qualified address by combining
`Term.origin` with the term slug (`tcw/store/base.py:139-158`). Today `origin`
means the directly configured project ID, which cannot identify a term owned by
a transitive source without either encoding the traversal route or changing the
meaning of the namespace.

Owner-sensitive reads also index the direct `extends` mapping with `origin`
(`tcw/store/fs.py:995-1009`, `tcw/store/fs.py:1033-1042`), so merely returning
transitive terms would make detail and validation-resource reads fail.

## Goals

- Make all taxonomy reads include every transitively extended, reachable local project.
- Preserve the source project's canonical project ID as the inherited namespace,
  independent of which inheritance route reached it.
- Preserve existing single-level addressing and bare-reference resolution.
- Keep inherited taxonomy read-only from the consumer.
- Keep cycles bounded and diagnosed by the existing validation behavior.

## Non-goals

- Remote git or URL taxonomy sources.
- Version pinning.
- Transitive capability inheritance.
- Changing project registration, reachability, or taxonomy `extends` storage.
- Introducing route-shaped aliases such as `b/c`.

## Design

Each filesystem taxonomy store will derive a flattened view of the nested stores
already opened from its direct `extends` declarations. The flattened view is
keyed by the owning project's canonical project ID. A local term in direct
project B therefore has origin `B`; a local term in B's extended project C has
origin `C`, including when C is reachable through more than one inheritance
route.

`list_all`, prefixed lookup, bare lookup, detail lookup, validation-resource
lookup, and search will use that flattened owner map. Local terms still win bare
lookups. A bare slug present in multiple distinct inherited projects remains
ambiguous. Qualified references remain `<source-project-id>/<term-path>`, so
existing direct references are unchanged and transitive references do not expose
the traversal path.

The existing direct `extends` map remains the representation of declarations and
the basis for cycle reporting. Flattening is a read projection, not a new store
operation or persisted structure, so a non-filesystem `TaxonomyStore` can honor
the same abstract contract using its own traversal mechanism.

## Acceptance criteria

- Given A extends B and B extends C, A lists and searches terms local to B and C.
- A resolves C's term through both a unique bare reference and
  `C/<term-path>`, and returns `origin == "C"`.
- Detail and bounded validation-resource reads for a C-owned term use C's store
  and do not raise.
- A local term continues to win over an inherited term with the same bare path.
- Equal bare paths from distinct inherited project IDs remain ambiguous.
- A diamond in which B and D both extend C exposes each C term once under the
  canonical `C/` namespace.
- Existing direct inheritance behavior and cycle diagnostics remain green.
- CLI documentation, the taxonomy-driving skill, release notes, developer
  changelog, roadmap note, and capability gap reflect transitive local
  inheritance without claiming remote sources or version pinning.

## Risks

- Flattening a graph can accidentally duplicate terms reached through a diamond;
  owner-project deduplication must happen before term enumeration.
- Preserving only source project IDs assumes the registered graph enforces their
  uniqueness; taxonomy loading must continue to rely on that validated registry.
- Owner-sensitive paths may be missed if they continue indexing only direct
  extensions; tests must cover detail and validation-resource access.
- Cycle-pruned nested stores may expose a partial graph before `check()` reports
  the cycle; the change must not weaken or bypass the existing cycle diagnostic.
