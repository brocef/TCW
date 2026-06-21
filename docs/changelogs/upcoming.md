# Upcoming

Developer changelog for the next version. Technical and precise; grouped by
category, with commit hash ranges so entries trace back to source.

## Added (e07c8f1..HEAD)

- Claude Code / Codex **plugin packaging**: `.claude-plugin/{plugin,marketplace}.json`,
  `.codex-plugin/plugin.json`, `.agents/plugins/marketplace.json`, and a relative
  `plugins/tcw → ..` symlink (mode 120000). Skills are exposed in both ecosystems;
  commands are Claude-Code-only.
- New skill `skills/tcw-plugin/SKILL.md` — single source of the init/doctor
  procedure (pipx-install the plugin clone; doctor reconciles version drift via
  sibling-dir scan + `sort -V`, leaves editable `-e` dev installs alone). Acts as
  the Codex shim (Codex has no slash commands).
- New commands `commands/tcw-init.md` and `commands/tcw-doctor.md` — thin pointers
  to the `tcw-plugin` skill.
- New `plugin` capability namespace (`docs/capabilities/plugin/`): `install-as-a-plugin`,
  `bootstrap-the-cli`, `diagnose-the-install` (Missing → Supported at completion).
- `tests/test_plugin_manifests.py` — asserts all manifests parse, the 5 version
  fields agree, the agents marketplace stays version-free, and the symlink resolves
  to the repo root.

## Changed (e07c8f1..HEAD)

- `AGENTS.md` *Versioning* now enumerates all **5** version-bearing files (was 2).
- `README.md` — `## Install` gains an "As a plugin" path; `## Skills` updated two → three.

## Internal (e07c8f1..HEAD)

- `pyproject.toml` — `[tool.pytest.ini_options]` (`testpaths = ["tests"]`,
  `norecursedirs` incl. `plugins`) and `packages.find` `exclude = ["plugins*"]`,
  so the `plugins/tcw → ..` symlink no longer causes pytest/build to recurse the
  repo root infinitely.
