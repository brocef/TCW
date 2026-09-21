# Upcoming

Developer changelog for the next version. Technical and precise; grouped by
category.

### Added

- `tcw work tracker create <slug>` — creates a ticket for an item that has none
  and binds it, through the same binding implementation as `tracker link`.
  `--dry-run` reports and writes nothing; `--all` sweeps every open unbound item,
  epics first, skipping items other accounts hold.
- `work.tracker.create` — `project` (required), `issue-type`, `issue-types`
  (`epic` / `bug`, epic wins), `components`, `on-new`. Fails closed with the rest
  of the block; `create:` with nothing under it is reported rather than read as
  absent.
- `work.tracker.statuses.backlog` — where a created ticket is placed. `create`
  refuses when it is unset, before anything reaches the tracker.
- `work.tracker.create.on-new` — `_new` and `_inbox_accept` (raw entries only)
  create and bind. Epics included, unlike strict mode's `and not args.epic`.
- `JiraClient.create_issue`.
- `tcw/tracker/create.py` — `create_and_place`, `placement_target`, `unplaceable`,
  `description_document`.
- `created` and `owed` records in `tracker.yaml`, both carrying no `ticket` key so
  the item stays `Unbound`. `created` survives an interrupted run so the next one
  binds rather than duplicates; `owed` records a ticket filing could not make.
- `WorkItem.tracker` gains a fourth shape, `{"owed": {"since", "reason"}}`, and
  the projection schema with it.

### Changed

- `TRACKER_STATUS_KEYS` gains `backlog`. `deliver` never computes a target for a
  backlog item, whatever `statuses` says — without that, `sync` pulled a bound
  backlog item's ticket backwards.
- `_tracker_link` takes a `verb`, so `create` binding through it names the command
  the user actually ran.
- `_create_one` collects refusal text for callers that record rather than print.

### Fixed

- `tcw validate` reports `strict: true` with `create.on-new: true`, naming both.
