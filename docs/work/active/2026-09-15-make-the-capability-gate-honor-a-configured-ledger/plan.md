# Plan: keep one bad capabilities.yaml from breaking the board

## Tasks

1. **Tests first** in `tests/test_unreadable_capabilities_sidecar.py`: criteria
   1-6 (the pipe and the anchor file each under a time limit; the web detail
   through the serve test client).
2. **Helper** in `tcw/store/base.py`: `sidecar_value_problem(value)` — the
   iterative, cycle-safe count against 10,000 — and the byte limit constant.
3. **Read** in `FsWorkStore._read_item`: `is_file()` first, then the size, the
   read and parse under one `except`, then the count; a vanished file stays
   `None`.
4. **Web reads** in `_detail_snapshot` and `read_sidecar`.

## Documentation Sync

- Changelog and release notes (a fix).
- No guide or skill describes what happens to an unreadable sidecar; checked
  `docs/guide/work.md` and `skills/capabilities/SKILL.md`.

## Verification

Hands-on: a scratch node with each bad file from the spec; run the worktree's
`tcw work list`, `show --json` and `complete`, and `tcw serve` with curl on the
item's detail.
