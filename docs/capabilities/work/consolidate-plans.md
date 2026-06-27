# Consolidate Plans — capabilities

## Consolidate external plans into TCW work
**Status:** Supported
**Planning doc:** 2026-06-27-consolidate-external-planning-documents-into-tcw-work

As a user, I run `tcw work consolidate-plans [PATH ...]` to find planning
documents that live outside the TCW work system and convert them into TCW work
items. When I omit paths, the command searches sensible project-local planning
locations while excluding `docs/work/` so existing work items are not reimported.

For each accepted external plan, the tool creates a backlog item, preserves the
source document's useful content as lifecycle artifacts, and reports the mapping
from old file to new work slug. Once migration succeeds, I can ask the command to
delete the old documents so the TCW backlog becomes the durable planning source.
