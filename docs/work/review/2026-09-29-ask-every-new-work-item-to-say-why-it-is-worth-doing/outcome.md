# Outcome — Ask every new work item to say why it is worth doing

## What shipped

- **`tcw-config.yaml`:** `work.procedures.create-work` holds two bindings,
  `builtin: true` and then `file: docs/procedures/create-work.md`.
- **`docs/procedures/create-work.md`:** requires a `## Why` section, placed
  after the idea and before `## Origin`, in every item and raw inbox entry the
  procedure creates.
  - It covers four points: without it, with it, cost and risk, and
    alternatives.
  - It has an "unknown" rule instead of invented benefits, with what each run
    mode does when "without it" cannot be answered.
  - It covers amendments, and gives the updated body template.

## Checked

- `tcw validate`: OK.
- `tcw work procedure prompt create-work`: TCW's own text first, ending at
  "## 5. Report", then this project's section last.
- This item's own `intake.md` was written with a `## Why` section, as a first
  use of the new rule.

## Decisions

- **Filed as a work item and taken through the lifecycle,** per this repo's
  rule that all work is tracked. It is small, so I did not run a code review
  or the verifier: no `tcw/` code changed.
- **No changelog or release-note entry,** because this is this repository's
  own configuration and users of TCW do not receive it.
