# Plan — Say where a dated amendment to an item's request belongs

Documentation only; no code changes. Worked on `main` without a worktree,
because nothing under `tcw/` that runs is edited. The prompt and procedure
files are text the CLI prints.

## Task 1 — The rule, in the work skill and the guide

**Modifies** `skills/work/references/commands.md` (a new "Amending a request"
paragraph after "The body surface") and `docs/guide/work.md` (the same,
after "Editing a body, and how it promotes an intake"). The paragraph covers:

- append to `initial-request.md` under `## Added <YYYY-MM-DD>` naming the
  source, and never rewrite what is there;
- an intake-only item gets its request written first (the `request` stage),
  and the intake is not touched;
- with a spec or plan, the amendment must reach them: in backlog or active,
  revise them or say why not; in review, `rework.md`, then `tcw work rework`;
- a bound ticket's description is not updated.

**Proves** criterion 2 (in part).

## Task 2 — The procedure, the stage prompt, the skill

- `tcw/work/procedures/create-work.md`: the append bullet sends item
  amendments to the rule, drops "otherwise `intake.md`", and keeps the
  inbox-entry clause. **Proves** criteria 1 and 2.
- `tcw/work/prompts/request.md` and its mirror
  `skills/work/references/lifecycle/stage-request.md` (only if the mirror
  carries the Produce text; it is a summary, so probably not): "if
  `initial-request.md` already exists, keep its `## Added` sections".
  **Proves** criterion 4.
- `skills/work/SKILL.md`: one sentence naming the file. **Proves**
  criterion 3.

## Task 3 — Documentation Sync

- `docs/capabilities/work/capture-raw-intake/description.md` and the item's
  `capabilities.yaml` (`changed:`).
- `docs/changelogs/upcoming/<slug>.md` [Any-Code-Change: the shipped
  procedure and prompt text changes]; `docs/release-notes/upcoming/<slug>.md`
  [Public-API: what an agent is told changes].
- README, jira guide, configure references: not triggered. No CLI surface,
  tracker behavior or configuration key changes.

## Task 4 — Checks

`tcw validate`, `tcw capabilities check`, the doc-surface tests (`-k "doc or
skill or prompt or procedure or capabilit"`), then the full suite, bare
`pytest`. **Proves** criterion 5.

## Verification

Read the three copies of the rule side by side, and confirm they say the same
four things.
