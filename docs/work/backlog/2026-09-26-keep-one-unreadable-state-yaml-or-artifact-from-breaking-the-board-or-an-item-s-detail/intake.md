# Keep one unreadable state.yaml or artifact from breaking the board or an item's detail

Found while fixing the same failure for `capabilities.yaml`
(`2026-09-15-make-the-capability-gate-honor-a-configured-ledger`), and raised by
the Opus advisor there.

`FsWorkStore._safe_yaml` (`tcw/store/fs.py`), which reads every item's
`state.yaml` for the board, catches only `yaml.YAMLError`. A `state.yaml` that
is not valid UTF-8, or a folder of that name, raises instead — by the same code
path that made one bad `capabilities.yaml` take down `tcw work list` for every
item (reproduced for that file on 2026-09-26; not yet reproduced for this one).

The web app's `_detail_snapshot` also reads `state.yaml` and each artifact with a
strict UTF-8 `read_text` to compute revisions, so one badly encoded artifact
breaks that item's detail view.

Likely direction: the same as the `capabilities.yaml` fix — `is_file()` first,
catch `OSError`/`ValueError` alongside YAML errors, and let the item still list.
