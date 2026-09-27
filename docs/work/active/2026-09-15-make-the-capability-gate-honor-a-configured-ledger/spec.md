# Spec: keep one bad capabilities.yaml from breaking the board

## Capability changes

None to the ledger: reads that crashed now report.

## Problem

Part 1 of the request is already fixed (`61a298b9`); nothing here changes it.

`FsWorkStore._read_item` (`tcw/store/fs.py`) reads every item's
`capabilities.yaml` whenever the name `exists()`, with
`yaml.safe_load(caps.read_text(encoding="utf-8"))`, and catches only
`yaml.YAMLError`. Reproduced on main 2026-09-26:

- a file that is not valid UTF-8 → `tcw work list` prints
  `'utf-8' codec can't decode…`, exit 1, no rows;
- a folder named `capabilities.yaml` → `IsADirectoryError` traceback;
- a named pipe of that name would block the read forever (not reproduced; no
  exception can catch it);
- a 10-line file of nested anchors (`a1: &a1 [*a0, *a0, …]` nine levels deep,
  10⁹ values once expanded) → `tcw work show --json` still running after 15 s,
  because the projection's `_json_safe` walks every expanded value.

The web app also reads the file itself: `_detail_snapshot` hashes each sidecar's
text for its revision and `read_sidecar` returns it, both with a strict UTF-8
read, so the same file breaks that item's detail view.

## Goals

1. A `capabilities.yaml` that cannot be read — not a regular file, not UTF-8,
   unreadable, larger than 1 MB, a YAML error, nesting deep enough for
   `RecursionError`, more than 10,000 values once aliases are expanded, or
   nesting deeper than 100 through aliases —
   becomes the existing parse-error value `{"_tcw_parse_error": <reason>}`.
   The board and `show` still list the item; `declared_capabilities` turns the
   value into `SidecarError`, so the completion gate refuses the item (fails
   closed), exactly as a YAML error does today.
2. A missing file is still "no sidecar", including one that disappears between
   the check and the read.
3. The size and expansion limits are a storage-neutral helper in
   `tcw/store/base.py`, beside `declared_capabilities`, so any store can apply
   them; the walk is iterative, counts every alias occurrence, and stops at a
   container that contains itself.
4. The web app's detail view of such an item still loads: the sidecar's revision
   is computed from a tolerant read, and reading the sidecar as an editable
   resource refuses with a message naming the file instead of raising.

## Non-goals

- `state.yaml` has the same weakness (`_safe_yaml` catches only YAML errors) —
  filed separately.
- Showing the problem on the board or in the web app. It is visible in
  `show --json`, in the completion gate's "capabilities.yaml is unreadable: …",
  and — once `2026-09-09-resolve-capabilities-yaml-sidecar-paths-while-an-item-is-still-being-worked`
  is merged — in `tcw validate` for every unfinished item.
- YAML merge keys (`<<:`) are expanded while loading, before any walk. Their
  growth is additive (a merge copies keys, which cannot repeat), so they cannot
  reach the exponential case; the 1 MB limit bounds them.

## Acceptance criteria

1. Non-UTF-8 file, a folder, and a named pipe named `capabilities.yaml`: `tcw
   work list` exits 0 and lists every item; `show --json` shows
   `_tcw_parse_error` for that item; the pipe case returns promptly.
2. The anchor file from the problem: `show --json` returns within a few seconds
   with `_tcw_parse_error` naming the limit.
3. A self-referencing sidecar (`a: &x {b: *x}`) does not hang or crash the count.
4. A sound mapping sidecar and reconcile's list form read exactly as before;
   a sidecar with repeated aliases under the limit is accepted.
5. `tcw work complete` refuses an item whose sidecar is unreadable, naming the
   file.
6. The web detail of an item with a non-UTF-8 sidecar loads (200); reading that
   sidecar is refused with a message, not a 500.
7. Full suite passes.

## Risks

- A legitimate sidecar over 10,000 values or 1 MB is refused. Real ones hold a
  few dozen paths.

## Notes

- Advisors (2026-09-26): both agreed the read is the place and the limit is
  sound, and warned against refusing aliases outright (PyYAML writes `&id001`
  anchors itself). Opus: missing-file handling, `is_file()` first, cycle-safe
  count, helper in `base.py`. Codex: the web app's raw reads, a byte limit,
  non-regular files, merge keys. All taken; see `outcome.md`.
