# Outcome

A wrong subcommand now gets a "did you mean" line after argparse's own
"invalid choice" message, and a wrong stage name after
`tcw work stage gate|prompt` gets a line saying which stage writes that
artifact, or which command runs that transition.

- New module `tcw/cli_suggest.py`: `SuggestingParser`, used as the root parser
  (every subparser inherits it), and `attach_index`.
- `_stage_hint`, `_TRANSITION_COMMAND` and `_stage_command` in
  `tcw/work/cli.py`.
- `_HidesRemovedSpellings` is gone: only subcommands that `--help` lists are
  ever offered or listed.

## What shipped, task by task

| Task | What | Commit |
| ---- | ---- | ------ |
| 1 | failing tests (xfail) for criteria 1-8 | `6d61c6ef` |
| 2 | `SuggestingParser`, the index, and the three rules | `2a1c42df` |
| 3 | stage-name hints | `2a1c42df`, `61726d0e` |
| 4 | capability `cli/get-a-suggestion-for-a-mistyped-command`, changelog, release notes | `66f0065b` |
| 5 | review fixes | `58093222` |

## What the plan and spec got wrong

- **The design kept `_HidesRemovedSpellings` as a subclass with a
  `_visible_choices` hook.** Simpler without it:
  - One rule, "offer only what `--help` lists", hides the seven removed stage
    spellings, which are registered without `help=`.
  - Those spellings are the only subcommands anywhere in the tree that `--help`
    leaves out.
  - The spec's Design section was rewritten to describe the code as built.
- **Goal 5, "the existing error text stays word for word", held only on some
  Pythons.**
  - The first version rebuilt the message itself, with quoted choices.
  - Python 3.12 and 3.13 print them unquoted, so every group's text changed
    there. CI runs only 3.11 and 3.14, so nothing caught it.
  - Now, where nothing is hidden, the message is argparse's own. That was
    checked by hand under 3.12.13, and a test compares against argparse's own
    `_check_value`.
- **`discard` was advised as `tcw work discard`, which does not exist.** A
  discard is `tcw work complete --resolution <not done>`. Found while checking
  every transition id before review. `_TRANSITION_COMMAND` names the real
  command, with the resolutions taken from `WORK_RESOLUTIONS`.
- **The spec named the class `_SuggestingParser`.** It is `SuggestingParser`.

## Review

The adversarial review returned "merge after the fixes below". Accepted:

1. **Removal commands were suggested.** `tcw work rm x` offered
   `tcw taxonomy rm`, and `tcw work tracker delete x` offered
   `tcw work delete`, which deletes a work item. That made the capability's
   "words for removing things are never suggested" false.
   - `rm`, `drop` and `delete` are now never offered by any rule.
   - A typed one gets no hint at all.
   - The spelling rule also offered `tracker release` for `tracker delete`,
     found by hand after the first fix, which is why a removal word now gets
     no hint rather than only a filtered one.
2. **The 3.12/3.13 wording** (above).
3. **`inbox` was advised with `<slug>`**, which both verbs refuse for it.
   `_stage_command` now builds every such command and is shared with the
   removed-spelling message, which already had that rule.
4. **Rule 1 preferred the shallowest path in any component.** It now prefers
   paths sharing the most leading words with where the error happened, so
   `tcw work tags show` points inside `tcw work`.
5. **Test gaps:** removal words, completing a valid next word,
   same-component-first, argparse's own wording, `inbox` without a slug. Each
   new test was mutation-checked.

Left for a separate change:

- adding Python 3.12 or 3.13 to the CI matrix;
- the fragility of finding the next word if a group parser ever gains an
  option that takes a value. Today none does.

Neither is a defect in this change.

## Checks

- 25 tests in `tests/test_command_suggestions.py`, and 86 with
  `tests/test_stage_verb.py`, pass.
- Every new assertion was mutation-checked: each mutation turned its test red.
- `tcw validate` and `tcw capabilities check` pass.
- Full suite: see `refined-outcome.md`.

## Autonomous decisions

- **Suggest only, or also accept aliases?**
  - Opus and Sonnet: suggest only, since an alias is a second spelling to
    support forever.
  - Chose suggestion only.
- **Where to hook argparse.**
  - Sonnet: `_check_value`, not `error()`.
  - Opus: subcommand choices only, and turn `suggest_on_error` off.
  - Both taken.
- **Review finding 1, filter or silence?** Chose silence for a typed removal
  word, which goes beyond the reviewer's "never offer". A spelling guess from
  `delete` to `release` is a guess about what to destroy.
- **Review finding 2, fix or accept?** The reviewer offered either fixing the
  code or rewording the spec. Chose to fix, so the promise in the spec and
  changelog stays true.
- **Rejected: none.** The two items listed under "needs a separate change" are
  not defects here.
