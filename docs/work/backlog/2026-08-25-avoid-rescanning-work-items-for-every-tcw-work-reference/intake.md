# Avoid rescanning every work item for each tcw:// work reference

## Finding

The work-reference existence check intentionally calls FsWorkStore.get once per resolved W reference. FsWorkStore.get locates a slug by scanning every state.yaml under every work status, so a validation or /api/resolve batch with R distinct work references and N work items is O(R x N).

Measured on 2026-08-25 in TCW with 148 work items: 100 distinct missing local work references took about 0.716 seconds, and 100 repeats took about 0.699 seconds. /api/resolve accepts up to 256 URIs, while tcw validate scans every Markdown tcw:// link.

## Scope

Keep the existence semantics and resolve_qualified_work_ref routing contract unchanged. Investigate a request/validation-scoped work-item index or another storage-neutral batch mechanism. Include performance-focused tests that prove repeated resolution does not rescan the same store for every URI, and preserve fresh-enough behavior during lifecycle moves.
