# Spec: harden tracker binding reads and Jira response parsing

## Capability changes

None to the ledger: refusals replace tracebacks and silent passes.

## Problem

- `FsWorkStore.read_sidecar` returns `None` when the sidecar name exists but is
  not a regular file, which every caller reads as "no file". For
  `tracker.yaml` that means unbound: `link` and `unlink` proceed, and
  `ever_bound` lets strict `drop` through — the opposite of the board, which
  classifies the same file as unreadable (`unreadable_binding`).
- `JiraClient` (`tcw/tracker/jira.py`) trusts every JSON response's shape:
  `_json` returns whatever parsed, and `search`, `issue`, `transitions`,
  `recent_comments`, `description`, `create_issue` and the readers of an
  issue's `fields` (`_fields` in `tcw/tracker/intake.py`, `_current_status` in
  `create.py`) call `.get` on it. A list, or a nested value that is not a
  mapping, raises `AttributeError`/`TypeError`, which no command handles.
- `tcw work tracker link` binds an item that `pending_deletion` says is waiting
  for deletion; `delete` then refuses until the binding is committed.
- `ClaimOutcome.account_id` and `account_name` are set but read only by a test.
- When `complete`'s merge-back fails, the hint checks only the item's own
  `tracker.yaml`, only when it holds a `sync`/`comment` record, and in the store's
  repository rather than the one being merged — though git refuses the merge
  for any staged file in the merging repository's index.

## Goals

1. `read_sidecar` raises `OSError` ("`<name>` is not a regular file") when the
   name exists but is not a regular file; `None` still means absent. The
   abstract docstring says so.
2. `binding_of` turns that and other read errors into `unreadable_binding`, so
   every caller that already refuses a malformed binding (`link`, `unlink`,
   `sync`, progress) refuses this too. `ever_bound` already treats `OSError` as
   bound, so strict `drop` refuses.
3. A Jira response of the wrong shape raises `TrackerError` naming the request
   path, in every operation: the top level in `_json` (a mapping, or empty for an
   empty body), and per operation each list and each entry or nested object read
   downstream (`issues[]` and each issue's `fields`/`status`/`statusCategory`/
   `assignee`, `transitions[]` and each `to`, `comments[]`, `fields` for
   `description`). `null` stays legal wherever the code already treats it as
   absent (an unassigned issue). `_document_text` skips a `content` that is not
   a list.
4. `tracker link` and `tracker create` refuse an item waiting for deletion,
   before any tracker call.
5. `ClaimOutcome.account_id`/`account_name` removed.
6. On a failed merge-back, `complete` lists every staged file in the index of
   the repository being merged (`node_root`) and says git will not merge while
   they are staged; the record-specific `tracker sync` hint stays for the
   item's own record.

## Non-goals

- A binding on a finished, gitignored item; two finished items holding one
  ticket — documented limits, kept.
- The direct re-reads of `tracker.yaml` after `binding_of` has succeeded (they
  fail only if the file changes in between).

## Acceptance criteria

1. A folder named `tracker.yaml`: `link`, `unlink` and `sync <slug>` refuse
   naming the binding as unreadable; strict `drop` refuses; exit 1, no
   traceback.
2. Each `JiraClient` operation, given a response of the wrong shape at each level
   it reads, raises `TrackerError` naming the path; an unassigned issue still
   reads.
3. `tracker link` on an item pending deletion refuses and calls no tracker.
4. A merge-back refused because another item's file is staged names that file.
5. Full suite passes.

## Notes

- Advisors (2026-09-26): both agreed on `read_sidecar` as the place (Opus: "the
  resource exists but cannot be read" is a condition any store has), on
  including the follow-ups, and that the pipe case is outdated. Opus: catch in
  `binding_of` rather than every re-read; the deletion guard in `link`/`create`,
  not the shared `_item_or_reason` that `sync` uses. Codex: nested shapes and the
  operations I had missed; check the repository actually merged. All taken.
