## Added

- `tcw/ids.py`: the grammar of a full identifier,
  `<project>.<namespace>/<id-path>`, and of a `tcw://` address, an object
  address or a folder address `tcw://<project>[.<namespace>].path/<folder>`.
  `FullId`, `FolderAddress`, `parse_full_id`, `parse_address`, `parse_stored`
  (a stored reference, refusing a 3.x value with `ThreeXReference`),
  `sort_input` (command input sorted into the four forms by its text alone),
  and the one recogniser of 3.x references and its messages. (TCW-110)
- `tcw/locate.py`: `Locator`, one per command for the project it acts on,
  which turns a project ID into a folder through the registry's
  `project_folder` and reads the object a full identifier names; `find_tree`
  and `find_tree_writable` for taxonomy and capability commands; the four
  lookup answers `found`, `missing`, `unresolved` and `error`. (TCW-110)
- `tcw.store.fs.store_location`: a component's folder from its configured
  location, a plain path or a `tcw://` folder address followed through the
  named project's own configuration, refusing a loop. (TCW-110)
- `tcw.config.store_location_problem`: an absolute or `~` store location in
  the shared configuration is a configuration error. (TCW-110)
- `web/client/src/model/identifier.ts`: the client's parser and printer of
  full identifiers and addresses, and `keySegments` for the tree. (TCW-110)
- `tcw validate`: stores that are the same folder or one inside the other,
  across this project and every project it can locate, Jira-mode work stores
  included, are an error naming both stores, their projects and folders.
  (TCW-110)

## Changed

- Every record of a taxonomy entry, capability or work item carries `full-id`
  and `owner` in place of `slug`, `qualified`, `path` and `origin`; lists
  print full identifiers; `print_json` writes `"schema": 2`. (TCW-110)
- Every stored reference (a capability's Subject, Feature, Roles, When,
  Blocked by and Superseded by; a term's vocabulary and relatesTo; a work
  item's parent and blockers; each `capabilities.yaml` entry) is a full
  identifier. A 3.x value is reported as needing `tcw migrate`. (TCW-110)
- `tcw/refs.py`: `resolve_address` resolves object and folder addresses
  through the `Locator`; `ResolveResult` gains `project`, `outcome` and
  `folder`; `route_key` gives an inherited entry's web route key, its whole
  full identifier. (TCW-110)
- `tcw/work/gates.py`: `route_capability_path` names the owning ledger from
  the entry's project, not its first folder; a new `Invalid` answer.
  (TCW-110)
- `tcw/work/open.py`: `open_project` looks every project ID up with
  `project_folder`. (TCW-110)
- `<component>.path` takes a relative path or a `tcw://` folder address;
  `tcw init` refuses an absolute or `~` location. (TCW-110)
- The Jira `TCW Item` field holds the item's full identifier; `tcw work list`
  leaves out a ticket still holding a 3.x value with one warning, and
  `tcw validate --remote` reports each. (TCW-110)
- The web server and client send, store and route by full identifier; an
  inherited entry's route key is its URL-encoded full identifier, and
  `/api/resolve` answers a folder address inert. (TCW-110)

## Removed

- `parse_tcw_uri`, the 3.x `.qualified` name, and the `AXIS_WORD` table.
  (TCW-110)
- The tree stores' `get`; `get_view`, `get_local` and `get_inherited` remain.
  (TCW-110)
- Routing a `capabilities.yaml` entry by its first folder name. (TCW-110)
- `_shared_work_paths` in `tcw/validate.py`, replaced by `_store_overlaps`.
  (TCW-110)

## Internal

- `tests/test_identifier_sweep.py`: `findings(root)` reports any 3.x link
  form, `parse_tcw_uri` or `.qualified` outside `tcw/ids.py`, and any
  identifier joined by hand, in TCW's own code; `SKIPPED_FOLDERS` and an
  empty `MIGRATION_FOLDERS` beside it. (TCW-110)
- `tests/projectfiles.py`: `connect_projects`, through which every test of
  this item connects projects by ID; `tests/fullids.py`, helpers that spell
  the full identifiers a test expects. (TCW-110)
