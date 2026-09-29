# Plan — Keep one unreadable state.yaml or artifact from breaking the board or an item's detail

Worked in a `--worktree` branch started from the `bug-run` integration worktree,
tested with the private virtual environment re-pointed at the item's worktree.

## Tasks

1. **Failing tests** — new `tests/test_unreadable_item_files.py`, reusing the
   shape of `tests/test_unreadable_capabilities_sidecar.py` (a two-item node
   fixture; `board()` and `show()` in a child process with a 20 s timeout; a
   `served()` helper around `TcwServer`). Every fixture argument the readers
   branch on (which file, which damage) is an explicit parameter.
   - AC1: `state.yaml` × {not UTF-8, folder, pipe} → board lists both, no
     traceback, no decoder message.
   - AC2: {`intake.md`, `initial-request.md`} not UTF-8 → board and `show` exit 0.
   - AC3: web detail 200 for bad `state.yaml` and for bad `spec.md`.
   - AC4: guarded `PUT` of bad `spec.md` and bad `capabilities.yaml` with the
     detail's revision succeeds and replaces the file; with another revision → 409.
   - AC5: a CRLF `spec.md`'s detail revision equals `_revision(p.read_text())`.
   - AC6: `_safe_yaml` on a path whose folder was removed raises
     `FileNotFoundError`.
   Proof: AC1–AC4 red on the current tree for the reported reason (decoder
   message / `IsADirectoryError` / timeout / 500 / 422); AC5 and AC6 pass today
   and are mutation-checked after task 2 (break the newline handling / swallow
   `FileNotFoundError` → red).
2. **Readers and revisions** — `tcw/store/fs.py`:
   - `_revision` encodes with `errors="surrogateescape"`; new module-level
     `_read_revision_text(path)`.
   - `_safe_yaml` as the spec's Design.
   - `_present` / `_resolve_body` decode with `errors="replace"`.
   - `_detail_snapshot`: state (non-file → `""`), body, artifacts, sidecars via
     `_read_revision_text`; the core revision's body read losslessly (the body
     file re-read through `_read_revision_text`, not the display text).
   - Guards in `write_artifact`, `write_sidecar`, `write_plan_stage`,
     `delete_plan_stage` and the plan-stage list via `_read_revision_text`.
   Proof: task 1 green; `tests/test_unreadable_capabilities_sidecar.py`,
   `tests/test_serve*.py`, `tests/test_work*.py` green.
3. **Full suite** — `pytest -q -n 8` from the item worktree.

## Documentation Sync

- `docs/changelogs/upcoming/<slug>.md` — fires (Any-Code-Change).
- `docs/release-notes/upcoming/<slug>.md` — fires (Public-API: user-facing
  behavior — the board no longer fails; a web save can replace a damaged file).
- `README.md`, `docs/guide/*`, `skills/work/*` — evaluate: fire only where a
  document says a damaged file breaks the board or that a guarded save refuses
  one (`grep -rn "UTF-8\|unreadable" README.md docs/guide skills/work`).
- `skills/configure/references/*` — does not fire.

## Verification

Re-run the three-row reproduction in a scratch node with the worktree's CLI
and confirm every row lists both items; start `tcw serve` against it and load
the damaged item's detail.

## Follow-up to file

A child whose `state.yaml` is unreadable loses `parent:` and may be missed by
its parent's completion gate — filed as a backlog item at implement.
