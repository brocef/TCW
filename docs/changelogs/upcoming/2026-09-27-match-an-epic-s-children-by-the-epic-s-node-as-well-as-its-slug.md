## Fixed

- An epic no longer counts a descendant node's slices of that node's own
  same-slug epic, whether the slice is live or known only from the graveyard.
  One rule now matches in both directions: `FsWorkStore._initiative_holder`
  drives `initiative_epic`, `initiative_slices`, `resolved_initiative_children`
  (through `_names_this_epic`) and the nesting in `tcw work list -i`.

## Changed

- `initiative` may be `<project-id>/<slug>`, the same form cross-node blockers
  use, resolved through `resolve_qualified_work_ref`.
  - New `AbstractWorkStore.qualify_initiative`, which returns the value
    unchanged by default. `create_work`, `update_work` and `inbox_accept` store
    through it: bare when the epic is on this board, qualified when it is
    elsewhere.
  - `delegate` always writes the qualified form, and refuses a slug it cannot
    find at or above the sender. `escalate` qualifies relative to the parent.
  - `_graveyard_initiative` now returns `(slug, value)` pairs.
  - An existing bare value keeps its old meaning (the nearest holder at or
    above the item), so there is nothing to migrate.
