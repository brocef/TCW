# Upcoming

Developer changelog for the next version. Technical and precise; grouped by
category, with commit hash ranges so entries trace back to source.

## Added (`f8f95d5..4de80a2`)

- **`review` work status.** `WORK_STATUSES` becomes a 5-tuple:
  `("backlog", "active", "review", "completed", "discarded")`.
  `RESOLVED_STATUSES` is unchanged — `review` is an *open* status, so an item in
  review still counts as an unresolved blocker, still holds its initiative epic
  open, and stays on the default board.
- **Four `LEGAL_TRANSITIONS` edges:** `(active, review)`, `(review, active)`,
  `(review, completed)`, `(review, discarded)`. `(review, active)` is the
  model's first and only reverse edge; nothing transitions out of a resolved
  status.
- **`WorkStore.submit()` / `WorkStore.rework()`** beside `start()` / `complete()`.
  `submit()` carries no gate. `rework()` fails closed while the
  `refined-outcome` artifact is present and content-bearing, reading through
  `artifacts()` rather than probing a path, so the gate stays in the model.
- **`tcw work submit <slug>`** and **`tcw work rework <slug>`**, each with a
  next-step hint on stderr.
- **`WorkItem.pr`** — pull-request URL, persisted in `state.yaml`, set with
  `tcw work edit --pr` (via `set_field`, not the composite `update_work`), shown
  by `show` when non-empty. No consumer yet; it is the field
  `complete --already-integrated` will read.
- **`WORK_ARTIFACTS` gains `rework` and `post-mortem`**, appended rather than
  inserted so no existing item's stage-letter string shifts. Board letters `W`
  and `M`.
- **`tests/test_status_parity.py`** — asserts `web/client/src/model/types.ts`
  and `tree.ts` agree with `WORK_STATUSES`. Verified to fail in both directions
  before landing.
- **`tests/test_work_review.py`** — the transition matrix, the `rework` gate,
  `review`-as-open-status, discovery/addressing, and missing-folder repair.

## Changed (`f8f95d5..4de80a2`)

- **`FsWorkStore._effect_transition` creates the destination status folder**
  (`mkdir(parents=True, exist_ok=True)`) before the move. `git mv` refuses when
  the destination's parent is missing, and nodes scaffolded before `review`
  existed have no such folder. Status-agnostic, so it also repairs a
  hand-deleted folder. Adapter-private: "ensure a directory exists" has no
  abstract analog.
- **`tcw work complete` warns on stderr when invoked from `active`** — that path
  skips the verify stage. `[prompted]`, not a gate: exit status is unchanged and
  no additional confirmation is read. Emitted by the CLI, not by
  `WorkStore.complete()`, since advisory output is not a store concern. The
  status is captured before the transition.
- **`WORK_STATUS_ORDER`** (`web/client/src/model/tree.ts`) gains `review` at
  index 1; `backlog`/`completed`/`discarded` shift to 2/3/4.
- **The board's stage-letter map uses `.get`**, so a name registered in
  `WORK_ARTIFACTS` without a corresponding letter can no longer raise `KeyError`
  in `tcw work list`.

## Removed (`f8f95d5`)

- **`WorkItem.phase`** — the field, its read in the FS loader, the three
  `"phase": ""` `state.yaml` creation sites, the `show` line, and the reconcile
  rollup column. Declared since the first work commit and never assigned a
  non-empty value by any code path; the rollup column read `-` on every row of
  every table.

  **Migration is a no-op and adds no rewrite pass.** The loader ignores unknown
  keys, so an existing `state.yaml` still carrying `phase:` loads normally; and
  `set_field` is a read-modify-write over the raw mapping, so the inert key
  simply persists. Erasing it would mean touching every item's `state.yaml` to
  delete an already-ignored value.

## Internal

- `RESERVED_PROJECT_IDS` derives from `WORK_STATUSES`, so `review` is now a
  reserved project id. `validate_project_id("review")` raises with a message
  naming the collision.
- Two existing assertions updated for the new constants
  (`test_formal_work_statuses_exclude_raw_inbox`,
  `test_artifacts_report_bounded_presence_and_locator`).
