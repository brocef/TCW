## Added

- `tcw/config.py`: the layered configuration loader (TCW-72).
  `load_config(root, *, personal=True)` merges the built-in layer,
  `tcw-config.yaml`, the user-wide file and `tcw-config.local.yaml`, and
  records each value's origin (`Origin(layer, file)`), what personal files set
  that was refused or skipped, and every problem as `Problem(file, key_path,
  message)`. `PERSONAL_KEYS` is the allowlist of what a personal file may set.
  `effective(root)` keeps the acting project's result for the rest of a
  command.
- `tcw.errors.ConfigError` (exit 1), raised for any configuration problem.
- `tcw config show [--origin]` (`tcw/config_cli.py`).
- `tcw work list --mine`, and `--assign-me` on `tcw work new` and
  `tcw work edit`, through the backend's `current_user()`.
- `TCW_CONFIG_DIR` in the environment of every `command` and `generate`
  binding, naming the declaring file's folder.
- `Outcome.post_failures` and `tcw.work.hooks.HookFailure`: a failed `post`
  hook carries its binding and the file that declared it.
- `tcw init` writes `/tcw-config.local.yaml` to `.gitignore` inside a
  repository; `tcw validate` warns when that file is tracked
  (`tcw.store.fs.personal_file_tracked`, read only).
- Tests under `tests/config/`; an autouse fixture in `tests/conftest.py` sets
  `TCW_NO_PERSONAL_CONFIG=1` and points `XDG_CONFIG_HOME` into each test's
  temporary folder.

## Changed

- Every command checks the whole configuration before it runs (in
  `tcw.cli._dispatch`), except `init`, `provision`, `validate` and
  `config show`. `open_backend` builds the acting project's backend from the
  merged configuration; another project's backend ignores personal files.
- TCW's own prompt and procedure text comes only from the built-in layer's
  `{builtin: true}` entries. The fallbacks in `tcw/work/resolve.py` and
  `tcw work lifecycle` are gone, so an empty list really is empty.
- A chain list's `inherit: true` entry replaces `builtin: true` in files;
  `builtin:` written in a file is an error.
- Configuration key paths carry list indexes as integers and print as
  `work.stages.spec.prompt[2]`.
- A `file:` binding is read relative to its declaring file's folder and may not
  leave it; this is checked when the configuration loads.
- `tcw validate` reports configuration problems from every layer first, once
  each; the work checks no longer repeat them.
- The duplicate-key YAML loader exists once, in `tcw/store/yaml_source.py`.

## Removed

- `builtin: true` written in `tcw-config.yaml`.
- The last mention of `TCW_WORK_OWNER` (a docstring in
  `tcw/store/project.py`); no identity is read from it or from version control
  settings.
