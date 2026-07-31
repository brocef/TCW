# Upcoming

Developer changelog for the next version. Technical and precise; grouped by
category.

## Added

- `FsTaxonomyStore` now flattens transitive taxonomy sources by canonical
  project ID for list, search, qualified and bare resolution, detail reads, and
  bounded validation resources. Diamond inheritance deduplicates each source,
  while local shadowing and cross-source ambiguity retain their existing
  behavior.
