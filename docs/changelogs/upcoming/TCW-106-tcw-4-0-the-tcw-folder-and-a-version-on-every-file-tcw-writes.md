## Added

- `tcw/project_files.py`: the project's own files and the rules every
  `tcw-*.yaml` file follows. `SENTINEL` (`.tcw/tcw-config.yaml`),
  `LOCAL_SENTINEL`, `LEGACY_SENTINEL`; `root_of(config_path)` (the project
  root for a file in `.tcw/`); `find_marker(start)` (the nearest folder holding
  `.tcw/tcw-config.yaml`, or a 3.x root `tcw-config.yaml`, never a folder named
  `.tcw`); `version_line()`, `version_problem(mapping)` (missing, not a version
  written as text, major below 4, newer `(major, minor)` than the running TCW),
  `without_version`; `key_problems` (the naming rule
  `^[a-z0-9]+(-[a-z0-9]+)*$` on every mapping key, list entries included, with a
  `write 'not-tags'` hint); `legacy_message(folder)`. `version_problem` is the
  one check later `tcw-*.yaml` readers call. (TCW-106)
- `tcw validate`: a warning for a 3.x `tcw-config.yaml` left at the root of a
  4.0 project. (TCW-106)
- `tcw/store/fs.py` `refuse_legacy_project`, run first in `tcw.cli._dispatch`
  for every command: a 3.x project is refused, exit 1, naming `tcw migrate`.
  (TCW-106)

## Changed

- The project marker is `.tcw/tcw-config.yaml`; the personal file is
  `.tcw/tcw-config.local.yaml`. `find_project_root` returns the nearest
  folder holding `.tcw/tcw-config.yaml`, and None when the nearest marker is a
  3.x one. Every site that took a configuration file's folder as the project
  root calls `root_of`; `Origin.folder` is the project root for the `project`
  and `local` layers, so `file:` bindings and `TCW_CONFIG_DIR` are unchanged.
  (TCW-106)
- `tcw init` writes `.tcw/tcw-config.yaml` starting with
  `tcw-version: <version>` and the ignore rule `/tcw-config.local.yaml` in
  `.tcw/.gitignore`; `config_edit.plan_id` puts a new `id:` below a leading
  `tcw-version`. No edit adds, removes or changes the version. (TCW-106)
- `tcw.config.load_config`, `tcw.store.fs.load_config` (as `ValueError`) and
  the registry's `_read_config` check `tcw-version`, and `_resolve_override`
  recognises a `TCW_PROJECT_<ID>` that names a 3.x folder; the
  key is removed before layers merge, so `tcw config show` does not print it
  and the personal-file allowlist ignores it. A connected project in the 3.x
  layout, or with an unreadable version, is that connection's problem. The
  version problem has no key path: its message names `tcw-version`. (TCW-106)
- The naming rule is checked on `.tcw/tcw-config.yaml`,
  `.tcw/tcw-config.local.yaml` and the user-wide file. A binding's `when`
  takes `not-tags` (was `not_tags`); `_binding_json` prints `not-tags`.
  Each mistake is reported once: a file whose version cannot be read gets
  only the version problem, a `when` key breaking the naming rule only the
  naming error, and a `TCW_PROJECT_<ID>` naming a 3.x folder only the
  variable's message. (TCW-106)
- The five version fields are `4.0.0`. (TCW-106)
- Help and error text naming the configuration file name
  `.tcw/tcw-config.yaml`. (TCW-106)

## Internal

- `tests/projectfiles.py`: `config_file`, `local_config_file`, `write_config`,
  `write_local_config`, `write_config_file`, which write the `.tcw/` layout with
  the version line in front of a mapping's text; the suite moved to it.
  `tests/test_project_files.py` and `tests/test_project_files_cli.py` cover the
  module and every acceptance criterion. (TCW-106)
- This repository keeps `.tcw/tcw-config.yaml` beside its root
  `tcw-config.yaml` until `tcw migrate` exists (TCW-116);
  `tests/test_repo_config_pair.py` keeps the two the same. `evals/seed_fixture.py`
  reads the fixture's `.tcw/tcw-config.yaml`. (TCW-106)
