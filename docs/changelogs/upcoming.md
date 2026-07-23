# Upcoming

Developer changelog for the next version. Technical and precise; grouped by
category, with commit hash ranges so entries trace back to source.

## Internal

- Backlog audit (`cbb52c8..HEAD`): registered the `remote` and `tech-debt` work
  tags; tagged eight backlog items; refreshed four stale request bodies
  (`remote-extends-for-taxonomy` for the ID-based project graph,
  `tracker-sync-for-capabilities` for the `meta.yaml` `Tracker` key,
  `concurrency-safe-work-claims` for the `tcw-config.yaml` sentinel, and the
  rich-Markdown-editor item for the post-rewrite React/Vite web client);
  retargeted `transactional-multi-file-writes` at the shared
  `FsTreeStore._write_node` helper. Closed three items:
  `per-object-capability-revision-token` and `live-browser-test-pass`
  (superseded), `additional-capability-sidecars` (wontfix).
- `web/e2e/parity.spec.ts`: assert the complete modal's
  `.reconciliation-reminder` callout in the lifecycle scenario, closing the last
  coverage gap from the retired live-browser-test item.
