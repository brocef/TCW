# Commit each TCW work lifecycle artifact stage

## Product changes

None. This changes the agent-facing TCW work process, not the `tcw` CLI or a
user capability.

## Technical changes

Update the TCW work lifecycle instructions so every durable lifecycle stage is
committed immediately after its artifact is written or materially updated.
This includes `initial-request.md`, `spec.md`, `plan.md`, `outcome.md`, and
`refined-outcome.md`, along with any other TCW work files changed as part of
that stage.

Apply the rule consistently to task and epic workflows and to the prompt
wrappers that drive planning or completion. Preserve the existing requirement
that `tcw work start` is committed before implementation code changes.

## Meta changes

Agents should no longer require a user reminder to commit request, spec, or
plan artifacts. Stage commits should remain narrow and should not sweep in
unrelated working-tree changes.

