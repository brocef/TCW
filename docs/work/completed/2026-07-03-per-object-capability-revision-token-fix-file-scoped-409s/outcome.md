# Outcome — superseded

Closed without implementation on 2026-07-23 (backlog audit): the problem this
item describes can no longer occur.

## Why

The request assumed capabilities were Markdown entries under `## capability`
headings, several per file, with the revision token derived from a hash of the
whole file (`_revision(file_text)`). Under that layout, editing capability B
rotated the token for co-located capability A and produced a spurious `409`.

Capabilities are now **folder nodes** — one capability per directory, holding its
own `meta.yaml` + `description.md`. The revision token is already scoped to the
individual capability:

- `tcw/store/fs.py` `FsCapabilitiesStore.get_capability_detail` hashes only that
  node's own texts (plus, for an inherited entry, its local override's files)
  via `_revision_multi`.
- No `## capability` heading parsing remains anywhere in `tcw/`.
- `docs/capabilities/` is folder-per-entry throughout.

Two edits to different capabilities therefore hash independently, which is the
outcome this item asked for. No regression test was added: the multi-capability
file format it would exercise no longer exists.

## Resolution

`superseded` — by the folder-node capability layout, not by another work item.
