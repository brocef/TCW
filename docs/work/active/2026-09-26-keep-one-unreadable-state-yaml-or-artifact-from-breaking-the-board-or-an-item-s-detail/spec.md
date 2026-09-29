# Spec — Keep one unreadable state.yaml or artifact from breaking the board or an item's detail

## Capability changes

None. The board, `show` and the web detail already exist; this stops one
damaged file from breaking them.

## Reproduction

In a scratch node (`tcw init work --id r2`) with two items, against the released
CLI (the `main` checkout, `0cc0410c`):

| Damage to item "Bad one"                  | `tcw work list`                                   | `tcw work show <bad>` |
| ----------------------------------------- | ------------------------------------------------- | --------------------- |
| `state.yaml` holds `title: \xff\xfe`      | `tcw: 'utf-8' codec can't decode byte 0xff …`     | same                  |
| `state.yaml` is a folder                  | `IsADirectoryError` traceback                     | same                  |
| `intake.md` holds `# hi \xff`             | `tcw: 'utf-8' codec can't decode byte 0xff …`     | same                  |

In every case the board fails for **every** item, not just the damaged one.
The web app's detail view (`GET /api/work/<slug>`) fails for the damaged item for
the same reason (see Problem 3).

## Problem

1. **`state.yaml`.** `FsWorkStore._safe_yaml` (`tcw/store/fs.py:4864`) catches
   `yaml.YAMLError` only. `load_yaml` (fs.py:1347) reads strictly, so a
   non-UTF-8 file raises `UnicodeDecodeError` and a folder `IsADirectoryError`,
   out of `_read_item` (fs.py:4925) and so out of every `query`. A named pipe at
   that name is found by `_item_dirs` (`rglob("state.yaml")`, fs.py:4190) and
   would block the read forever. The graveyard readers already catch the gap
   themselves (fs.py:5846, 5968).
2. **The request text.** `_present` (fs.py:4635) and `_resolve_body`
   (fs.py:4644) read `initial-request.md` / `intake.md` strictly, and
   `_read_item` calls `_resolve_body` for every item on the board.
3. **The web detail.** `_detail_snapshot` (fs.py:7109) reads `state.yaml`
   (fs.py:7120) and every artifact (fs.py:7129) strictly to compute revisions,
   and `artifacts()` (fs.py:4668) goes through `_present`.
4. **Revision guards disagree with the snapshot.** The snapshot already hashes a
   sidecar with `errors="replace"` (fs.py:7138), but `write_sidecar`'s guard
   (fs.py:7560) re-reads strictly, so a guarded save of a non-UTF-8 sidecar fails
   with the decoder's byte-offset message (422) while an unguarded one succeeds.
   `write_artifact` (fs.py:7457) and the plan-stage guards (fs.py:4789, 4815,
   4828) have the same strict read.

**Sibling sweep, repo-wide** (`grep -n 'read_text(encoding="utf-8")' tcw/`): the
readers above are the ones on the board, `show` and web-detail paths. The
editor-facing resource reads (`read_artifact`, `read_sidecar`,
`read_plan_stage`) are strict by design and the web maps a decode failure to a
named 400 for sidecars; `read_artifact` raises `UnicodeDecodeError`, which the
detail endpoint (`tcw/serve/__init__.py:799`) swallows as `ValueError` and so
drops that artifact from the list. The write paths that read `state.yaml`
before writing it (`update_work` fs.py:7274 and the transitions) use strict
`load_yaml` and refuse, which is correct and stays. Taxonomy and capability
stores are out of this sweep's scope (a different item's board).

## Goals

1. One item's `state.yaml` that is not valid UTF-8, is a folder, or is a named
   pipe does not stop `tcw work list` listing every other item; the damaged item
   lists with its folder name as title, as a YAML syntax error already does.
2. One item's request or intake text that is not valid UTF-8 does not stop the
   board; the item lists, and `tcw work show` shows the text with replacement
   characters.
3. The web detail of such an item loads (200).
4. A revision-guarded save may replace a file that is not valid UTF-8: every
   revision — snapshot and guard alike — is computed losslessly from the file's
   bytes, so the two agree and a stale revision is still refused.

## Non-goals

- Making the editor-facing resource reads tolerant. A non-UTF-8 artifact or
  sidecar is still refused by the endpoint that returns its content to an editor;
  the fix is a guarded or unguarded save, or a hand edit.
- Reporting the damage on the board. `tcw validate` already reports a file in
  the store that is not valid UTF-8 or not a regular file
  (`tests/test_unreadable_capabilities_sidecar.py:190-205`).
- Any write that could replace damaged `state.yaml` with a degraded `{}`: every
  read-modify-write keeps strict `load_yaml` and refuses.
- A child whose `state.yaml` is unreadable loses its `parent:` field and falls
  back to folder nesting, so its parent's completion gate may not see it (raised
  by the Opus advisor). This is true today for a YAML syntax error too; it is a
  gate question, recorded as a follow-up, not fixed here.
- Taxonomy and capability stores.

## Design

- `_safe_yaml(path)`: `{}` when `path` is not a regular file (checked first, so
  a pipe is never opened); `load_yaml` otherwise, with `OSError` (except
  `FileNotFoundError`, which callers use to detect a folder moved mid-read),
  `UnicodeDecodeError`, `yaml.YAMLError` and `RecursionError` all degrading to
  `{}`. The docstring states it is for reads only and never feeds a write.
- `_present` and `_resolve_body` decode with `errors="replace"`: display only.
- One module-level `_read_revision_text(path)` —
  `path.read_text(encoding="utf-8", errors="surrogateescape")` — and `_revision`
  encodes with `errors="surrogateescape"`. For a valid UTF-8 file both are
  byte-identical to today, so no existing token changes; for an invalid one the
  token is stable and distinct per byte sequence. `read_text` keeps its newline
  normalization, so a CRLF file's token is also unchanged.
- Every revision computation over a file on disk uses it: `_detail_snapshot`'s
  state, body and artifacts and sidecars; the guards in `write_artifact`,
  `write_sidecar`, `write_plan_stage`, `delete_plan_stage`; the plan-stage list.
  The core revision's body goes through it too (not the replacement-decoded
  display text), so two different damaged bodies never share a token.
- `_detail_snapshot` hashes a `state.yaml` that is not a regular file as `""`.
- Writes keep encoding strictly (`_atomic_write_many`), so submitted content with
  a lone surrogate is still refused before any revision is computed.

## Abstraction litmus test

No new store-interface operation. "One item's damage does not take down a
query" and "a revision identifies the current content" are already the store's
contract; how bytes on disk are decoded and hashed is private to the filesystem
adapter.

## Acceptance criteria

1. For each of `state.yaml` not valid UTF-8, a folder, and a named pipe:
   `tcw work list` (in a child process with a timeout) exits 0 and lists both
   items, and does not print `codec can't decode` or `Traceback`.
2. With `intake.md` not valid UTF-8 (and again with `initial-request.md`),
   `tcw work list` exits 0 listing both items and `tcw work show <bad>` exits 0.
3. With `state.yaml` not valid UTF-8, and separately with `spec.md` not valid
   UTF-8, `GET /api/work/<slug>` answers 200.
4. With `spec.md` not valid UTF-8: a web `PUT` of that artifact carrying the
   revision from the detail payload succeeds and the file then holds the new
   text; one carrying any other revision is refused as stale (409). The same for
   `capabilities.yaml` through the sidecar endpoint.
5. For a valid UTF-8 file with CRLF line endings, the revision in the detail
   payload equals the one `_revision` gives its `read_text()` today.
6. A folder moved mid-read is still skipped: `_safe_yaml` raises
   `FileNotFoundError` for a path whose folder is gone.
7. The full test suite passes.

## Risks

- Changing `_revision`'s encoding is shared with taxonomy and capability
  revisions; for any string without lone surrogates the output is identical, and
  those stores read files strictly, so nothing there can change.
- A tolerant `_safe_yaml` hides damage from the board; `tcw validate` is where it
  is reported (non-goal above).

## Notes

- Advisors, 2026-09-29: Codex and an Opus subagent both chose that a guarded
  save may replace a non-UTF-8 file (option 1), on the ground that only then do
  the snapshot's token and the guard's agree. Codex raised newline normalization
  (hence `read_text` + `surrogateescape`, not `read_bytes`) and the body's
  lossless hashing; Opus raised the `FileNotFoundError` re-raise and the
  lost-`parent:` hazard (a non-goal, filed as a follow-up).
