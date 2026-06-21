# Doc-sync directive for skills/

## Product changes

## Technical changes

## Meta changes

- Add a directive to `AGENTS.md` (the project guide) requiring that **any change to this project updates the matching `skills/` file** — `skills/tcw-work/SKILL.md`, `skills/tcw-capabilities/SKILL.md`, etc. — so the driving skills never drift from the CLI/model they describe.
- Wire it into the existing Documentation Sync flow: add a tracked entry (trigger = a change to the component a skill drives) alongside README / release-notes / changelog, so the `documentation-sync` gate evaluates `skills/` too.

Small, doc-only change. Spec/plan to be written into this folder at planning time if needed.
