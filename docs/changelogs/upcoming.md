# Upcoming

Developer changelog for the next version. Technical and precise; grouped by
category.

## Added

- `WorkItem.tracker`: the item's tracker binding, filled by `FsWorkStore` from
  `tracker.yaml`. `None` when unbound (no file, or no `ticket` key after `unlink`),
  `{"problem": reason}` when unreadable, else `{provider, project, part,
  ticket: {id, key, url}, bound}`, all strings.
- `WORK_ITEM_SCHEMA` declares `tracker` as a closed `oneOf` of those three shapes.
  `SCHEMA_VERSION` stays 1, per the projection's rule that an added field is not an
  incompatible change; a consumer validating against a saved copy of the earlier
  schema will reject the new property. Every `tcw work show --json` document and
  `tcw serve` item payload now carries `tracker`, `null` for unbound items.
- `tcw work show` prints `tracker: <key> (<provider>, part <part>) <url>`, or
  `tracker: tracker.yaml cannot be read (<reason>)`, after the other fields.
  `tcw work list` appends ` | ticket: <key>` (with ` (part <part>)` when not
  `default`) or ` | ticket: unreadable` to a bound item's row, after every existing
  segment.
- Web app: a `Ticket` field on the work item detail (`TrackerField`), linking the
  ticket key to its URL.
- A `tracker.yaml` that cannot be read (not UTF-8, a directory, no permission,
  nested too deep) is reported as that item's problem value rather than failing
  every board read; one removed while it is being read reads as unbound.

## Changed

- `Unbound`, `Malformed`, `Bound` and binding classification (`classify_binding`,
  over parsed YAML) moved from `tcw/tracker/intake.py` to `tcw/store/base.py`, so the
  store classifies a binding without importing `tcw.tracker`. `tcw.tracker.intake`
  re-exports the three classes; `read_binding(content)` now also reports YAML nested
  too deep to parse as malformed instead of raising `RecursionError`.
  `Bound` gains `bound` (excluded from equality). `binding_value` renders the
  `WorkItem.tracker` value.
