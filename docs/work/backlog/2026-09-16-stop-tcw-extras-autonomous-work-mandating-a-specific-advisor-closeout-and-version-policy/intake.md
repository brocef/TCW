# Stop tcw-extras-autonomous-work mandating a specific advisor, closeout and version policy

Child 3 of the epic
`2026-09-16-make-every-procedural-skill-in-tcw-overridable-by-the-project-that-uses-it`.
Blocked by children 1 (rules and marker) and 2 (the procedure mechanism). Spec
this against what child 2 actually shipped, not against the epic's plan.

## What to deliver

- `skills/tcw-extras-autonomous-work/SKILL.md`'s body stops mandating the items
  the epic spec's Problem §2 lists (re-check the line numbers): the Codex CLI and
  its invocation, the Opus subagent through `Agent`, the "no majority of two"
  adjudication rule, `SendMessage`, "Codex is the reliable half",
  `adversarial-code-reviewer`, the local-merge-never-push closeout, and the
  never-cut-a-version policy.
- The body states what an advisor must be and how many are wanted, naming none.
- Today's text ships as the procedure's `builtin` default, so a project that
  configures nothing gets the same advisors, closeout and version policy.
- `allowed-tools:` and `compatibility:` frontmatter declaring what the default
  needs, as `tcw-setup` and `tcw-extras-triage-issues` do.
- A manual fallback block for a harness that ran no injected commands, modelled
  on `skills/tcw-work-stage/SKILL.md`.
- Ledger: `changed: skills/tcw-extras-autonomous-work`.

## Constraints

- Do not add or change the `SKILL.md` marker key — child 1 owns it.
- Consider `work.trunk-branch` and `work.publish-transitions`
  (`skills/tcw-configure/references/work.md`), which already express the
  closeout the skill hardcodes.

## Acceptance criteria carried from the epic

Epic criteria 8, 9, 10 and 11 for this skill. Verification includes an actual
unattended run against a real backlog item, and a Codex session confirming the
fallback block works.

## What child 2 shipped (added 2026-09-16)

- Procedure ids for this item: `unattended-work`. Read the text with
  `tcw work procedure prompt <id> [slug]`; a project configures it under
  `work.procedures.<id>` as a plain list of bindings.
- Each id's default lives in `tcw/work/procedures/<id>.md`, today a verbatim copy
  of the skill or reference text. `tests/test_shipped_procedures.py` fails when
  a default and its source drift apart: change the default and its `SOURCES`
  row in the same commit that converts the source.
- The command does no harness adaptation, so the converted skill's manual
  fallback block is what a harness without context injection relies on.
- The epic's criterion 8 grep covers the converted skill files only, never
  `tcw/work/procedures/`.

## Origin

Opened by the epic's `implement` stage (plan task 3) on 2026-09-16.
