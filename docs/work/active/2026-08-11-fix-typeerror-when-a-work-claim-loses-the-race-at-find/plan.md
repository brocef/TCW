# Plan — Fix TypeError when a work claim loses the race at _find

## Task 1 — Write the failing test first

**Changes:** `tests/test_external_work_store.py`.

Monkeypatch `FsWorkStore._find` to return `None` for the target slug while the
item is genuinely active under another owner, then assert `start()` raises
`AlreadyClaimed`.

**Verify:** the test fails against unfixed `fs.py` with `TypeError`, and the
message names `NoneType`. A test that passes before the fix proves nothing here,
because the bug already passes most of the time.

## Task 2 — Normalize the lost-race signals

**Changes:** `tcw/store/fs.py`, inside `start()`.

Three lines plus a comment, per spec §Design.

**Verify:** Task 1's test passes; `pytest tests/test_external_work_store.py`
green; full suite green.

## Documentation Sync

Evaluated against `CLAUDE.md` §Documentation Sync:

- `README.md` **[Public-API]** — does not fire. No CLI surface, flag, or
  user-facing behavior change; an internal error becomes the correct already-
  documented error.
- `docs/release-notes/upcoming.md` **[Public-API]** — **fires, marginally.** A
  user racing two agents saw a crash and now sees the intended message. One line
  under a Fixed heading.
- `docs/changelogs/upcoming.md` **[Any-Code-Change]** — **fires.** Behavior
  change in `fs.py`.
- `skills/<component>/SKILL.md` **[Skill-Driven-Component]** — does not fire.
  `tcw-work` drives this component, but nothing about its CLI surface, model,
  lifecycle, or guardrails changes; `AlreadyClaimed` is already what the skill
  describes.

### Task 3 — Write the two doc entries

After Tasks 1-2, in one pass.

## Verification

The suite covers criteria 1-3. Criterion 4's CI half needs a push; the flake
means a single green run is weak evidence, so the deterministic test is what
actually demonstrates the fix.

## Notes

- Test-first is not ceremony here: the failure is intermittent, so writing the
  test afterwards risks writing one that passes for the wrong reason.
