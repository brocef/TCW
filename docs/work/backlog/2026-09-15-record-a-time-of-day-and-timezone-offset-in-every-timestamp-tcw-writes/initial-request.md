# Record a time of day and timezone offset in every timestamp TCW writes

## Request

Timestamps TCW records, such as a work item's `created`, hold only a date today
(`created: '2026-09-15'`). They should also hold the time of day.

- **Format:** written as the local time of the machine that wrote it, with its
  timezone offset included, so the exact moment (the absolute point in time,
  independent of timezone) can always be recovered. For example
  `2026-09-15T14:03:22-07:00`.
- **Scope, as confirmed by the requester:** every date TCW writes, not only
  `created`.
- **Existing values stay as they are on disk.** A stored value that has a date
  but no time is read as 12:00 (noon) UTC on that date. No migration rewrites
  old files.

Requested together with
`2026-09-15-let-tcw-work-list-sort-by-created-priority-effort-or-title`, which
sorts the board by creation time. The requester chose to track the two changes
as separate items.

## Notes

- Reference material: asked; none provided.
- What the repository holds today, found while taking the request (context for
  `spec`, not decisions):
  - `created` on a work item's `state.yaml` is a date only, and the item's slug
    (its stable identifier and folder name) begins with that date.
  - `resolved` in the record the store keeps for removed items is a date only.
  - The tracker binding sidecar's link and `unlinked-on` dates are dates only.
  - `started` already carries a time, but is written in UTC with a `Z` suffix
    rather than as local time with an offset. Tracker sync also writes UTC `Z`
    times.
  - Inbox entries written by `delegate` and `escalate` begin their file name
    with a date.
  - `tcw serve` accepts a `created` value from the web app when it creates an
    item, and `tcw work tombstone add` accepts a `resolved` value from the user.
  - Nothing shown to a user displays `created` today, including
    `tcw work show`.
- Open for `spec`, not settled by the requester: whether the date prefix of
  slugs and inbox file names is in scope (they are names, not recorded
  timestamps, and changing them would change identifiers); whether the values
  already written in UTC `Z` form switch to local time with an offset; and what
  a caller-supplied date-only input (web app `created`, `tombstone add
  --resolved`) becomes when stored.
