# Upcoming

Developer changelog for the next version. Technical and precise; grouped by
category, with commit hash ranges so entries trace back to source.

## Internal (cb5543f..45ca608)

- Add `scripts/cut_version.py` — deterministic version cut: bumps all 5
  version files in lockstep, rotates `docs/{changelogs,release-notes}/
  upcoming.md` → `v{version}.md`, recreates fresh `upcoming.md`, commits, and
  tags (no push). Aborts on version drift or a non-unique match. Covered by
  `tests/test_cut_version.py`. `AGENTS.md` Versioning section now points at it.
