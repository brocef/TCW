# Compose a procedure's instructions from project bindings the way a stage's are composed

Child 2 of the epic
`2026-09-16-make-every-procedural-skill-in-tcw-overridable-by-the-project-that-uses-it`.
Read that epic's `spec.md` (Problem §1, Design → "Where the mechanism goes") and
`plan.md` (task 2) before specifying. Line citations below are from the epic's
spec and must be re-checked against the current tree.

## What to deliver

- `PROCEDURE_IDS` beside `STAGE_IDS` (`tcw/store/base.py`, around `:932`).
- `tcw/work/procedures/<id>.md` beside `tcw/work/prompts/`, loaded by
  `load_builtins()` (`tcw/work/resolve.py:48-86`) with the same missing-file and
  empty-file refusals. Each file's content is today's text of the procedure; the
  conversion children supply or confirm those texts.
- `work.procedures` as a **sibling** of `work.lifecycle`, not inside it, added to
  the validated key set the way `tcw/store/base.py:2267` does for lifecycle.
- A `procedure()` accessor on `LifecyclePolicy` (`tcw/store/base.py:1560-1590`)
  returning `[]` by default.
- Resolution through the existing `_resolve_one`
  (`tcw/work/resolve.py:188-209`) and the `or [Binding(kind="builtin")]` floor
  (`:445`). No second binding grammar: `Binding`, its kinds and `when:` are
  reused. Bindings are read, never executed.
- A read-only CLI verb serving it (the epic names
  `tcw work procedure prompt <id>` provisionally), whose output adapts to the
  harness using the detection `tcw work stage validate` already has.
- `tcw validate` reports an unknown procedure id, a malformed binding shape, a
  blank or duplicated reference, and a kind used where it is not allowed.
- `skills/tcw-configure/references/work.md` documents the new key;
  `skills/tcw-work/SKILL.md` and `references/commands.md` name the verb. The
  `tcw-work` skill has a 60-line budget
  (`tests/test_skill_lifecycle_parity.py`) — extract rather than grow.

## Constraints

- A project that configures nothing behaves exactly as today.
- Abstraction litmus test (`docs/lifecycle/abstraction.md`): procedure bindings
  are node configuration, not a store operation.
- This child changes `tcw/`. While it is active, this repository's `CLAUDE.md`
  forbids driving the lifecycle with the `tcw` CLI from the modified tree —
  maintain `docs/work/` by hand and say so in the outcome.
- The epic reserves the ledger deltas `added: work/run-a-procedure`,
  `work/configure-procedures` and `changed: work/configure-the-work-lifecycle`.

## Acceptance criteria carried from the epic

Epic criteria 4, 5, 6 and 7.

## Origin

Opened by the epic's `implement` stage (plan task 2) on 2026-09-16.
