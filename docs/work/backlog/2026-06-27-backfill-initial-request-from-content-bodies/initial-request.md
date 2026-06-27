# Initial request — Backfill initial-request from content bodies

## Requested outcome

Migrate existing TCW work item `content.md` text into `initial-request.md` when
an item does not already have an initial request artifact.

## Constraints

- Preserve existing `initial-request.md` files.
- Leave `content.md` in place because the current store still treats it as the
  work item body.
- Keep the migration simple enough that agents can later promote richer request
  details into `spec.md` or `plan.md` by judgment.
