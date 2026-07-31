# Refined outcome

## Decision

Accepted by the user on 2026-07-30.

## Evidence

- Transitive A → B → C taxonomy reads are covered for listing, search, bare and
  qualified resolution, detail reads, and bounded validation resources.
- Canonical source project IDs remain the inherited namespaces.
- Local shadowing, inherited ambiguity, diamond deduplication, and cycle
  diagnostics retain their intended behavior.
- `python -m pytest -q` passed with 1165 tests.
- `tcw taxonomy check`, `tcw capabilities check`, and `tcw validate` passed.
- Documentation Sync and capability reconciliation are complete.

## Deferred follow-ups

- Remote git or URL taxonomy sources remain tracked separately.
- Taxonomy source version pinning remains deferred.
- Transitive capability inheritance was outside this item's scope.

## Closeout

- Integration route: committed directly on `main`.
- Documentation: README, roadmap, release notes, changelog, capability ledger,
  and `tcw-taxonomy` skill updated.
- Follow-up items: none created; existing adjacent backlog items retain their
  scopes.
- Version choice: pending after work-item completion.
