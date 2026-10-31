## Added

- `tcw/ownership.py`: `check_owned`, the one ownership check every command and
  web route that changes or deletes an object runs, and the `writes` marker on
  the write methods of the work backend and the tree stores. (TCW-114)
- The web route table's `writes`, which the router checks before a write route
  runs (403 for another project's object). (TCW-114)
- The global option `-C <folder or address>`. (TCW-114)
- `tcw/move.py`, the move and rename commands' order of checks, writes and
  tidying; `tcw/rewrite.py`, which rewrites references in records and
  documents (`rewrite_yaml`, `rewrite_links`, `rewrite_references`,
  `mentions`); `tcw/reference_fields.py`, the one list of fields that hold
  object references. (TCW-114)
- `tcw work move`, `tcw taxonomy rename|move`, `tcw capabilities rename|move`.
  (TCW-114)
- `move_object_folder` and `remove_emptied` in `tcw/object_folders.py`;
  `item_prefix` in `tcw/work/model.py`; `code_spans` and `links_outside_code`.
  (TCW-114)
- A Jira item's state file may hold `parent` and `blocked-by`, for references
  Jira cannot link. (TCW-114)
- The fake Jira's `fail_edit` (with `then_unreachable` and `status`).
  (TCW-114)

## Changed

- The backend operation `rename` became `move(id_path, new_id_path,
before_folder)`, returning the old and new identifiers. The files backend
  writes its state files, then the repository's references, then moves the
  folder; the Jira backend reads each ticket again just before setting its
  `TCW Item`, and never sets one back. (TCW-114)
- `tcw work rename` works on an item with nested items and prints one
  `<old> -> <new>` line per identifier; it takes `--json`. (TCW-114)
- Every reference checker reads the one list of fields;
  `reference_problems` takes triples. (TCW-114)
- `tcw validate` checks recorded Jira references offline, and `--remote`
  reports a ticket with both a Jira parent and a recorded one. Jira sites are
  compared by host, ignoring letter case. (TCW-114)
- The web create and edit answers carry, as warnings, the backend's lines
  about a parent or blocker: one Jira records rather than links, and a nested
  folder not made under another project's parent. The backend's other lines,
  such as which files it wrote, go to the server's standard error as before.
  A Jira-mode create accepts blockers in other projects. (TCW-114)
- The plan stage prompt's step 6, the `audit-backlog` procedure and
  `docs/lifecycle/abstraction.md` describe making a part in its own project
  and the `move` operation. (TCW-114)
- The passages of the skills, guides, `README.md`, `docs/use-cases.md` and the
  ledger that wrote a removed option as a command now name one that works.
  (TCW-114)

## Removed

- `tcw work new --project` and `tcw work edit --blocks`, kept only to give a
  message. (TCW-114)
- Delegation: `delegate`, `open_for_update`, `uncommitted_changes`,
  `_check_declared`, `_check_target`, `_uncommitted_in`, `blocks_target`,
  `delegate_to_jira` and its helpers, the server's `delegate` service, the
  `/blocks` route, `BlocksForm` and the create form's project selector.
  (TCW-114)
- `read-only` in `tcw projects list --json` and `readOnly` in the web
  project answer; the registry's `read_only_reason`, which nothing else used;
  `_own`; `report_mentions`; `_strip_code`; TCW-111's refusal to rename an item with nested
  items. (TCW-114)
- The `work/delegate-a-work-item-to-another-project` capability record.
  (TCW-114)

## Internal

- `tests/move_stops.py`, which stops a move at every write in turn and checks
  that running it again finishes it; `tests/processes.py`; the sweep guards
  in `tests/test_ownership_sweep.py` and `tests/write_callers.py`; the
  `-C`-aware command checkers. (TCW-114)
