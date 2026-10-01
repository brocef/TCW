# Outcome: Name the item and file when editing an item whose state.yaml cannot be read

## What shipped

- **Code and tests** — `109ea5be`: `_require_readable_state` is an instance
  method naming the file's path and `tcw validate`; `_set_fields_at` and
  `update_work` call it before their strict read;
  `tests/test_damaged_state_on_edit.py`.
- **Keep the parser's excerpt** — `0e5ef323`: `tcw/store/yaml_source.load`
  names the loader built from the text, used by `load_yaml`, the project config
  reader (`tcw/store/project.py`) and `tcw validate`'s scan.
- **Docstring correction** — in `325fb1bd`: the loader does not name the file
  for every error (see below).
- **Docs** — `4b2d2c87` (changelog, release notes).

## Test result

- Full suite under bare `pytest` at `d6e98814`: 1 failed, 5219 passed, 3
  skipped; the one failure belongs to the detached-worktree item.
- `tests/test_damaged_state_on_edit.py`: 8 passed; the two excerpt tests fail
  against the first (named-stream) version.

## What the plan or spec got wrong

- **Handing PyYAML a named stream drops its line excerpt and caret.** The spec
  review found it; the loader-name approach keeps both.
- **Goal 3 promised every YAML error would name its file**; the design covered
  three reads. Narrowed in the spec amendment.
- **Two errors still name no file**, found by the code review: a character YAML
  forbids (raised while the loader is built, before it has a name) and a
  duplicate key (no position at all).
- A test assumed the error pointed at line 1 of a broken config; PyYAML points at
  line 2. The test was corrected, not the code.

## Notes

- About twenty direct `yaml.safe_load` calls outside `load_yaml` still report
  `"<unicode string>"`; proposed as a follow-up.

## Folded in at verify

- `d4fbdc38`: `tcw init`'s config read, `dod.yaml`, an item's
  `capabilities.yaml` (read and write) and `config_edit.edit_text` name their
  file. The other direct `yaml.safe_load` calls either swallow errors (so show
  nothing), parse text that is not a file, or feed the tracker binding, whose
  message never includes the parser's text. The follow-up in Notes is done.
- Tests: `tests/test_damaged_state_on_edit.py` 13 passed; the files touching
  those sites — 3321 passed, 3 skipped.

## Folded in at verify (second round)

- `d61a543f`: a `capabilities.yaml` read error names the file from the project
  root (`docs/work/<status>/<slug>/capabilities.yaml`) rather than the bare
  file name, so it says which item's file it is. `_read_capabilities_sidecar`
  became an instance method to reach `_shown_path`.
- The comment at `tcw/cli.py` naming `yaml_source.named` now names `load`.
- The changelog entry no longer says the other `yaml.safe_load` calls are
  unchanged in the bullet before the one that changes several of them.
- Tests: `test_a_capabilities_file_names_itself` asserts the full path (fails
  with the fix removed); `tests/test_unreadable_capabilities_sidecar.py`'s exact
  message updated.
