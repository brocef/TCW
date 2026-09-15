# Harden tracker binding reads and writes, and Jira response parsing

## What is wanted

The tracker commands should fail with a reported problem, never a traceback, a hang
or a silent wrong answer, when the binding file or Jira's response is not what they
expect — and should tell the user plainly when a binding write gets in the way of
finishing work.

1. **Reading `tracker.yaml`.** The board reads the binding carefully and reports any
   failure on the item. `tracker link`, `unlink`, `import`, `sync <slug>` and strict
   `drop` read it another way: a directory named `tracker.yaml` reads as "unbound"
   (so strict `drop` goes through although the board shows the ticket as unreadable),
   a file that is not UTF-8 prints Python's decoding error, and a named pipe blocks.
   The commands should agree with the board.
2. **Jira responses.** `search`, `issue`, `transitions` and `recent_comments` assume
   parsed JSON has the expected shape; a list where a mapping was expected raises
   `AttributeError`, which escapes the tracker error handling and prints a traceback
   instead of a pending or conflicting result.
3. **Staged writes blocking a merge-back.** Binding and record writes are staged, not
   committed. Git refuses to merge a worktree item back while *any* file is staged,
   so a record on one item can block completing another, and `link`/`unlink` on a
   worktree item give only git's message. The user should be told which staged files
   are in the way.
4. **Linking an item waiting for deletion.** Under `work.retain: false`, `link` binds
   a resolved item whose folder has not been deleted yet; `delete` then refuses until
   that write is committed. Safe, but it should be refused up front.
5. **Dead fields.** `ClaimOutcome.account_id` and `account_name` are set but read only
   by one test since `claimed-by` left `tracker.yaml`.

## Out of scope

- **Decided at triage:** the two tracker-link follow-ups recorded as documented limits
  stay limits — a binding written on a finished item never reaches git, and two
  finished items can hold one ticket and part.

## Notes

- Merged at triage from four review follow-ups, because each is about the binding file
  or the Jira client failing badly; all kept verbatim in `intake.md`.
- Checked at triage on `main`: every part is still present (`read_sidecar` returns
  `None` for anything but a regular file and decodes without catching errors;
  `_json` in `tcw/tracker/jira.py` returns `json.loads(raw)` unchecked; `_complete`'s
  hint looks only at the item's own `tracker.yaml`; `_tracker_link` never calls
  `pending_deletion`).
- Reference material: asked; none provided.

## References

- `unreadable_binding` in `tcw/store/base.py` and `FsWorkStore._read_item` — the
  board's handling, which the entry names as the behaviour to match.
