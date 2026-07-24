# Upcoming

Developer changelog for the next version. Technical and precise; grouped by
category, with commit hash ranges so entries trace back to source.

<changes starting-hash="d163961" ending-hash="b8e3895">

### Added

- `documentation-sync` skill (`skills/documentation-sync/`) — a TCW-owned port of the
  documentation-sync trigger-evaluation workflow: `SKILL.md` router plus
  `references/release-notes-and-changelogs.md` and `references/setup.md`. Trigger
  vocabulary (`Public-API`, `Public-{Name}-API`, `Any-Code-Change`, `Only-Breaking`) is
  a base set projects may extend with named triggers (e.g. TCW's `Skill-Driven-Component`).
- `tests/test_documentation_sync_wiring.py` — guards that the skill files exist, no
  `skill-cefailures` reference survives, and the tcw-work lifecycle invokes the skill.

### Changed

- Documentation-sync is now sourced from TCW itself instead of the external
  `skill-cefailures:documentation-sync` skill. `AGENTS.md` `## Documentation Sync`
  directive and the `tcw-work` lifecycle references (`task-lifecycle.md`,
  `epic-lifecycle.md`) now invoke the TCW-owned `documentation-sync` skill at the plan
  and completion gates.
- Skill count and framing updated in `README.md` (`five` → `six`; the CLI-driver framing
  now admits one cross-cutting process skill) and `.codex-plugin/plugin.json`
  (`longDescription` / `shortDescription`); `.claude-plugin/plugin.json` and
  `.claude-plugin/marketplace.json` framing softened for consistency.
- The absorbed skill defers version-cutting to the project's own process (TCW's
  `scripts/cut_version.py`) rather than hardcoding a path, and replaces the FOLLOWUPS.md
  pattern with `tcw work` backlog items.

</changes>
