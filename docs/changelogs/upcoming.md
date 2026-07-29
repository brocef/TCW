# Upcoming

Developer changelog for the next version. Technical and precise; grouped by
category.

## Added

- **`tcw-triage-issues` skill** (`skills/tcw-triage-issues/SKILL.md`) — sweeps a
  project's own open GitHub issues via `gh`, filters the ones already triaged,
  classifies the rest as worth-doing / duplicate / not-worth-doing / ill-defined,
  creates work items only for the first, and offers a reply for each. Single
  `SKILL.md`, no `references/`: one linear procedure, nothing conditional enough
  to earn the indirection.
- **`/tcw-triage-issues` command** (`commands/tcw-triage-issues.md`) — routes to
  the skill and names the Codex fallback. Carries no instruction the skill lacks.
- **Capability `plugin/triage-github-issues`** (`cap-2c9a74`).

## Changed

- **`skills/tcw-work/references/stage-inbox.md`** — `## Purpose` now points at
  `tcw-triage-issues`, naming a GitHub issue as the same intake shape from a
  different source. The pointer is in `Purpose` rather than `Steps` because
  `test_skill_lifecycle_parity` requires every `Steps` line to carry a
  `[judgment]`/`[gated]` marker.
- **`skills/tcw-plugin/SKILL.md`** — the skill map's feedback section now covers
  both GitHub-issue skills and states their opposing directions; the routing list
  gains an entry.
- **`.codex-plugin/plugin.json`** — `longDescription` skill count seven → eight.
- **`README.md`** — install inventory (skills + commands), the skill-list bullet,
  and two counts that were load-bearing prose: "six skills" → seven, "five
  axis/plugin skills" → six.

## Internal

- No `tcw` CLI, model, or store change. Triage is judgment and lives entirely in
  the skill; no `tcw work inbox fetch` verb, no `source`/`external-ref` field, no
  new lifecycle stage.
- The already-triaged filter greps `docs/work/` for the issue URL, then resolves
  the slug through `tcw work show` to branch on status — so the status read goes
  through the CLI rather than off the folder name.
