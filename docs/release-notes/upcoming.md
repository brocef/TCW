# Upcoming

User-facing release notes for the next version. Plain language — no jargon or
internal module names.

## Improved

- Taxonomy, Capability, and Work trees now use consistent spacing, row
  structure, selection, and metadata at every depth. Expand/collapse controls
  are easier to target, and Work rows use a clear lifecycle-status tint.
- Non-empty filters now have an accessible clear button that preserves the same
  navigation safeguards as typing.
- Reference search results remain on an opaque, bordered surface above the
  editor and preview, including while long result lists scroll.
- Work status filters now live in one `Status` dropdown and use the same compact
  checkbox pattern as the `Tags` filter.
- Work trees can now be sorted by name or last-modified time in either direction
  while keeping active, backlog, and completed items grouped in that order.

## Fixed

- Opening a plan-stage document no longer fails with an empty-JSON-body error.
- Work-item copy controls and other popup content no longer expand to the full
  height of the browser; copy tooltips now display their label normally.
- Long trees now have one scrollbar instead of two synchronized scrollbars.
