# Plan — Doc-sync directive for skills/

1. Add a tracked entry to the **Documentation Sync** list in `AGENTS.md`:
   `skills/<component>/SKILL.md [Skill-Driven-Component] — update the matching skill whenever the component it drives changes (CLI surface, model/fields, lifecycle, guardrails).`
2. Run the `documentation-sync` gate over the change — record a changelog `Internal` note if warranted; README/release-notes unaffected (no public CLI change).
3. Complete the item (`tcw work complete … --resolution done --confirm`) in an atomic commit carrying the AGENTS.md edit + the status transition.
