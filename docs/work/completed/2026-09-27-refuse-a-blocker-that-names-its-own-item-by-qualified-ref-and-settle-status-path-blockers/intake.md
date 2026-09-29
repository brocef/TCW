# Refuse a blocker that names its own item by qualified reference, and settle status-path blockers

Left by the review of
`2026-09-09-resolve-a-cross-node-external-blocker-against-the-node-that-owns-it`
(2026-09-27). Both predate that change — each blocked forever before it too.

1. **Self-blocks and cycles through a qualified reference.** In node `pa`,
   `tcw work edit <s> --blocked-by pa/<s>` is recorded as `external:` because
   `WorkStore._entry_for` only probes the bare slug, so the item blocks itself
   and `start` needs `--force`. A cycle across nodes (A/x waits on B/y, B/y on
   A/x) is not detected either. The cheap half: record a reference qualified
   with this node's own id as `slug:`, so the existing self-block and cycle
   checks see it.
2. **A status-path locator as a blocker** (`completed/<slug>`, `active/<slug>`,
   as `tcw work path` prints) is stored as external text and never resolves.
   Normalise it to the bare slug when the blocker is written.
