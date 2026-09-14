# Upcoming

Developer changelog for the next version. Technical and precise; grouped by
category.

## Added

- **`tcw-setup` skill** (`skills/tcw-setup/`): a router over `install.md` (the
  install and repair text from `tcw-plugin`), `project.md` (new: `tcw init`,
  per-component `init`, `tcw provision`, `tcw validate`, hand-off to
  `tcw-configure`), `taxonomy.md` and `capabilities.md` (moved from the axis
  skills' `references/init.md`). Its routing table sends "set up" requests for
  configuration areas to `tcw-configure`.
- **`tcw-configure` skill** (`skills/tcw-configure/`): a router over `work.md`
  (declaring `work.lifecycle` bindings, moved from `tcw-work`'s `hooks.md`; new
  text for `work.lifecycle.artifacts`, `work.lifecycle.timeout`,
  `work.lifecycle.output-cap`, `dod.yaml`,
  `work.auto-commit-transitions`, `work.trunk-branch`, `work.publish-transitions`
  and `work.retain`), `docs-sync.md` (moved from `documentation-sync`'s
  `references/setup.md`), `tracker.md`, `stores.md` and `projects.md` (moved from
  `tcw-work`'s `commands.md` and the axis skills, with new text for store paths,
  the `connected-projects` shape and where `extends` is stored).
- **Four command skills**, moved from `commands/`: `tcw-commands-plan-work`,
  `tcw-commands-drive-work-to-completion`, `tcw-commands-verify-work`,
  `tcw-commands-process-inbox`. Paths into `tcw-work` are named in words, and
  `$ARGUMENTS` is gone.
- **Eval cases B11 and B12.** B11 ("set up documentation tracking", existing
  fixture) must open `tcw-configure`'s `docs-sync.md`, open no `tcw-setup`
  document, change only `tcw-config.yaml` and validate. B12 (`fixture: bare`)
  must open `tcw-setup`'s `project.md` and no `tcw-configure` document; it runs
  only with `--out` outside this checkout. B4 and B8 gain `tool_input_absent`
  `tcw-setup/references/`. `PARTIAL` gains `tcw-setup`, `tcw-configure` and
  `tcw-work-stage` (the `request` route); `EXCLUSIONS` lists the four command
  skills.
- **`Configuration-Key-Change` documentation entry** in `tcw-config.yaml` for
  `skills/tcw-configure/references/<document>.md`; `Skill-Driven-Component` now
  sends configuration text to `tcw-configure`.
- **Tests:** router tests for both new skills (60-line body, every reference
  linked and resolving, no `$ARGUMENTS` or context injection, the other skill
  named); `tests/test_skill_path_pointers.py` (no skill writes another skill's
  `tcw-setup/references/` or `tcw-configure/references/` path); a deleted-names
  test over `skills/`, the manifests, `README.md`, `docs/guide/` and
  `docs/lifecycle/`, plus a check that `commands/` and the manifest key are
  gone; grading tests that read each case's routing assertion from
  `evals/evals.json` and check it fails a run that opened the wrong document;
  checks that `tcw-work-stage`'s fallback names where `$stage` and `$item` come
  from, and that `tcw-taxonomy` and `documentation-sync` descriptions do not
  advertise setup.

## Changed

- **Setup and configuration text moved out of usage skills.** `tcw-work`'s
  `hooks.md` keeps the roles, kinds and conditions table and how bindings run;
  `commands.md` keeps tracker runtime behaviour and store resolution, with
  one-line pointers to `tcw-configure`; `transitions.md` and the default
  lifecycle `README.md` point there for setting keys. `tcw-taxonomy` and
  `tcw-capabilities` keep how inherited entries resolve and lose how to declare
  `extends` and their `## Bootstrap` sections. `tcw-taxonomy`'s `description`
  and `when_to_use` drop seeding, bootstrapping and federating;
  `documentation-sync`'s description no longer says "declares".
- **`tcw-work-stage` works under Codex on its own.** Its manual fallback says to
  use the stage and work item named in the request in place of `$stage` and
  `$item`, and `commands.md` drops its "Claude only" label.
- **Axis A cases A1–A4 and A8 invoke `tcw-work-stage`**; B5 is `cross-axis` over
  `tcw-taxonomy` and `tcw-capabilities`.
- **`documentation-sync`'s `cut-version.md`** opens on a direct request to cut a
  version, and says to write the `upcoming.md` entries before rotating them.
- **Renamed:** `autonomous-work` → `tcw-extras-autonomous-work`,
  `tcw-triage-issues` → `tcw-extras-triage-issues`, `tcw-report` →
  `tcw-extras-report`, with every reference, eval cases B6 and B7, and the
  coverage exclusion.
- `tcw-work`'s `when_to_use` names searching the board, auditing the backlog
  and consolidating external plans, which were reached through slash commands.
- **Taxonomy: a `skill` Vocabulary term and one Feature per skill.** Fifteen
  Features, each slug the skill's directory name plus `-skill`
  (`tcw-setup-skill`, `tcw-configure-skill`, `tcw-work-skill`, …), each naming
  `skill` and the terms it operates on, with `relatesTo` links to the existing
  Features they overlap.
- **Capabilities: one `skills/<skill>` capability per skill.** Fifteen new
  capabilities, all `Supported`, each with `Feature: <skill>-skill` and
  `Subject: skill`. Nine capabilities that described a skill were folded into
  their skill's capability and deleted with `tcw capabilities rm`:
  `plugin/work-lifecycle` (split between `skills/tcw-commands-plan-work` and
  `skills/tcw-commands-drive-work-to-completion`); `work/consolidate-plans`,
  `work/search-the-work-items` and `work/audit-work-backlog` (into
  `skills/tcw-work`); `plugin/report-an-issue-upstream` (into
  `skills/tcw-extras-report`); `plugin/run-a-post-mortem` (into
  `skills/tcw-post-mortem`); `plugin/triage-github-issues` (into
  `skills/tcw-extras-triage-issues`); `taxonomy/bootstrap-the-taxonomy` and
  `capabilities/bootstrap-the-capabilities` (into `skills/tcw-setup`).
  `work/complete-a-work-item` now links `tcw://C/skills/tcw-extras-triage-issues`.

## Removed

- **`tcw-plugin`** and its skill map.
- **The five `tcw-work-stage-<stage>` skills** and their parity tests
  (`NO_PER_STAGE_SKILL`, `PER_STAGE_IDS`, `PER_STAGE_SKILLS` and the two tests
  over them).
- **Every slash command**: `commands/`, the `commands` key in
  `.claude-plugin/plugin.json`, and `COMMAND_ROUTES` with
  `test_commands_route_into_the_skill`.
