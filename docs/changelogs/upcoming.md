# Upcoming

Developer changelog for the next version. Technical and precise; grouped by
category, with commit hash ranges so entries trace back to source.

## Added

- `2085163..b5fbc05` — Added the storage-neutral `ProjectRegistry` model and
  `FsProjectRegistry`, canonical project-ID validation, reciprocal
  `connected-projects` graph loading, cached config reads, arbitrary absolute or
  relative locators, and graph invariant checks.
- `2085163..b5fbc05` — Added the `connected-project-registry` taxonomy Feature and
  associated it with the eight affected capabilities.

## Changed

- `2085163..b5fbc05` — `tcw init` and component init mirrors accept `--id`; new and
  legacy nodes require it, configured nodes reuse their existing ID, and
  backfill preserves other config.
- `2085163..b5fbc05` — Work topology, qualified refs, boards, coordination, web
  routes, rollups, inbox origin metadata, and `tcw://` work namespaces use
  registered project IDs.
- `2085163..b5fbc05` — Taxonomy and capability `extends` are explicit project-ID
  lists resolved through the graph; the source ID is the inherited namespace.
- `2085163..b5fbc05` — `tcw validate` always validates the complete current project
  graph even when component scanning is narrowed.

## Removed

- `2085163..b5fbc05` — Removed topology discovery by directory walk, git ignore
  state, worktree inspection, filesystem ancestry, path-qualified descendant
  identity, and component alias-to-path inheritance maps.

## Internal

- `2085163..b5fbc05` — Migrated topology, federation, reference, CLI, web, and
  environment-hardness tests to reciprocal registered graphs, including decoy
  trees and out-of-tree locator coverage.
