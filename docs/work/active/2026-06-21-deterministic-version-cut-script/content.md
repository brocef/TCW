# Deterministic version-cut script

## Product changes

(none — developer tooling; the `tcw` CLI surface is unchanged.)

## Technical changes

- Add `scripts/cut_version.py`: bumps the version in all 5 version-bearing
  files in lockstep, rotates `docs/{changelogs,release-notes}/upcoming.md` →
  `v{version}.md` (and recreates fresh `upcoming.md`), then commits and tags.
- Importable pure functions (`current_version`, `next_version`, `bump_files`)
  + git side-effects, with `tests/test_cut_version.py` self-checking the math,
  drift detection, and an end-to-end cut over a tmp git repo.

## Meta changes

- The version-cut ritual becomes a single command, so future cuts cost few
  tokens. `CLAUDE.md` Versioning section points at the script.
