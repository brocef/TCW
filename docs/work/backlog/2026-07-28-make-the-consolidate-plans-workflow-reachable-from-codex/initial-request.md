# Make the consolidate-plans workflow reachable from Codex

## Origin

Split out of
`2026-07-28-audit-the-work-backlog-with-subagents-and-make-the-workflow-reachable-from-codex`,
which found and fixed the identical defect for the **backlog audit** workflow.
That item deliberately fixed only its own workflow; this is the other half.

## Problem

`consolidate-plans` is an AI-driven workflow with no CLI verb behind it, and it
is reachable only as a Claude slash command:

- `.codex-plugin/plugin.json` exposes `"skills": "./skills/"` and **no `commands`
  key**, so Codex never sees `commands/`.
- The whole procedure lives in `commands/tcw-consolidate-plans.md`.
- The docs used to paper over this by describing `tcw work consolidate-plans
  [PATH …] [--apply] [--delete]` as if it were a CLI subcommand. It never was —
  `tcw work` has no such verb. Those lines are now corrected, so the gap is
  stated honestly rather than hidden, but it is still a gap: a Codex user cannot
  run this workflow.

This violates the AGENTS.md rule that a task a Claude user can accomplish, a
Codex user must also be able to accomplish.

## Product changes

Codex users gain access to plan consolidation. No `tcw` CLI surface change.

Check at spec time whether a `work/consolidate-plans` capability entry exists and
whether its body claims the fictional CLI verb — the sibling item found exactly
that on `work/audit-work-backlog` and had to rewrite it.

## Technical changes

Apply the pattern the sibling item established, which is already proven:

1. Move the procedure from `commands/tcw-consolidate-plans.md` into
   `skills/tcw-work/references/consolidate-plans.md`.
2. Reach it from a gate line in the `tcw-work` router's "Read on demand" list.
3. Reduce `commands/tcw-consolidate-plans.md` to frontmatter plus a pointer —
   **not** deleted, or the `/tcw-consolidate-plans` slash command disappears and
   the Claude UX regresses for no gain.
4. Update `skills/tcw-work/references/commands.md`'s "Not CLI subcommands" table,
   which currently says this workflow is "Claude only, not yet reachable from
   Codex", and the matching paragraph in `README.md`.

Consider while in there: does this workflow also benefit from the per-item
subagent fan-out the audit workflow gained? Migrating many plan documents is
per-document work with the same shape. Decide deliberately — it may not be worth
it, but it should not be missed by default.

## Meta changes

Litmus test: not applicable — nothing here touches the store interface. This is
plugin packaging and skill prose.

`tests/test_documented_cli_surface.py` already guards the class of defect that
produced this item; no new test is expected.
