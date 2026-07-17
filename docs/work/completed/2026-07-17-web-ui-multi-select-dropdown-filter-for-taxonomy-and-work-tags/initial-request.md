# Web UI: multi-select dropdown filter for taxonomy and work tags

## Requested outcome

In the `tcw serve` web interface, add a filter **control distinct from the
existing free-text filter field** for narrowing the object list by category:

- **Taxonomy:** filter by kind — Feature / Vocabulary — via a drop-down with a
  **checkbox per option** (multi-select).
- **Work tags:** reuse the same control to filter work items by **tag**, where
  the user can select multiple tags and the board shows items carrying **one or
  more** of the selected tags (OR semantics; leverage the multi-selection).

The idea is one reusable multi-select dropdown component used for both the
taxonomy kind filter and the work-tag filter, complementing (not replacing) the
text filter.

## Constraints / notes

- Web-UI-only (frontend in `tcw/serve/static/`, possibly a read-only endpoint
  for the available tag/kind options).
- The work-tag half depends on tags existing on work items and a way to read
  the registered tag set — hence the blocking relation below.

## Dependencies

- **Blocked by** `2026-07-17-add-tags-to-work-items-for-filtering` — work items
  need tags (and a registered-tag read path) before the web tag filter is
  meaningful. The taxonomy-kind half could ship independently, but this item is
  scoped as one reusable control covering both.

## Status

Captured during the tags planning session (2026-07-17). Not yet planned —
plan with `/tcw-plan-work` once the tags item lands.
