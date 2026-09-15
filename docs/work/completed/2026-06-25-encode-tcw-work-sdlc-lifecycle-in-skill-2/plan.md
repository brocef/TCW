# Plan — encode the TCW work SDLC lifecycle in the skill

1. Update the plugin capability ledger for the new planning/execution command affordance.
2. Add split lifecycle docs: `lifecycle.md` as the dispatcher, `task-lifecycle.md` for standalone/initiative child work, and `epic-lifecycle.md` for initiative coordination.
3. Update `skills/tcw-work/SKILL.md` to make the lifecycle the primary work-driving model and route detailed work through the dispatcher.
4. Add `/tcw-plan-work` and `/tcw-drive-work-to-completion` command markdown wrappers.
5. Add relation-based gates so initiative child tasks cannot start before the epic is active and epics cannot complete while initiative children are still open.
6. Update public docs and upcoming release/changelog files if documentation sync triggers fire.
7. Verify skill docs, command docs, and transition gates with targeted reads plus the relevant test subset.
