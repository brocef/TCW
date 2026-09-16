# Compose the five tcw-work procedure documents from project bindings

Child 4 of `2026-09-16-make-every-procedural-skill-in-tcw-overridable-by-the-project-that-uses-it`.
The brief in `intake.md` is the requester's position; this request adds only
what was decided since.

## What is wanted

A project can replace the text of `audit-backlog.md`, `consolidate-plans.md`,
`decompose.md`, `delegation.md` and `search.md` under
`skills/tcw-work/references/procedures/`, through the procedure ids of the same
names, with today's text as the default. `agents/tcw-backlog-auditor.md` stops
carrying its own copy of `audit-backlog.md`'s checks, so a project's replacement
is not skipped when that agent is dispatched. Write `delegation.md` first.

These are reference documents an agent opens with a file read, not skills, so
context injection does not run in them; how a reader of one reaches the
resolved text is for `spec` to decide.

## Already decided for every conversion child (2026-09-16)

- Children 1 and 2 are merged on `main`. The verdicts are in
  `skills/README.md`; the mechanism is `tcw work procedure prompt <id> [slug]`
  with `work.procedures` configuration, defaults in `tcw/work/procedures/<id>.md`,
  and the drift test `tests/test_shipped_procedures.py`. Spec against that code,
  not against the epic plan.
- A project that configures nothing must get exactly today's text. The proof the
  requester wants in the outcome is a diff of the resolved text against the
  pre-conversion source.
- **Live checks are deferred to verify.** A real session exercising the
  converted skill, and a Codex session confirming the manual fallback block,
  are not run by the implementer. The outcome lists them as not done, and the
  requester decides at verify.
- Do not change the `dynamic_skill` key or `skills/README.md` verdicts.

## Notes

- Reference material: asked on 2026-09-16; none provided beyond the brief.
- The item was started into its worktree before `spec` and `plan`, by the
  requester's choice to do all planning in worktrees; the `spec` and `plan` gates
  therefore refuse on status, as they did for children 1 and 2.
