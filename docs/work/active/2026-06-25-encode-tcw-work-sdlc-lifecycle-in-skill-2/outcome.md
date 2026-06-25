# Outcome

Work completed successfully; awaiting user verification before TCW closeout.

## Changed

- Added split lifecycle docs: `lifecycle.md` as the dispatcher, `task-lifecycle.md` for standalone/initiative child work, and `epic-lifecycle.md` for initiative coordination.
- Updated `skills/tcw-work/SKILL.md` to route planning, implementation, resume, and closeout work through the lifecycle artifact spine.
- Updated `skills/tcw-work/docs/process-inbox.md` so `docs/work/inbox/` requests become backlog items plus `initial-request.md`, then the inbox source is removed.
- Added `/tcw-plan-work` and `/tcw-drive-work-to-completion` command wrappers.
- Added relation-based transition gates: initiative child tasks cannot start before their epic is active, and epics cannot complete while initiative children are still open.
- Surfaced `type` and `initiative` in `tcw work show` when present, so agents can dispatch to the right lifecycle without opening `state.yaml`.
- Added a plugin capability entry for planning and driving work items.
- Updated README, release notes, and changelog entries for the new plugin-facing workflow.

## Verification

- `pytest tests/test_recursion.py tests/test_work.py tests/test_skill_flow.py tests/test_plugin_manifests.py tests/test_capabilities.py` -> passed.
- `tcw capabilities check` -> passed.

## Follow-ups

- Decide after user verification whether to complete this work item and flip `plugin/work-lifecycle#plan-and-drive-work-items` from `Missing` to `Supported`.
- Decide whether a later TCW work item should change `delegate`/`escalate` mechanics to create backlog items directly instead of using `docs/work/inbox/` as a transient raw request channel.
