# Outcome — Share one descendant walk, and say when delegate names a node with no board

## What shipped

| Task | Commit | What |
| ---- | ------ | ---- |
| 1–2 | `1db269af` | Tests, then `FsWorkStore.initiative_slices` (one walk for the completion gate and `reconcile`'s table), `_label`, and `delegate`'s refusal for a registered node with no board. |
| docs | `5e0aa082` | Changelog and release-note entry files. |
| review | `df415d68` | The new refusal only for nodes below this one; a board configured but not openable says "not available here" with its reason; the test fixture gains a boarded sibling. |

## Tests

- `tests/test_boardless_delegate_and_slices.py`, 6 tests: the gate and the table
  read the same slices; boardless node below; board declared but not
  provisioned; board configured but broken; unregistered name; boardless
  ancestor.
- Against the code before the fix, the two `delegate` tests failed and the
  slice and unregistered-name tests passed (guards). Mutation-checked: a
  shared walk that stops at this node turns the slice test red; at review, each
  of the three fixes, reverted, turns its test red.
- Full suite after the review fixes: 4803 passed, 3 skipped.

## What the plan or spec got wrong

- **The refusal was written for "registered", not "below".** Naming a boardless
  ancestor offered the caller's own children as the place to delegate; a
  sibling was refused for the wrong reason. Found by review; the spec's goals
  were amended.
- **"Keeps no board" was said of a board configured but broken**, dropping the
  real reason. Found by review.
- The spec called `_tasks_for`'s `stores` parameter unused; `reconcile` passed
  it. Removing it is harmless; `reconcile` now opens the stores a second time.

## Autonomous decisions

- No advisor consult: no open question.
- Review (adversarial-code-reviewer, "merge after fixes"): accepted findings
  1–3. Left, not filed: `reconcile` now opens each store about twice as often
  (small graphs only; no behavior difference).
