# Outcome

Work completed successfully.

## What changed

- Added an always-visible rule to the `tcw-work` skill requiring a narrow
  commit after every new or materially updated lifecycle artifact.
- Defined the shared checkpoint procedure in the lifecycle dispatcher,
  including diff inspection, narrow staging, ordered commits, and no empty
  commits for unchanged stages.
- Added explicit request, spec, plan, outcome, refined-outcome, start, and
  completion checkpoints to both task and epic lifecycle guidance.
- Updated `/tcw-plan-work` and `/tcw-drive-work-to-completion` so a single
  invocation that runs multiple stages creates separate ordered commits.
- Updated README and upcoming release notes for the public agent-workflow
  change. The developer changelog was not updated because no code changed.

## Verification

- `tcw validate` -> `validate OK`
- `git diff --check` -> passed
- Confirmed all six driving instruction surfaces contain explicit commit
  guidance:
  - `skills/tcw-work/SKILL.md`
  - `skills/tcw-work/references/lifecycle.md`
  - `skills/tcw-work/references/task-lifecycle.md`
  - `skills/tcw-work/references/epic-lifecycle.md`
  - `commands/tcw-plan-work.md`
  - `commands/tcw-drive-work-to-completion.md`

## Lifecycle commits demonstrated

- `9f759e5` — request checkpoint
- `1ce304a` — spec checkpoint
- `6c087dd` — plan checkpoint
- `7f5809e` — start transition checkpoint
- `6aae92d` — implementation and documentation changes

## Deviations and follow-ups

No implementation deviations or follow-up work items are needed. This change
does not add CLI enforcement; the existing hard commit-range enforcement item
remains a separate backlog concern.
