# Upcoming

Developer changelog for the next version. Technical and precise; grouped by
category.

### Added

- `tcw work tracker create <slug>` — creates a ticket for an item that has none
  and binds it, through the same binding implementation as `tracker link`.
  `--dry-run` reports and writes nothing; `--all` sweeps every open unbound item,
  epics first, skipping items other accounts hold and stopping if a created key
  cannot be recorded locally.
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
- `WorkItem.tracker` gains two shapes, `{"owed": {"since", "reason"}}` and
  `{"created": {"key", "id"}}`, in the projection schema and in
  `TTrackerBinding`. `bound_value` in `tcw/store/base.py` is the one predicate
  for "is this a binding with a ticket"; readers narrow on the presence of
  `ticket`, never on the absence of the other shapes.
- `tracker unlink` clears a `created` or `owed` record on an item that is not
  bound. Nothing else did, so a `created` record naming a deleted ticket was
  unfixable except by hand.
- `record_owed` / `owed_reason` / `without_pending_records` in
  `tcw/tracker/intake.py`; `owed_reason` folds the reason to one line of 200
  characters before it reaches a committed file.

### Changed

- `TRACKER_STATUS_KEYS` gains `backlog`. `deliver` never computes a target for a
  backlog item, whatever `statuses` says — without that, `sync` pulled a bound
  backlog item's ticket backwards.
- `_tracker_link` takes a `verb`, so `create` binding through it names the command
  the user actually ran.
- `_create_one` collects refusal text for callers that record rather than print,
  and prints nothing itself when it is collecting.
- `_sweep_order` selects with `binding_of` / `isinstance(..., Bound)` and
  `RESOLVED_STATUSES` instead of a `"ticket:" in content` substring test and a
  hand-spelled status tuple.
- `ever_bound` asks what the sidecar says instead of whether the file exists.
- `POST /api/work` records an owed ticket under `create.on-new`; the web app
  makes no tracker call.
- `create_and_place` receives `item_url` from `work.tracker.link`.
- `find_binding` raises `BindingProblem` for a sidecar it cannot read, as it
  already did for a malformed one. It scans the whole board, so a read error
  escaped as a traceback while binding an unrelated item.
- `tcw/serve/dist` rebuilt. `tcw serve` serves the committed bundle, not the
  TypeScript source, so a client fix does not ship until it is rebuilt.
  `pnpm check:build` catches this and nothing runs it — not the test workflow,
  which installs no Node, and no test. Worth wiring up separately.

### Fixed

- `_deliver_after` and `_siblings` raised `KeyError` on an item carrying an owed
  record — the first on every lifecycle verb for that item, after its status had
  already moved; the second on lifecycle moves for *every other* bound item on
  the node, because it scans the whole store.
- `TrackerField` in the web client threw on the owed shape. With no error
  boundary in that app, the page rendered blank.
- `tracker create --all` skipped an item whose binding had been unlinked: the
  `unlinked` history contains a nested `ticket:`, which the substring filter read
  as a binding.
- Filing reported "no ticket was created" when creation had succeeded and only
  the binding failed, and recorded the placeholder reason "creating it did not
  succeed" against a ticket that existed.
- The message after a failed placement told the user that running `create` again
  would make a second ticket. With the key recorded it binds that ticket.
- `--dry-run` reported "would create" for an item it would have resumed.
- `strict: true` with `create.on-new: true` is no longer a validation error: `_new`
  exempts epics from strict mode's refusal and creation-on-filing covers them, so
  the pair is a project somebody can mean. Rejecting it made `tracker_config`
  fail closed, taking `import`, `link`, `sync` and `claim` down with it.
