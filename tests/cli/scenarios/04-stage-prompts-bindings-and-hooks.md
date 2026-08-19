# 04 — Stage prompts, config bindings, and hooks

The 1.0.0 headline: the lifecycle is polymorphic and CLI-driven. A node's
`tcw-config.yaml` decides what a stage prints and what runs around a transition.

## Functionality covered

- `tcw work stage <stage> <slug>` and `--no-exec`
- `tcw work lifecycle` with `--json`, `--directive`, `--phase`, `--stage`,
  `--transition`, and a slug argument
- `work.lifecycle` config: `stages.<id>.prompt` (`builtin:`, `file:`, `blob:`),
  `pre` and `post` hooks, `command:` hooks
- Hook environment (`TCW_SLUG` and friends) and fail-closed behaviour

## What is tested

| # | Assertion |
| - | --------- |
| 1 | On an **unconfigured** node, `tcw work stage spec $SLUG` exits 0 and prints TCW's built-in instructions. |
| 2 | Binding `prompt: [{builtin: true}, {blob: "PROJECT RULE"}]` on `spec` makes the output contain **both** the built-in text and `PROJECT RULE`, in that order. |
| 3 | Binding without `builtin: true` **replaces** the built-in text — the built-in marker string is absent. |
| 4 | A `file:` binding resolves relative to the node root and its content appears; a `file:` pointing at a missing path exits non-zero with a message naming the path. |
| 5 | `tcw work lifecycle` exits 0 and lists stages and transitions. |
| 6 | `tcw work lifecycle --json` is parseable JSON carrying a schema version; every stage id in the human output appears in the JSON. |
| 7 | `tcw work lifecycle --stage spec --phase prompt` narrows the output to that stage/phase only. |
| 8 | `tcw work lifecycle --directive --stage spec` prints **one line** when bound, and **nothing at all** (exit 0) when unbound. Both branches asserted. |
| 9 | `tcw work lifecycle --transition start --phase post` reports the transition's post hooks. |
| 10 | A `pre:` hook that exits 0 lets the stage through; one that exits non-zero **blocks** it, and the stage's output is not printed. |
| 11 | A `command:` hook receives `TCW_SLUG` in its environment — the hook writes `$TCW_SLUG` to a file, which the script then reads and compares to the real slug. |
| 12 | A `command:` hook that **reads stdin** does not stall the transition: the transition completes within the timeout with the hook's stdin closed. (Regression for the inherited-stdin fix.) |
| 13 | A hook that exceeds its configured timeout aborts the transition non-zero, and the item's status is unchanged. |
| 14 | `tcw work stage <stage> <slug> --no-exec` prints what **would** run and executes none of it — proven by having the hook create a sentinel file and asserting the file does not exist. |
| 15 | A malformed `work.lifecycle` block is reported by `tcw validate` as a problem, and the affected stage still behaves (advisory, not fatal) **or** fails closed — whichever the implementation does, the scenario pins it explicitly rather than leaving it undefined. |

## Refusals asserted

- unbound `--directive` prints nothing (8)
- failing `pre` hook blocks the stage (10)
- hook timeout aborts (13)
- `--no-exec` executes nothing (14)

## Explicitly not covered here

Documentation entries reaching `plan`/`implement` — that is scenario 05, because
it has its own back-compat contract.

## Notes for the implementer

Assertion 15 is deliberately open. Find out what the implementation does, then
write the assertion to match **and say so in a comment** — an unpinned behaviour
is how the next refactor changes it silently. Do not change the implementation to
suit the test; if the behaviour looks wrong, report it rather than encoding a
preference.

Assertion 12 needs a hook whose stdin would block: `cat` or `read -r line`. Run
the transition with a **held-open pipe** as `tcw`'s stdin (a background `sleep`
writing into it), otherwise the test proves nothing — an already-closed stdin
passes trivially.
