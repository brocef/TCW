# Upcoming

Developer changelog for the next version. Technical and precise; grouped by
category, with commit hash ranges so entries trace back to source.

## Internal

- `skills/tcw-work`: split into a progressive-disclosure router + `docs/` sub-docs
  (`process-inbox.md`, `decompose.md`, `cross-node-epic.md`). The router (107 → 47
  lines) keeps the core lifecycle, planning, resume, and quick-ref inline; rare
  sub-procedures load on demand. No CLI / behavior change. `tcw-capabilities` left
  inline (too small to earn the split). Skill-authoring convention documented in
  `AGENTS.md`. (`5ddaa20`..HEAD)
