# Taxonomy skill + per-component init bootstrap with extends CLI

## Product changes

## Technical changes

## Meta changes

## Product changes

- `/tcw-taxonomy-init` and `/tcw-capabilities-init`: agent-driven bootstrap — deep-dive the codebase, propose terms / capabilities, refine with the user, write the first draft.
- `tcw taxonomy extends add <alias> <path>` / `rm <alias>`: declare (or drop) taxonomy inheritance from sibling repos via CLI instead of hand-editing config.yaml.

## Technical changes

- New `tcw-taxonomy` skill (thin router + docs/init.md), peer of tcw-capabilities/tcw-work.
- `TaxonomyStore.extends_add/extends_remove` (ABC) + FsTaxonomyStore impl writing docs/taxonomy/config.yaml; `tcw taxonomy extends` nested subparser; "extends" added to SUBCOMMANDS.
- Bootstrap sub-docs: skills/tcw-taxonomy/docs/init.md (incl. inheritance step) and skills/tcw-capabilities/docs/init.md (taxonomy-first).
- Two command routers; one gated line added to tcw-capabilities SKILL.md.

## Meta changes

- Docs sync: README, docs/release-notes/upcoming.md, docs/changelogs/upcoming.md. No version cut.
- Capabilities: declare two new bootstrap capabilities (Missing); body-edit federate-shared-vocabulary (stays Partial).
