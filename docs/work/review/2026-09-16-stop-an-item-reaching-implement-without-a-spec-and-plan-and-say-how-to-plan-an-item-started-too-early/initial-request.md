# Stop an item reaching implement without a spec and plan, and say how to plan an item started too early

## Request

`intake.md` is the report. An item started with no `spec.md` or `plan.md` hits a
dead end: `tcw work stage gate spec|plan` refuse because the item is `active`
and no verb moves it back, while `stage gate implement` passes with nothing
written and `start` says nothing about it. Fix all three: warn at `start`, stop
the `implement` gate passing silently (and refuse it in this repository), and
give an item started too early a way to be specified and planned.

## Taken without a human (unattended run, 2026-09-27)

Both advisors (Codex, an Opus subagent) agreed on: a warning at `start`, not a
refusal; making `spec` and `plan` legal in `active` rather than adding a
reverse transition. They split on the `implement` gate: Opus wanted TCW's
built-in gate to warn and this repo to refuse; Codex wanted only this repo's
refusal, checking spec as well as plan. Both are taken: the warning is TCW's
default for every project, the refusal is this repository's own policy.
