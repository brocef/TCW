# Outcome — Give lifecycle hooks roles, kinds, and conditions

All thirteen plan tasks shipped. Suite green at 1442 Python (baseline before this
item: 1346), 52 web unit. Every acceptance criterion is met.

## What shipped, task by task

| # | Task | Commit |
| - | ---- | ------ |
| 1 | The legacy corpus and its baselines | `6e6c2af` |
| 2–6 | `Condition`, `Binding`, `StageBindings`, the parser, rendering, `--phase` | `a79caaf` |
| 7 | The bounded subprocess runner | `c36b226` |
| 8–9 | Resolution, and conditions wired into transition checks | `24e8797` |
| 10 | Validation, including `file:` confinement | `a7ee784` |
| 11 | The Vocabulary term | `3f02d42` |
| 12–13 | Documentation Sync and the capability ledger | `205ea7d` |

## The review found this spec not ready to implement, and it was right

`codex` and `bllm-review` ran against the first draft. Six of its claims were
false or unrepresentable, and each would have been discovered mid-implementation
or, worse, at `verify`:

| The draft said | What was actually true |
| -------------- | ---------------------- |
| "the policy records which form the list arrived in" | The model it showed had nowhere to record it |
| `body_truncated` sits beside `body` in the item | C2's schema is closed; the document would fail its own contract |
| The body cap is 64 KiB | Of *characters*, which caps nothing on multi-byte text |
| Bound the output by checking it after `subprocess.run` | `run` buffers everything first; that is a cap on the result, not on memory |
| One `builtins` map | `spec` is both a stage id and an artifact name |
| `--json` is unaffected | Its stage payload had to change, and criterion 1 did not say how |

**And one finding was a contradiction inside the *epic's* spec**, not C3's: its
role table allowed only `command` in a check position while its own back-compat
table required `{skill: X}` under `transitions.<id>.pre` to keep being reported.
Verified at `spec.md:301` versus `:339`. The epic was amended rather than worked
around, in the same commit as this spec — the second time this initiative has had
to do that, after C2's `body` amendment.

Two findings were rejected after being checked: `sorted({1,"a",2.5}, key=str)`
does not raise, and an empty `builtin` registry cannot hide a misspelled key
because `builtin: true` has no key to misspell.

## Where the design landed differently than the plan expected

**The `command`-in-a-prompt exception is narrower than either table admitted.**
The role table forbids `command` in a prompt position; the back-compat table
requires `stages.<id>: [{command: C}]` to keep working. Both are load-bearing, so
the prohibition applies to the explicit `prompt:` key and the exception to the
bare legacy list. `legacy_prompt` is what lets the parser tell them apart, which
is the second reason that field is not optional. Criterion 10 asserts both halves
in one test so neither can be tidied away as redundant.

**`policy.stage()` kept its meaning rather than being migrated.** Stage bindings
were never executed — `run_pre`/`run_post` handle transitions only — so what they
always were is what `prompt` names. The accessor returning prompts is the accurate
reading, not a compatibility shim. `policy.stages`' *type* did change, and the
spec says so precisely after review pointed out the first draft's claim that
"every existing caller keeps working" was made about an attribute whose type it
was changing.

**The body cap is not the output cap.** The first implementation passed
`policy.output_cap` for both, which a test caught immediately: a node tightening
`output-cap` to keep prompts short would have silently started truncating the
request its hooks read. Two limits, two reasons, one default (`BODY_CAP`).

**The board was not part of this slice, but `_board()` was a sixth `serve`
projection site in C2** — recorded here because the same "the list is five" error
appeared twice in one initiative, both times inherited from the epic's spec.

## The bug the risky code actually had

`tests/test_generate_hook.py::test_a_chatty_stderr_does_not_deadlock` failed on
the first run with exit **-13** — `SIGPIPE`.

The stderr drain stopped reading at the cap and closed the pipe, so a generator
writing more than 64 KiB of diagnostics was killed by the signal while its
perfectly good stdout was discarded for it. The fix distinguishes the two
streams: stdout **stops** at the cap, because exceeding it is a hard failure and
the process is about to be killed anyway; stderr **keeps draining to EOF and
throws the excess away**, because a chatty script is not a failing one.

That is exactly the class of defect the spec predicted would live in this task,
and it was found by the criterion written for it rather than by a user.

## Verified by hand

- **This repository's own `tcw-config.yaml` is in the corpus** (`self.json`), so
  every `tcw` command run while developing C3 was checking the rewrite against
  the config it was running under.
- **`tcw work lifecycle --phase`** in all four legal and three illegal
  combinations.
- **`tcw validate`, `tcw capabilities check`, `tcw capabilities drift`** clean.

## Notes

- `builtin` resolves to nothing until C5 and C6 fill the two registries. Criterion
  16 pins that as intended rather than accidental; between now and then it is
  indistinguishable from "not configured", which is stated in the spec's risks.
- The `--no-exec` plan mode is a parameter of the same traversal rather than a
  report derived from a real run. Review was right that the latter is not a dry
  run, and C4 needs the former.
- `select()` is shared by prompts, artifacts, and transition checks. Criterion 8
  asserts the third specifically, because a matcher unit-tested but never wired
  into checks is the exact shape of escape this initiative keeps finding.
