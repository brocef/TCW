## Fixed

- One item's `state.yaml` that is not valid UTF-8, is a folder, or is a named
  pipe no longer takes down `tcw work list` for every item. `FsWorkStore._safe_yaml`
  checks `is_file()` first and degrades `OSError`, `ValueError` and
  `RecursionError` to `{}` as it already did YAML errors, still raising
  `FileNotFoundError` so a folder moved mid-read is noticed.
- A request or intake text that is not valid UTF-8 no longer takes down the
  board or `show`: `_present` and `_resolve_body` decode with replacement.
- The web app's item detail loads for an item with a damaged `state.yaml` or
  artifact. Every revision is computed losslessly (`_read_revision_text`, and
  `_revision` encodes with `surrogateescape`), so the snapshot's token and the
  guards in `write_artifact`, `write_sidecar` and the plan-stage writes agree,
  and a guarded save can replace a damaged file. No valid file's token changes.
- The detail lists a damaged artifact with its revision instead of dropping it,
  and `GET /api/work/<slug>/artifacts/<name>` refuses one with
  "<name> is not valid UTF-8; fix or replace the file" instead of the decoder's
  byte offset.
- `start` and every transition refuse an item whose `state.yaml` cannot be read
  (`FsWorkStore._require_readable_state`), naming the file, before anything
  moves — the tolerant board read would otherwise let their gates pass on
  defaults and the move fail after it had happened.
