# TCW work lifecycle

Use this file to choose the smallest lifecycle document needed for the current work item. TCW's durable unit is the work item folder; lifecycle artifacts live beside `initial-request.md` so the item can move through `backlog`, `active`, and `completed` without losing context. `initial-request.md` is the always-present body/overview surface and canonical request artifact.

## Common rules

- Do not hand-edit `docs/work/` when a `tcw work` command exists.
- Preserve the work item as the source of truth. `docs/work/inbox/` is raw intake only; inspect it with `tcw work inbox show` and convert it with `tcw work inbox accept`, which generates the durable request and consumes the source after success.
- For product changes, run the tcw-capabilities planning gate before writing the technical plan, and reconcile capabilities before completion.
- For small changes, offer to compress unnecessary planning detail, but keep enough artifact context for another agent to resume safely.
- A lifecycle stage is not finished until its new or materially updated artifact
  and related TCW work files are committed. Before moving to the next stage:
  validate as appropriate, inspect the intended diff, narrowly stage only the
  current item's related work files, and commit them. Do not sweep in unrelated
  changes or create an empty commit when the stage was already complete and
  unchanged. A command that runs several missing stages must create separate,
  ordered commits for each stage.
- `tcw work start <slug>` is the implementation boundary. Run it before the first code edit and commit that status transition before implementation changes.
- `tcw work complete <slug> ...` is the closeout boundary. After it succeeds,
  commit the completion status transition and its related work-file changes.
- Do not silently complete after implementation. Stop for user verification/refinement before `tcw work complete`.

## Choose the lifecycle

Inspect the item state (`state.yaml`, or `tcw work show <slug>` when it includes the relevant fields):

- If `type: epic`, read [`epic-lifecycle.md`](epic-lifecycle.md).
- Otherwise, read [`task-lifecycle.md`](task-lifecycle.md). This covers standalone items and initiative child tasks with `initiative: <epic-slug>`.

## Command behavior

`/tcw-plan-work` runs the planning stages for the chosen lifecycle. It accepts either an existing work item slug/path or a chat request that the agent turns into a new backlog item.

`/tcw-drive-work-to-completion` detects the current stage from the item status and existing artifacts, dispatches to the chosen lifecycle, runs all missing stages through implementation or coordination, and stops in verification/refinement for explicit user approval before completion.
