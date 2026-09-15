# Work item priority

## Product changes

- A caller can give a work item an **integer priority** — higher integer = higher priority.
- Priority is settable when **creating** (`tcw work new "<title>" --priority N`) and when **editing** an existing item (`tcw work edit`).
- Default priority is **unspecified**. With priority unspecified, items keep their current order (creation order). `tcw work list` orders specified-priority items above unspecified ones (descending by integer), unspecified items retaining creation order among themselves.

## Technical changes

- Add `priority: int | None` to the `WorkItem` model and the abstract `WorkStore` interface (creation arg + a set path). Litmus test passes — a remote tracker (Jira) has a native priority field, so this belongs in the model, not the FS adapter.
- `FsWorkStore` persists it in `state.yaml`; `create()` accepts it, `set_field`/`edit` already generalize.
- CLI: `new --priority`, an `edit` path for priority, and `list` sort key.
- Decide the stable sort: (priority desc, then created/creation order) so output is deterministic.

## Meta changes

- Update design doc `docs/plan/phase-5-work.md` (the work model) in the same change.
- Documentation Sync: README (CLI usage), `docs/release-notes/upcoming.md`, `docs/changelogs/upcoming.md`, and `skills/tcw-work/SKILL.md` (priority in the lifecycle/quick-reference).

Spec/plan to be written into this folder (`spec.md`, `plan.md`) at planning time.
