## Changed

- `request` is legal for an `active` item as well as a `backlog` one
  (`STAGE_STATUSES`), as `spec` and `plan` have been since 2.6.3: nothing moves
  an item back, so work written up after it started had no gate for its
  request. `start_next_stage` returns `request` while the item has neither
  `initial-request.md` nor `spec.md`, and `start`'s warning
  (`_unwritten_planning`, was `_unwritten_plan`) names `initial-request.md` in
  that case too. A request is not asked for once a spec exists. New next-step
  key `start:request`.
- A stage refused by `tcw work stage gate` for the item's status adds a line
  after the unchanged refusal: `tcw work rework` from review, `tcw work start`
  from backlog, `tcw work stage prompt` for either open case, and "no stage runs
  on it" for a resolved item (`_illegal_stage_hint`). `request` in review
  is told to write `initial-request.md` directly, `rework` advice on accepted
  work names `refined-outcome.md` as what is in the way, and `postmortem` on
  an active item names `submit`. The `stage prompt` alternative is offered
  for reading only.
- The "Amending a request" rule (added in this release by
  `2026-09-29-say-where-a-dated-amendment-to-an-item-s-request-belongs`) now
  writes the request with the `request` stage in `active` as well as
  `backlog`, and directly only in `review`. Its own entry, written first,
  says "past backlog"; this supersedes it.
