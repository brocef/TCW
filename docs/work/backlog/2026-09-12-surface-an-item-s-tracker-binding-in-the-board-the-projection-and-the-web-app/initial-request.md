# Surface an item's tracker binding in the board, the projection and the web app

## What is being asked for

Child **C5** of `2026-08-04-supplement-filesystem-tcw-work-with-an-external-tracker-bridge`.
A work item bound to a tracker ticket should say so wherever the item is read.
Today the only record is the `tracker.yaml` sidecar that `tcw work tracker import`
and `tcw work tracker link` write, and nothing reads it back for a person: `tcw
work show` and `tcw work list` print no trace of it, `tcw work show --json` has no
field for it, and the web app lists `tracker.yaml` by file name only.

The epic's `spec.md` (§ Design, C5) is the authoritative statement of the boundary
and is not restated in full. In summary it asks for:

- `tcw work show` and `tcw work list` name the provider, the ticket, its link, and
  whether the item is bound or unbound. **Nothing about delivery or drift** — the
  current / pending / conflicting indicator belongs to C3
  (`2026-09-12-synchronize-the-work-lifecycle-outward-to-the-tracker`), which
  creates those states.
- `tcw work show --json` carries the binding, through exactly one of two routes the
  epic names: a `WorkItem` field (which flows into the document and forces the
  matching schema entry in the same change) or a `SCHEMA_VERSION` bump. This
  item's spec picks one and says why. It is not a free-form addition to a document
  whose schema is closed.
- The web app displays the binding and does not offer to change it. The sidecar is
  already marked `generated`, so the web app already offers no edit button for it;
  what is missing is showing what it says.

## Constraints carried from the epic and the completed siblings

- A binding is **never proof that a claim was made**
  (`tcw/tracker/intake.py`, module docstring; epic criterion 11). Anything shown
  here describes what the file records, not what the tracker says. No command in
  this item calls the tracker.
- **No tracker configured means no change** (epic criterion 1): an item with no
  `tracker.yaml` prints exactly what it prints today, on every surface.
- `test_the_schema_declares_exactly_the_model_plus_two`
  (`tests/test_projection.py`) passes without being edited (epic criterion 10).
- Since C6 (`2026-09-14-make-tracker-link-record-a-cross-reference-without-claiming-the-ticket`),
  a binding records what is bound to what and when, and **never who took the
  ticket** — `claimed-by` left the file. There is no claimant to show.
- A binding removed by `unlink` leaves `tracker.yaml` in place with the old binding
  moved under `unlinked:`. That item is unbound, and a surface must not read it as
  bound.
- A malformed `tracker.yaml` must not break the board (the same rule `tcw validate`
  follows for a malformed `work.tracker` block).

## Capability changes the epic planned

The epic's capability table names `work/read-a-work-item` and
`work/open-a-work-item` as changed by C5. The second looks like a slip: `open`
creates an item and C5 does not touch creation, while `tcw work list` is described
by `work/view-the-board`. This item's spec should settle which capabilities change
rather than inherit the table unexamined.

## Notes

- This document was written on 2026-09-14 by an autonomous session driving the
  epic's remaining children. **Everything in it is compiled from existing
  evidence, not taken from a requester**: the epic's `spec.md` § Design C5 and
  § Acceptance criteria 1, 10 and 11; the `work/manage-external-tracker-intake`
  capability's text; the completed siblings C2 and C6; and this item's title. No
  user was available to ask what is unclear or for reference material — asked of
  nobody; none provided.
- Overlap with C3 was considered before ordering the children. C3's indicator is
  added to the same `show` and `list` output this item changes. Doing this item
  first gives C3 a place to put its indicator beside an identity that already
  prints, so the order is C5, then C3, then C4.

## References

- `2026-08-04-supplement-filesystem-tcw-work-with-an-external-tracker-bridge`,
  `spec.md` § Design → C5 and § Risks 1 and 5 — the boundary, and why the closed
  schema needs a deliberate choice.
- `tcw/tracker/intake.py`, `read_binding` — the existing classification of a
  binding as unbound, malformed or bound, which every surface here should reuse
  rather than re-parse.
- `tcw/work/projection.py`, `WORK_ITEM_SCHEMA`, and `tests/test_projection.py` —
  the closed document and the test that pins it.
- `web/client/src/ui/content-views.tsx`, the work item detail view — where the
  sidecar list and the item's fields are rendered today.
- `docs/work/inbox/2026-09-14-a-tracker-binding-does-not-record-its-site.md` — a
  binding's ticket URL is the only record of which Jira site it belongs to, which
  matters for what "its link" means.
