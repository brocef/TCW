# Restructure TCW's skills: setup and configure skills, command and extras skills, and no slash commands

## What is being asked for

This item was split out of
`2026-09-14-consolidate-the-setup-skills-into-a-single-tcw-setup-skill` on
2026-09-14, at the requester's direction, after that item's third review round.
It carries the skill restructure. The requester's decisions are recorded there as
revision notes 1–15 in its `initial-request.md`. In short:

- **Setting up and configuring.**
  - One skill, `tcw-setup`, gets TCW working where it doesn't yet: installing or
    repairing the CLI, a new repository, a new machine, and starting a taxonomy
    or capabilities ledger.
  - One skill, `tcw-configure`, changes a working project's configuration: every
    `tcw-config.yaml` key except `id` and `work.tags`, the `extends` entries, the
    Definition of Done, and `TCW_PROJECT_<ID>`.
  - Both only route to reference documents, and the setup and configuration text
    scattered across other skills moves into them.
- **`tcw-plugin` is removed** and its skill map deleted.
- **The five per-stage skills are deleted**, and `tcw-work-stage` covers every
  stage.
- **Three kinds of skill, told apart by name:**
  - plain `tcw-*` for core skills;
  - `tcw-commands-*` for the core workflow entry points (`plan-work`,
    `drive-work-to-completion`, `verify-work`, `process-inbox`);
  - `tcw-extras-*` for optional ones (`autonomous-work`, `triage-issues`,
    `report`).
- **No slash commands.** `commands/` is removed. A command that only points at an
  existing skill is deleted, after checking the skill covers what it said. A
  command with its own procedure becomes a `tcw-commands-*` skill.
- **Evals are rebuilt:**
  - a configuration case phrased "set up";
  - a setup case on a fresh repository;
  - routing checks on B4 and B8;
  - B5 retargeted, and the axis A cases pointed at `tcw-work-stage`.
- **A large change is acceptable**, because the goal is cleanup.

### Round-three answers (2026-09-14)

- **`skills/tcw-work/references/commands.md:42-43`.** The audit and consolidate
  rows stay as pointers to their procedures, and their old slash-command mentions
  become "ask the `tcw-work` skill".
- **`tcw-work-stage`** becomes a first-class entry point under Codex. Its fallback
  tells the reader to use the stage and item named in the request, and the
  "Claude only" label goes.
- **No fourth review round.** The round-three findings are applied, and review
  stops there.

## Notes

- **Blocked by**
  `2026-09-14-make-eval-checks-measure-what-the-agent-did-working-tree-file-changes-tool-call-routing-and-named-fixture-variants`.
  This item's new eval cases use that item's tool-input predicates and `bare`
  fixture.
- **Blocks** `2026-09-14-consolidate-the-setup-skills-into-a-single-tcw-setup-skill`
  (now "Give every TCW skill a taxonomy Feature and exactly one capability"). That
  item creates a Feature and capability for each skill this item leaves in place.
- **Reference material:** the original item's request, spec, plan and three review
  rounds.

## References

- `2026-09-14-consolidate-the-setup-skills-into-a-single-tcw-setup-skill` — the
  requester's revision notes, and `spec.md`/`plan.md` as of `9fbaa25a`, which this
  item is carved from.
