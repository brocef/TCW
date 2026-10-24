## Added

- `tcw.config.INHERITED_KEYS`: `work.tags` and `work.jira`, the keys a
  project takes from its parents, in the order messages name them. (TCW-109)
- `tcw/config_keys.py`: `known_keys` (every key reachable through mappings in
  `.tcw/tcw-config.yaml`, with the kind of value it takes), `jira_keys`,
  `key_part`, `override_name`, `decode_key`, `project_of`, `Override`,
  `is_override`, `read_overrides` and `read_override`, which name and read the
  override variables `TCW_<KEY>__<PROJECT>`. (TCW-109)
- The `environment` configuration layer, the last personal layer, and
  `Origin.variable`, `Origin.project` and `Origin.position`; `Setting.variable`.
  (TCW-109)
- `tcw.config.Withheld`, a value that raises its error only when used, and on
  `Config`: `withheld`, `require(key)`, `sources`, `inherited_problems`,
  `inherited_refusals`, `gaps_withholding`, `order_error` and
  `personal_variables(key_path)`. (TCW-109)
- `ProjectRegistry.source_entries` and `SourceEntry`, the configuration
  sources of a project without raising for a gap, and
  `ProjectRegistry.unavailable`, the one builder of `InheritedUnavailable`'s
  messages, with a `subject` for the configuration. (TCW-109)
- `tcw.store.config_edit`: `SetList(inherit=True)` writes an
  `inherit: true` entry first, and a list holding one is edited in place.
  (TCW-109)
- `tcw.work.open`: `project_facts` and `ProjectFacts` (every check opening a
  work store makes, without building a backend), `external_stages_of`,
  `item_folders` and `read_layered`. (TCW-109)

## Changed

- `load_config` folds a project over its configuration sources: the built-in
  values, then for each source, farthest first, its shared file, the
  user-wide file (checked once, as the active project's own) and its local
  file, then the override variables naming it. From another project only
  `work.tags`, and `work.jira` when the project's own `work.backend` is
  `jira`, are taken. A problem in such a value withholds the key with a
  `ConfigError` rather than going into `Config.problems`; a source not here
  withholds each key no later layer replaces whole with
  `InheritedUnavailable` (exit 7); when the sources cannot be had, the keys
  the project does not set are withheld with the graph problem. (TCW-109)
- `load_config(personal=False)` takes the command's `registry`, required for a
  project that declares `parents:` (`TypeError` without it), and applies the
  override variables that passed every check, reporting none. Every caller
  passes one: `open_project`, `delegate`, `open_for_update`,
  `delegate_to_jira(registry=)`, the web app's item suggestions and the
  reference checks. `effective`, `read_work_config` and `open_backend` take
  `registry=` too. (TCW-109)
- `Origin.rank` is `(position, layer)`, so a later project outranks an
  earlier one when a parser problem is blamed on a layer. (TCW-109)
- `inherit: true` is accepted in `work.tags`, and the refusal elsewhere names
  `work.tags`; `null` at `work.tags` or `work.jira`, or under them, in a shared
  file removes the inherited value. (TCW-109)
- `_allowed` speaks for an override variable when given its name. (TCW-109)
- `validate_changes` reads the registered tags only when a tag is added.
  (TCW-109)
- `open_backend` is built on `project_facts`, and in Jira mode requires
  `work.jira` and then `work.tags` before it builds the backend. (TCW-109)
- `tcw work lifecycle`, `docs`, `path` with no item, and `stage prompt` and
  `procedure` with no item no longer open the work store; nor does the check
  that a write targets this project. A reference into a Jira-mode project is
  answered from its item folders, and `reference_resolver` leaves a reference
  unresolved when the project's inherited configuration is not here. (TCW-109)
- `tcw config show` exits 7 for an undecided inherited key and 1 for one a
  parent passes with a problem, printing nothing; `--origin` labels a value
  another project passes with that project's file by its whole path, and a
  variable's value `environment: <NAME>`. (TCW-109)
- `tcw work tags add` writes `inherit: true` first in a child with no list of
  its own; `tcw work tags rm` refuses, exit 3, a tag a parent passes. (TCW-109)
- `tcw validate` adds `; could not check the configuration inherited from it`
  to the finding of each source that left a key undecided, warns at a
  parent's file about a problem in what it passes, and skips the checks an
  undecided key would need. Under an undecided `work.jira`, the keys a layer
  after the last gap sets are still checked, apart from "required": an error
  when the active project sets them, a warning at the parent's file when a
  parent does. That includes a key TCW does not know, even inside one it
  knows or set to an empty mapping, and an entry a parent after the gap
  writes in a `work.tags` list holding `inherit: true`: whether a parent's
  problem is reported is decided by the problem's own key, not by the known
  key it is filed under. (TCW-109)
- A problem the parser finds in an override variable's value starts with the
  variable's name, as the ones found while reading it do. (TCW-109)
- `parse_jira_config` checks a credential variable name that is given when
  the other one is missing, beside the "required" problem. (TCW-109)
- An ancestor, or a project read only for a lookup, whose shared file cannot
  be read at all is placed with no parents and its links unreadable, a gap,
  rather than a graph problem; its manifest entry is no longer also an error.
  A descendant's stays a graph problem. (TCW-109)
- `GET /api/project` gives `tags` as `{"unavailable": …}` when they are not
  known. (TCW-109)
- `work_store_problems` skips the unregistered-tag check when the tags are
  withheld. (TCW-109)

## Internal

- The test suite removes every override variable before each test. (TCW-109)
- `tests/test_inherited_config.py`, `tests/test_config_environment.py`,
  `tests/test_config_keys.py` and `tests/test_config_overrides.py`. (TCW-109)
