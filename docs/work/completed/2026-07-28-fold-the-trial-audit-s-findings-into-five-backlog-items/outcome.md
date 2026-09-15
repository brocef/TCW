# Outcome: Fold the trial audit's findings into five backlog items

All nine planned tasks shipped. Suite green: **1066 passed**. `tcw validate` OK,
`tcw capabilities check` OK.

## What shipped

| Task | Commit | What landed |
|---|---|---|
| 1 | `80eded4` | `--title` on `tcw work edit`, `_nonempty` guard, corrected subcommand help, 2 tests |
| 2 | `2dbb609` | Findings into `2026-07-03-transactional-multi-file-writes-in-the-fs-store` |
| 3 | `34dc014` | Findings into `2026-06-22-concurrency-safe-work-claims-…` |
| 4 | `2ddd4b9` | Findings into `2026-07-01-transitive-taxonomy-inheritance` |
| 5 | `e61b9ef` | Retitle of the Markdown editor item + body heading and note |
| 6–9 | `d97e0f2` | README, changelog, release notes, `tcw-work` command table |

Planning artifacts: `d05e960` (spec + capability), `b0bcbdc` (plan).

## Task 1 — the flag

Three edits to `tcw/work/cli.py`: `_nonempty` validator, `--title` on the `edit`
subparser, `title=_provided(args.title)` in the `update_work` call. No store
change, as planned.

Tests in `tests/test_work.py`: `test_cli_edit_title_keeps_slug_and_body` (title
changes, slug does not, `initial-request.md` byte-identical) and
`test_cli_edit_rejects_empty_title`, parametrized over `""` and `"   "`.

The plan's prediction that argparse never calls `type=` for an omitted flag held —
`_nonempty` needed no `None` branch.

## What the spec and plan got wrong

**1. The "bonus finding" was not a finding.** The spec claimed `create_work`'s
two-write gap as new material for the transactional item, calling it the one that
"matters more, because it is on the path users actually hit". It is already that
item's *first bullet* — `initial-request.md:14-16` describes the exact `mkdir` →
`_atomic_write` → `_atomic_write` shape.

The cause is worth naming: the spec verified the claim against `fs.py` and never
re-read the item the claim was destined for. That is the same failure this whole
work item exists to clean up after, reproduced inside it. Withdrawn in `spec.md`
and struck from `plan.md` rather than quietly dropped. Nothing was lost —
`FsWorkStore.create` and the `accept_inbox` precedent were the genuinely new
material, and both landed.

**2. The spec undercounted `create`'s test callers.** It said "at least eight
modules" while listing seven. The verified figure is 17 test modules containing
`.create(`, each of which constructs an `FsWorkStore`. The target item carries the
17 figure; the spec was corrected to match.

**3. Task 1 invalidated citations written by tasks 2–4.** Adding 12 lines to
`tcw/work/cli.py` shifted every `cli.py` line number cited later in the same item:
`973 → 982`, `1020 → 1030`, `208 → 216`. Caught by the plan's manual citation
read-back, and repointed in the two target items, `spec.md`, and `plan.md`.

This is a real sequencing lesson, not a clerical slip: **a plan that edits code
and also writes citations into documents must re-verify the citations after the
code task, not before.** The plan happened to order the code task first, which is
what made the drift visible; the reverse order would have produced four documents
whose citations were correct when written and wrong when committed.

`initial-request.md` is deliberately left carrying the old `cli.py:973` — it is
the record of what was requested on 2026-07-28, not a claim this item maintains.

## Verification

- `pytest` — 1066 passed.
- `tcw validate` — OK. `tcw capabilities check` — OK.
- **Citation read-back (manual).** Every `file:line` written into a target item
  was re-opened after the last code commit and confirmed to show the claimed
  code: `fs.py` 578, 625, 656, 748, 863, 868, 893, 977, 1229, 1614, 2246, 2288,
  2321; `base.py` 152, 155-158, 331, 931; `cli.py` 216, 982, 1030;
  `hooks.py` 61; `serve/__init__.py` 773.
- **Scope read-back (manual).** Each target item's diff re-read. No goal added or
  removed anywhere. Task 4's item gained content in two previously empty sections,
  which is the stub being filled, not a boundary moving. Task 3's corrections
  state what the code does and explicitly hand the consequent decisions —
  the take-over flag's name, how to break the sentinel cycle — to that item's own
  spec.
- **`--title` was exercised on a real item**, not only in tests: task 5's retitle
  ran through the new flag, which was the point of adding it.

## Notes

- `skills/tcw-work/SKILL.md` needed no change. The router names no `edit` flags at
  all, so `references/commands.md` is the only place in the skill that describes
  them — checked rather than assumed.
- `work/retitle-a-work-item` is still `Missing`; the completion gate flips it.
- The `remote`-tag parking decision and the `typed-taxonomy-relations` discard
  were left untouched, as the spec's non-goals required.
- Four items were folded, not five. The fifth was discarded during the audit; the
  slug keeps "five" for stability.
