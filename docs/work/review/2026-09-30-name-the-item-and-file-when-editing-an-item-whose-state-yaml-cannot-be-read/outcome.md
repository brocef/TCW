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
