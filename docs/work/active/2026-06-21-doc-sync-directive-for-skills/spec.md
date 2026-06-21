# Spec — Doc-sync directive for skills/

## Problem
The `skills/` driving skills (`tcw-work`, `tcw-capabilities`) teach agents to operate each component through its CLI. When a component's CLI surface, model, or lifecycle changes, the skill silently drifts — nothing forces it to be updated in the same change.

## Change
Make "update the matching `skills/` file" a tracked obligation. Add a new entry to the **Documentation Sync** section of `AGENTS.md` so the existing `documentation-sync` gate evaluates `skills/` alongside README / release-notes / changelog.

## Acceptance
- `AGENTS.md` Documentation Sync list includes a `skills/<component>/SKILL.md` entry with a clear trigger (the driven component changed).
- The entry is phrased so the `documentation-sync` skill picks it up like the others (path + trigger tag + "update when…").

## Out of scope
No code, no CLI, no model change. Pure meta/process.
