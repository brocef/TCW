# Let a child created under an already-active parent run its own planning stages

A `--parent` child created after its parent has been started is born `active`,
because it is nested in an active item. The `request`, `spec` and `plan` gates then
refuse it ("'spec' is not legal for an item in 'active'; it runs in backlog"), and
only `implement` passes. The lifecycle's own order causes this: the plan stage ends
by telling the agent to run `tcw work start <parent>`, and decomposition into
children happens after that. So every child is born active, and the model the
decompose procedure documents cannot be followed. That model is "Each child gets
its own initial-request.md/spec.md/plan.md as it's planned — the parent stays a
thin umbrella."

## Steps to reproduce

1. Parent item in backlog with `initial-request.md`. Run the spec stage, then the
   plan stage.
2. The plan stage prompt says "Commit plan.md on its own, before `tcw work start`",
   then "When this stage's output is written, run `tcw work start <slug>`". Run
   `tcw work start <parent>`.
3. As plan.md's decomposition section says: `tcw work new "<title>" --parent <parent>`, four times.
4. `tcw work stage gate spec <child>` refuses. `request` and `plan` refuse the same way.

## Possible fixes (from the reporter)

- (a) `new --parent` under an active parent creates the child in `backlog`, with its
  own planning stages available;
- (b) the plan stage tells the agent to create `--parent` children *before*
  `tcw work start`; or
- (c) the decompose procedure's text says nested children are implement-only.

The reporter's workaround: the parent's spec.md and plan.md carry all four
children's design, and each child writes only outcome.md.

## Origin

Reported 2026-09-21 by the Claude session working in proposit-app
(`/Users/brian/Projects/proposit-orchestration/proposit-app`). It was driving one
work item through spec → plan → decompose → implement on tcw CLI 2.5.0 (2.4.0 until
partway through the session). The requester asked for it to be tracked at high
priority.

## References

- `2026-09-16-stop-an-item-reaching-implement-without-a-spec-and-plan-and-say-how-to-plan-an-item-started-too-early`
  shares the symptom: an active item can't run spec/plan, and the implement gate
  passes without a plan. That item is about an item started too early by hand. This
  one is about children that never had a backlog state at all. Its "Recovery"
  question (may spec/plan run in active, or is there a way back to backlog) is one
  possible answer to both.
- `tcw work procedure prompt decompose`: the "thin umbrella" text that contradicts the behavior.
