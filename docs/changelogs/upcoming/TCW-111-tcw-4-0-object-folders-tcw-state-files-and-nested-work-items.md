## Added

- `tcw/object_folders.py`: the one listing of a store's objects. `walk`
  classifies every folder and file under a store root (object, organising,
  misplaced, reserved, 3.x, unmade, extra, loose, a state file at the root);
  `object_paths`, `is_object`, `objects_below`, `folder_parent`,
  `removal_blockers`, `shape_problems` (Design 2.6 rows a to h),
  `length_problems` (row n), `id_problem` (row k), `disagreement` (row m),
  `read_state`, `state_text`, `STATE_FILES`, `LEGACY_STATE_FILES`, reserved
  names per store. (TCW-111)
- A new item's folder can sit inside its parent's folder; a note on standard
  error when the parent is another project's, whose folder cannot hold it.
  `tcw/work/backend.py` `nesting_parent` and `folder_disagreement`. (TCW-111;
  the flags are TCW-118's.)
- `tcw capabilities add --parent` and `tcw capabilities set --parent` (`''`
  clears it; refused on an inherited capability). `parent` on `Term` and
  `Capability`, after `owner` in every record, in `show`, and in the web app's
  records. (TCW-111)
- `tcw/ids.py` `ID_LIMIT` (255), `length_problem`, `parent_text`;
  `tcw/work/model.py` `MIN_TITLE_WORDS`, `words_room`, `fitted_words`. (TCW-111)
- `tcw validate`: rows a to n of Design 2.6 for all three stores, the parent
  checks for terms and capabilities (malformed, another namespace, itself,
  missing, unresolved, a loop), and the folder-and-parent warning for terms,
  capabilities and work items (Jira items under `--remote` only). (TCW-111)
- `tcw/errors.py` `StateFileProblem`; `tcw/output.py` `left_out`: list and
  search name each state file they could not read on standard error and
  exit 1. (TCW-111)

## Changed

- State files are `tcw-taxonomy.yaml`, `tcw-capability.yaml` and
  `tcw-work-item.yaml`, each written with the `tcw-version` line first and
  read by `version_problem`; an existing version line is kept on edit. A
  version problem means the object is never read. An `id` must equal its
  folder's name. (TCW-111)
- Every listing of a store's objects is the walk: the tree stores'
  `_local_slugs`, `_object_dirs` (was `_all_meta_dirs`), `get_local`;
  `read_all`, `Layout.item_folders` (now id-paths at any depth),
  `work_store_problems`, `jira_store_problems`, the Jira lookup and key index,
  the remote check's folders, `round_findings`, the targeted check. A folder
  with no state file is never a term. (TCW-111)
- Both work backends take an item's id-path in every operation, at any depth;
  `create` takes `nest`; `rename` renames within the holding folder and
  checks the 255-character limit.
  `SLUG_HELP` says id-path. In Jira mode a key-named folder needs its state
  file to be an item, and adopt and `tickets list` find a key's folder at any
  depth. (TCW-111)
- A term's attachments, and a capability's `prependedDocs` and
  `appendedDocs`, come from `resources/` only. `tcw validate` does not parse
  YAML under `resources/`, and warns for Markdown there it cannot read.
  (TCW-111)
- `tcw taxonomy add --parent` takes any term TCW can find (exit 4 when none),
  writes `parent:`, and makes the folder inside the parent's only for a term
  of this project's own store. (TCW-111)
- Taxonomy and capabilities `rm` refuse while anything they would delete holds
  a state file or a 3.x file, the latter naming `tcw migrate`. (TCW-111)
- New full identifiers are at most 255 characters: tree `add`, work `create`
  (title words fitted, or refused before anything is written), Jira create
  (refused before the ticket, cut to the key's room after), fresh adoption,
  delegation. The parsers refuse longer input. (TCW-111)
- `docs/guide/examples/commit-item-after-move.sh` leaves items nested in the
  moved one out of its staging and commit. (TCW-111)
- The plan stage prompt nests each part inside its parent's folder;
  `docs/lifecycle/abstraction.md` bounds an object's folder by `resources/`
  and says the interface takes id-paths; the backend docstring counts twelve
  operations. (TCW-111)

## Removed

- `ITEM_FILE`, `_entry_reserved`, the "unlisted extra doc" check, and the
  top-level "is not an item folder" error, which the walk's rows replace.
  (TCW-111)

## Internal

- `tests/statefiles.py` and `tests/objectcli.py`: state files written and
  read one way in the tests. `tests/test_object_folder_sweep.py` keeps the
  3.x names in `tcw/object_folders.py` alone and every directory listing on a
  list of reasons. (TCW-111)
