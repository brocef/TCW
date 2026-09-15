# Upcoming

Developer changelog for the next version. Technical and precise; grouped by
category.

## Added

- `WorkItem.tracker`: the item's tracker binding, filled by `FsWorkStore` from
  `tracker.yaml`. `None` when unbound (no file, or no `ticket` key after `unlink`),
  `{"problem": reason}` when unreadable, else `{provider, project, part,
  ticket: {id, key, url}, bound}`, all strings.
- `WORK_ITEM_SCHEMA` declares `tracker` as a closed `oneOf` of those three shapes.
  `SCHEMA_VERSION` stays 1, per the projection's rule that an added field is not an
  incompatible change; a consumer validating against a saved copy of the earlier
  schema will reject the new property. Every `tcw work show --json` document and
  `tcw serve` item payload now carries `tracker`, `null` for unbound items.
- `tcw work show` prints `tracker: <key> (<provider>, part <part>) <url>`, or
  `tracker: tracker.yaml cannot be read (<reason>)`, after the other fields.
  `tcw work list` appends ` | ticket: <key>` (with ` (part <part>)` when not
  `default`) or ` | ticket: unreadable` to a bound item's row, after every existing
  segment.
- Web app: a `Ticket` field on the work item detail (`TrackerField`), linking the
  ticket key to its URL.
- A `tracker.yaml` that cannot be read (not UTF-8, a directory, no permission,
  nested too deep) is reported as that item's problem value rather than failing
  every board read; one removed while it is being read reads as unbound.

- `work.tracker.statuses` (`active`, `review`, `completed`, `discarded` — a status
  name, or for `discarded` a mapping of `wontfix`/`duplicate`/`superseded` to one).
  `active` is required once any key is set. Parsed into `TrackerConfig.statuses`;
  `target_status()` in `tcw/store/base.py`.
- `tcw/tracker/sync.py`: `deliver()` claims for `start` and otherwise moves a bound
  ticket to the mapped status only when it is assigned to the caller and in the
  expected status; `assess_move()` is the pure check for strict mode to reuse;
  `record_unsent()` for a tracker block with problems. Outcomes `current`, `pending`,
  `conflicting`, `held`, `none`; 401/429/unreachable are pending, other tracker
  errors conflicting.
- `tcw work start|submit|rework|complete` deliver to a bound item's ticket after the
  move, its commit and `post` hooks (and after a `TransitionCommitError`), and exit 1
  when the ticket did not follow. `complete` delivers before auto-deletion and skips
  the deletion when delivery fails.
- `tcw work tracker sync [<slug> | --all]`: retries recorded items, skipping items
  whose `owner` is not the local identity; check-only for an item with no record;
  a `held` item counts as success. When `complete`'s worktree merge fails and the
  item's `tracker.yaml` is staged, a hint names the record.
- `tracker.yaml` `sync` record (`state`, `move`, `since`, `claim`, `reason`, `at`),
  written only when a delivery is pending or conflicting and removed once current;
  `Bound.sync`, `WorkItem.tracker.sync` and a closed `oneOf` in `WORK_ITEM_SCHEMA`.
  An unusable record is `{"problem": …}` and does not unbind the item.
  `with_sync_record()`; `unlink_document()` moves `sync` into the unlinked history.
- `tcw work show` prints `tracker sync: …`; a board row's ticket segment gains the
  state; the web Ticket field appends it.
- `same_site()` in `tcw/tracker/intake.py`; `find_binding(..., base_url=)` raises
  `BindingProblem` for a same-id binding on another site. `import` and `link` pass it.
- Tests: `tests/tracker_fake.py` gains a `SYNC` workflow, `down`, and
  `install_sites()`.

- `work.tracker.strict` (boolean, default false): `TrackerConfig.strict`,
  `WorkStore.tracker_strict()` (concrete, `False`). Strict requires
  `statuses.active`, `statuses.completed` and `statuses.discarded` as a name or a
  mapping of all three resolutions. `FsWorkStore.tracker_strict()` stays true when
  the block has problems, so the gates refuse instead of switching off.
- `tcw/tracker/sync.py`: `authorize(store, slug, client, config, *, target)` —
  bound, same site, no `sync` record, ticket read, assigned to the caller, in the
  mapped status of the item's status or an earlier one, or the target.
  `claim_refusal(client, config, ticket_id, outcome)` — refuses a claim that did not
  land in `statuses.active`, or whose ticket still offers the claim transition
  (`assess()` → `NOT_EXCLUSIVE`). Under strict, `deliver()` runs it after an owed
  claim.
- Strict gates in `tcw/work/cli.py`: `new` (not `--epic`) and `inbox accept` refuse;
  `start` claims before the store move (`_strict_claim`, after the store's own
  status and blocker checks); `submit`, `rework`, and `complete` as `done` call
  `authorize` (`_strict_refusal`), `complete` before the worktree merge-back; `drop`
  refuses when a `tracker.yaml` exists (`ever_bound()` in `tcw/tracker/intake.py`);
  `tracker import` runs `claim_refusal` before creating the item. Discards and epics
  are not gated. Refusals exit 1 and write no `sync` record.
- `tcw serve`: `_strict_refuses()` answers 409 for create (not epic), start,
  complete with `done`, drop of an ever-bound item, and a PUT of `tracker.yaml`.

## Changed

- `expected_statuses(..., shared=)`: when another item here is bound to the same
  ticket, every earlier mapped status is expected, so the last part completing from
  `review` moves a ticket that was held in the `active` status instead of reporting
  it conflicting.

- `Unbound`, `Malformed`, `Bound` and binding classification (`classify_binding`,
  over parsed YAML) moved from `tcw/tracker/intake.py` to `tcw/store/base.py`, so the
  store classifies a binding without importing `tcw.tracker`. `tcw.tracker.intake`
  re-exports the three classes; `read_binding(content)` now also reports YAML nested
  too deep to parse as malformed instead of raising `RecursionError`.
  `Bound` gains `bound` (excluded from equality). `binding_value` renders the
  `WorkItem.tracker` value.
