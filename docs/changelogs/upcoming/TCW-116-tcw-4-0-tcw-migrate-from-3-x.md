## Added

- `tcw migrate`, with `--dry-run` and `--no-jira`: converts a TCW 3.x project
  to 4.0 in place, the one command a 3.x project is not refused. The code is
  `tcw/migrate/`: `legacy.py` (the 3.x readers copied from tag `v3.0.2`),
  `family.py` (the related projects, read in either form and never
  written), `plan.py` (the whole plan, made before any write), `config.py`
  (C1-C8: the configuration, `projects:` and `extends` as parent links, the
  manifests, store locations), `stores.py` and `overrides.py` (C9-C15: state
  files, `cap-…` ids into `.tcw/tcw-migration.yaml`, loose files into
  `resources/`, overrides moved to their original's path), `references.py`
  (C16), `jira.py` (C17, and `edited_tickets` and `restore_tickets`, the way
  back for the tickets), `execute.py` and `progress.py` (phases B to F, the
  progress record, a stopped run finished by running again), `report.py`,
  `editors.py`, `loose.py`, `model.py` and `record.py`. Exit codes 0, 1, 3
  and 5. (TCW-116)
- `JiraBackend.item_values` and `set_item_values`: the search for every
  ticket's `TCW Item` and the edit of it, each checked against the value it
  replaces; used only by `tcw migrate`, and not backend operations. (TCW-116)
- `tcw/config.py` `parse_project_file_text` and `tcw/object_folders.py`
  `parse_state_text`: 4.0's checks of a file's text before it is written.
  (TCW-116)
- `tcw/cli.py` `collect_findings`: an offline `tcw validate`'s findings,
  unprinted, which the check after a migration compares with the run's
  plan; `validate`'s `work` keyword leaves the work store out (`--no-jira`).
  (TCW-116)
- `tcw/store/config_edit.py`: three edits at any depth, a key renamed, a
  top-level key removed and a top-level key set, kept in the file's own
  layout and comments. (TCW-116)

## Changed

- `tcw/rewrite.py` `rewrite_yaml` takes a `replace` function as well as a
  list of changes, and `rewrite_references` also rewrites
  `.tcw/tcw-migration.yaml` (`MIGRATION_RECORD`): a capability's move or
  rename changes the id-paths its `capability-ids` and `moved:` sections
  hold. (TCW-116)
- `tcw.cli._dispatch` skips the 3.x refusal and its other checks for
  `migrate`. (TCW-116)

## Internal

- `tests/migrate/`: the F-single, F-full and monorepo fixtures, built by
  `fixtures.py`; the goldens of what 3.0.2 listed for each
  (`golden/*.json`, recorded by `record_3x_listings.py`, whose fixture
  digests `test_goldens_current.py` checks); a frozen copy of a 3.x
  configuration under `data/`. (TCW-116)
- The guards' exemptions for `tcw/migrate/` and `tests/migrate/`
  (`MIGRATION_FOLDERS`, `MIGRATION_CODE`, `MIGRATION_TESTS`, the identifier
  sweep's), each with a test of its reach; one entry in the git-word guard,
  the git-write scan's new folder, and the ownership sweep's entries for
  the migration's callers and its reading of the working folder. (TCW-116)
- `tests/move_stops.py` drives a Python function as well as a command.
  (TCW-116)
- `tests/test_ledger_3_0.py` reads this repository's records under either
  name. (TCW-116)
