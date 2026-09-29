# Outcome — Let --untag remove a tag an item holds that is not a valid tag

## What shipped

| Task | Commit | What |
| ---- | ------ | ---- |
| 1–2 | `b1279476` | Tests, then `--untag` matched verbatim against the item's tags before `_tag_list`, and `_validate_tags(tags, held=…)` from `update_work`. |
| plan | `3754d663` | Spec and plan amended: held tags pass update validation (see below). |
| docs | `8ac283ac` | `docs/guide/work.md`, `skills/work/references/tags.md`, changelog and release-note entry files. |
| review | `bf7c86e7` | Review fold-in: tests for a held unregistered tag and for exact-match priority; spec, docs and docstring widened to say so. |

## Tests

- `tests/test_untag_invalid_tags.py`, 8 tests: removing held `'cli,docs'` and
  `'!!!'` one at a time; a comma list still removing each tag; an invalid value
  the item does not hold refused (exit 1); `--tag` on an item holding an invalid
  tag; a save resending held tags; adding an invalid tag still refused; a held
  unregistered tag kept and still reported by `check`; an exact held match
  removed as written and not split.
- Mutation-checked: dropping the verbatim match, and dropping `held` from
  `update_work`, each turns the intended tests red.
- Full suite: see `refined-outcome.md`.
- Hands-on: see `refined-outcome.md`.

## What the plan or spec got wrong

- **The spec put the fix in the wrong place.** It limited the change to `--untag`
  and listed "changing `_validate_tags`" as a non-goal. Criterion 1's own example
  (`'cli,docs'` and `'!!!'` both held) could not pass that way: removing one left
  the other, and `update_work` re-validated the whole remaining list. The
  intake's other two symptoms (every `--tag`, every web save refused) have the
  same root, so the fix moved to `update_work`'s validation — "an edit is refused
  for what it adds". Spec and plan amended in `3754d663`.
- **The widened rule also covers a tag that is valid but no longer registered**,
  which used to be refused at edit time and is now kept (still reported by
  `check` and `tcw validate`). The review found the spec did not say so; it now
  does, and a test pins it.
- **The new test file** is `tests/test_untag_invalid_tags.py`, as planned; its
  helpers come from `tests/test_item_tags_read.py`.

## Autonomous decisions

- No advisor consult: the one design question (where the fix belongs) was
  settled by reading `update_work`, which every tag edit passes through.
- Review (adversarial-code-reviewer, DONE with notes). Accepted and folded in:
  pinning the unregistered-held-tag behavior, documenting and testing exact-match
  priority, the docstring note on the read form. Rejected: a notice when
  `--untag` names a tag the item does not hold — the silent no-op is pinned on
  purpose by `test_cli_untags_ignores_a_tag_the_item_does_not_carry`, and
  changing it is a separate decision. Accepted as is: a non-string held entry
  (`True`) is written back as its text; nothing is lost and `check` reports it.
