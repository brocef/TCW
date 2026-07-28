# Upcoming

Developer changelog for the next version. Technical and precise; grouped by
category, with commit hash ranges so entries trace back to source.

## Fixed (`2b008bf`..)

- `skills/tcw-work/SKILL.md` — restored the YAML frontmatter (`name`,
  `description`, `when_to_use`, `allowed-tools`, `metadata`, `license`) dropped
  in `494eec9` when the skill was restructured into per-stage documents. Codex
  refuses to load a skill whose `SKILL.md` has no `---` frontmatter, so
  `tcw-work` — the central skill — was silently absent for every Codex user
  across v0.15.0–v0.15.3; Claude tolerated the omission, which is why it went
  unnoticed.

## Internal (`2b008bf`..)

- `tests/test_plugin_manifests.py` — new parametrized guard asserting every
  `skills/*/SKILL.md` opens with `---` frontmatter carrying at least `name` and
  `description`. Nothing checked this before, which is how the drop shipped.
- `tests/test_skill_lifecycle_parity.py` — the router line budget now measures
  the body after the frontmatter rather than the whole file. The 60-line budget
  was set while the frontmatter was missing; counting required metadata against
  a prose budget would have forced prose out to make room for it.
