# Outcome — Stop an item reaching implement without a spec and plan

## What changed

- `STAGE_STATUSES` (`tcw/store/base.py`): `spec` and `plan` are legal in
  `backlog` and `active`. Nothing moves an item back to `backlog`, so this is
  the recovery for an item started too early; `scaffold spec|plan` follows.
- `_unwritten_plan` (`tcw/work/cli.py`): a warning on stderr naming whichever of
  `spec.md`/`plan.md` is missing and the gate command to write it, printed after
  a successful `start` and by the `implement` gate. Neither refuses. The
  reference is printed as the user typed it; a document that cannot be read
  yields no warning rather than an error.
- `STAGE_NEXT_STEPS["plan"]` and the plan prompt's step 7 name the
  already-started case. `tests/fixtures/prompt_fallback/unconfigured.json`
  re-captured (only the `plan` entry moved).
- This repository: `tcw-config.yaml` binds `require_artifact.py spec` and
  `plan` as `pre` on `implement`, so here the gate refuses.
  `tests/fixtures/lifecycle_baseline/self.json` re-captured (only `implement`
  rows moved; the other baseline rows passed first).
- Docs: `skills/work/references/transitions.md`, `CLAUDE.md` stage table,
  `scripts/require_artifact.py` docstring, changelog, release notes.
- Tests: `tests/test_unplanned_start.py` (12); `tests/test_stage_verb.py` table
  and next-step checks updated.

## Verification

- Full suite before the review fixes: 4671 passed, 3 skipped (baseline file
  run separately: 11 passed). Targeted files after the fixes: 63 passed.
- By hand, the report's reproduction in a scratch node: `start` warns and names
  both gate commands; `stage gate implement` warns and passes (no bindings);
  `stage gate spec`/`plan` pass for the active item; `scaffold spec` writes a
  draft; the plan footer names both branches.

## Autonomous decisions

- **start without a plan: warn or refuse?** Codex and Opus: warn, exit 0 —
  `transitions.md` already calls it a check, and small items skip planning on
  purpose. Taken.
- **implement gate** — split. Opus: TCW's built-in gate warns, and this repo
  binds a refusal. Codex: only this repo's binding, checking spec as well as
  plan. Took both parts: the warning is harmless for every project and is what
  the report said was missing (the gate passed silently); Codex's point that the
  binding must check spec too was right and is in.
- **Recovery** — both: make `spec`/`plan` legal in `active` rather than add a
  reverse transition (which would have to undo worktree and tracker state).
  Taken. `request` was not added (Opus raised it): an item always has a request
  of some form and none was reported stuck.
- **Review, accepted**: an unreadable document failing a completed start
  (guarded; test added, fails on the old helper); a qualified reference advised
  with its bare slug (prints what was typed; test added, fails on the old
  helper); the next-step test's conditional branch now requires the condition to
  name the status that needs the transition; `CLAUDE.md`, `require_artifact.py`
  and `transitions.md` wording ("where `tcw work path <slug>` says", since the
  store may live in another repository).
- **Review, separate change**: `FsWorkStore._present` raising on an unreadable
  artifact for every caller is already filed as
  `2026-09-26-keep-one-unreadable-state-yaml-or-artifact-from-breaking-the-board-or-an-item-s-detail`.
- **Rejected**: none.
