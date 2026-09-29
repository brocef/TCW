# Outcome — Match an epic's children by the epic's node as well as its slug

The autonomous run held this item back because the advisors split on a
data-format choice that is hard to undo. The user chose option A
(2026-09-29): record the epic's node with the reference.

## What shipped

| Commit | What |
| ------ | ---- |
| `29364610` | `initiative` may be `<project-id>/<slug>`. `_initiative_holder` is the one rule behind `initiative_epic`, the slice walk, the graveyard walk and the list's nesting. `qualify_initiative` (the abstract default returns the value unchanged) is applied by `create_work`, `update_work`, `inbox_accept` and `escalate`. `delegate` always qualifies. Also tests, the guide, skill references, the changelog and the release note. |
| `88d9b0af` | Review fold-in: a qualified value must name this project or one above it; a graveyard record counts as holding a slug; the `tracker import` re-run check qualifies both sides; `delegate` checks a qualified value from the child's side; the test fixes. |

## Tests

`tests/test_initiative_node_qualified.py` has 9 tests: acceptance criteria 1
to 6, a qualified value naming a sibling project, and a resolved local epic
on a clone missing its `completed/` folder. `test_recursion.py`'s delegate
test now creates the epic it names and expects the qualified value.

Before and after:

- Against the code before the fix, the criteria 1, 2, 3, 5 and 6 tests fail;
  criterion 4 (backward compatibility) passes both before and after.
- Against `29364610`, the two tests added at review fail.

Mutation checks (each change undone, its test confirmed red):

| Change undone | Test that went red |
| ------------- | ------------------ |
| Slice walk back to comparing text | 3 tests |
| Graveyard walk back to comparing text | The graveyard test |
| `delegate` no longer qualifying | The 2 `delegate` tests |
| `create` no longer qualifying | The criterion 5 test |
| The old list-view code | The list test |
| The tombstone holder | The clone test |

Hands-on, with the real CLI on a scratch graph (`root` with `kid`, each
holding an epic of the same name):

- `delegate` wrote `initiative: root/…`.
- After `inbox accept` in `kid`, `list -i` nests the slice under `root`'s epic.
- `root`'s epic refuses to complete while the slice is open.
- Once the slice is discarded, `root`'s epic shows "ready-to-close" and then
  completes; `kid`'s epic is untouched.

## What the spec got wrong

- **Goal 3's "exactly when".** It did not hold for a qualified value naming a
  sibling project. That value passed the start gate, but no walk ever counted
  it.
- **"Only affects old data".** This was wrong. A bare value written today
  changed meaning on a clone that was missing the resolved epic's folder.

Both were amended as Goals 4 and 5.

## Autonomous decisions

- **The format was decided by the user**, after the advisors split: Codex
  favored A, Opus favored B.
- **An unresolvable value**, bare or qualified, is stored as given by
  `new`/`edit`, the same as today. `delegate` refuses instead, because the
  child cannot resolve it any better than the sender.
- **Review (adversarial-code-reviewer, NOT DONE)**:
  - Accepted all three main findings and the minor `delegate` check. I chose
    to refuse sideways values rather than widen the walk, as the reviewer
    recommended.
  - Accepted the weak-test finding.
  - Rejected folding `delegate`'s formatting into `qualify_initiative`. It
    resolves from the sender rather than from the item's own node, so it is a
    different question; the comment says so.
  - Left for a separate change, not filed:
    - read paths can now raise from `get` (`MultipleMatch`, an interrupted
      claim) where the old string comparison never did;
    - a web or CLI edit rewrites an unchanged old bare value to the qualified
      spelling.
- **Not tested at runtime:** the `tracker import` re-run comparison, which
  needs a tracker client. It is a single comparison, and I checked it by
  reading.
