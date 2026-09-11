# Outcome — Accept comma-separated tags

Both defects closed. `2614 passed`, twenty above the `2594` baseline.

## What shipped, task by task

| Task | Commit | What |
| --- | --- | --- |
| 1 | `fa0a2c06` | Thirteen CLI tests for the four options, red |
| 2 | `f3bec6a9` | `_tag_list` / `_tags`, four options gain `--tags` / `--untags` |
| 3 | `ce0cc74e` | `tags add` / `tags rm` split too; seven more tests |
| 4 | `ce0cc74e` | The `--blocked-by` non-goal guard, mutation-checked |
| 5 | `ff995131` | `work/tag-a-work-item` revised |
| 6 | `402b8782` | Guide, tag reference, command table, release notes, changelog |

## Acceptance criteria

All eighteen met, at `402b8782`.

Criteria 1 through 13 are covered by twenty tests in `tests/test_work_tags.py`,
all green. Criterion 14 is the `--blocked-by` guard. Criterion 15 was read by
hand: `--tag, --tags TAG` appears in `new`, `list` and `edit`;
`--untag, --untags UNTAG` appears in `edit`, the only command that has it; and
both `tags` positionals say `a value may be a,b,c`. Criterion 16
is `2614 passed in 792.52s`. Criterion 17 is `capabilities OK` plus the revised
description. Criterion 18 is Task 6, with the README evaluation recorded.

Driven by hand against the real CLI on four scratch nodes, not only through the
suite: registering with a comma, an empty value, the lost `--ta` abbreviation,
the exact `--tag` spelling still working, and a node poisoned before the fix.

## What the plan and spec got wrong

- **The first spec covered where tags are applied and missed where they are
  registered.** That is the whole item. `tcw work tags add "cli,docs"` wrote
  `cli-docs` into `tcw-config.yaml`, `tcw validate` reported OK, and every later
  `--tag cli,docs` succeeded silently. The spec proposed fixing the four options
  that read a tag and left the two commands that write the registry, so it
  shipped the cure for the symptom and left the cause. Both adversarial reviews
  found it independently. **The root cause was scope by grep**: the design table
  was built from `action="append"` sites, which is a search for a mechanism
  rather than for a meaning, and the registry positionals use `nargs="+"`.

- **The first spec was wrong about four other things**, each corrected in place
  rather than dropped: it called the change additive when three behaviours
  change; it added parser-level deduplication justified as something "the store
  already assumes", when the store performs it at all three call sites; it said
  argparse `choices=` made a comma unsafe for `--component`, which is an
  implementation detail rather than a reason; and it called `--blocks` accepting
  commas while `--blocked-by` does not an inconsistency, when `--blocks` takes
  only slugs and the asymmetry follows from the value grammar.

- **A custom argparse `Action` was the wrong mechanism and existed only to
  support the deduplication that was itself unnecessary.** `action="extend"`
  with a list-returning `type=` does everything. Two classes of work removed by
  one review question.

- **Acceptance criterion 10 described a behaviour that has never existed.** It
  required `--untags cli,nope` to refuse. Removal checks no registry at any call
  site and `--untag nope` succeeds as a no-op today. The criterion was corrected
  rather than the code, and the asymmetry is now stated in the capability:
  applying an unregistered tag writes data nobody can act on, removing one
  cannot.

- **The shared splitter raised the wrong exception type**, which the plan did not
  anticipate. `argparse.ArgumentTypeError` raised from a command handler escapes
  uncaught, because handlers catch `ValueError`. Two of the Task 3 tests failed
  on it. Split into a pure `_tag_list` raising `ValueError` and a thin `_tags`
  wrapper for argparse.

- **The plan's Task 6 missed that `skills/tcw-work/references/commands.md` is
  already unformatted**, so `pnpm prettier --check` on it is red before and
  after. Left red rather than reformatted, since the diff would be unrelated to
  this item. The changelog was also unformatted, left that way by the previous
  item whose format check was scoped to the README and the guide; that one is
  fixed here because this item edits it anyway.

## Notes

- **Newly accepted costs, both in the spec's Risks and in the release notes.**
  `--ta` and `--unta` stop resolving, because Python's parser accepts unambiguous
  long-option prefixes and `--tags` makes them ambiguous; `--tag` still matches
  exactly. And `--tags ""` is an error rather than "no tags", so a script passing
  a possibly-empty variable must omit the option.
- **A node poisoned before this change is not repaired**, deliberately. Verified
  by hand that it is also not made worse: the joined tag still registers, the
  item still reads, `tcw validate` still reports OK, the board filter still finds
  it, and `tags rm "cli,docs"` no longer removes it by accident. A `validate`
  warning for a registered tag that is the hyphen-join of two others would close
  this and belongs to its own item.
- **Priority was raised from 20 to 35 during the spec stage.** Filed as "additive
  sugar", which the alias is. The value is entirely the silent corruption.
- **A neighbouring backlog item will inherit this decision unread.**
  `2026-09-10-let-a-node-declare-its-own-work-item-state-fields` says a declared
  field should behave the way a tag does. Whoever picks it up should read this
  spec's non-goals rather than re-deriving the comma rule.
