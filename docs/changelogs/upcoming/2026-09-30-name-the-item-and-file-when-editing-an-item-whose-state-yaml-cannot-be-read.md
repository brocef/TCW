## Fixed

- Editing an item whose `state.yaml` cannot be parsed now refuses with the item,
  the file's path and a pointer to `tcw validate`, instead of the bare parser
  message. `_set_fields_at` and `update_work` call `_require_readable_state`
  (now an instance method, and naming the path) before their strict read.
- YAML syntax errors from `load_yaml`, the project config reader
  (`tcw/store/project.py`) and `tcw validate`'s scan name the file instead of
  `"<unicode string>"`, keeping PyYAML's line excerpt: new
  `tcw/store/yaml_source.load` names the loader built from the text.
  Other direct `yaml.safe_load` calls are unchanged.
- The same naming for `tcw init`'s config read, `dod.yaml`, an item's
  `capabilities.yaml` (read and write) and `config_edit.edit_text`. Reads that
  swallow their errors, and tracker binding text (whose error shows no parser
  text), are unchanged.
