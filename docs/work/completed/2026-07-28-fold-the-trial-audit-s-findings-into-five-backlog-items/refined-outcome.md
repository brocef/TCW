# Refined outcome — accepted

## Decision

Accepted on 2026-07-28. Merge route: **local `main`** — the work was done on
`main` throughout, so there is no branch to merge and no PR to open. **No version
change**: the changelog and release-note entries stay in `upcoming.md` until a
later release picks them up.

## Evidence

Every acceptance criterion in `spec.md` is met:

| Criterion | Evidence |
| --- | --- |
| Transactional item names `FsWorkStore.create` and the `accept_inbox` precedent | `2dbb609` |
| States `create` has no production caller; corrects the "sole caller" claim | 17 test modules, priced in the item |
| Concurrency item no longer asserts "only new branching" | `34dc014`, cites `fs.py:578-585` |
| Records the `--force` name collision and the second-commit consequence | `34dc014` |
| Taxonomy item: `origin` encoding raised as a spec decision | `2ddd4b9` |
| Cycles marked already-guarded and struck from scope | `2ddd4b9` |
| Links `taxonomy/federate-shared-vocabulary` | `2ddd4b9` |
| Editor item title and body heading free of "vendored"; slug unchanged | `e61b9ef` |
| The retitle used the CLI flag, not a hand edit | `e61b9ef` |
| `tcw work edit --title` works and `--help` lists it | `80eded4`, `c014199` |
| `work/retitle-a-work-item` declared and flipped | Missing → Supported at closeout |
| README, changelog, release notes, and the `tcw-work` skill updated | `d97e0f2` |

Checks: **1066 tests passed**, `tcw validate` OK, `tcw capabilities check` OK.
Citations were re-read by hand *after* the last code commit — `fs.py` 578, 625,
656, 748, 863, 868, 893, 977, 1229, 1614, 2246, 2288, 2321; `base.py` 152,
155-158, 331, 931; `cli.py` 216, 982, 1030; `hooks.py` 61;
`serve/__init__.py` 773.

## Decisions taken during closeout

- **Untrimmed whitespace on `--title`.** `--title "  x  "` stores the padding.
  `_nonempty` validates against `value.strip()` but returns `value` unchanged, so
  `edit` matches `create_work`, which does not strip either. Confirmed as
  intentional: trimming in one path and not the other is the worse outcome.
- **Local review triage.** One reported blocker (that `_UNSET` reaches
  `state["title"]`) was false — `update_work` guards it at `fs.py:2588`; the
  reviewer had been handed a context file that omitted the guard line. The one
  fair finding, that the omitted-flag path was untested, became the assertion in
  `c014199`, mutation-checked by replacing `_provided(args.title)` with
  `args.title` and confirming the test fails.

## Follow-ups

None filed. The systematic phantom-CLI-verb sweep this item bumped into stays
where it already lives, as
`2026-07-28-scan-every-markdown-file-for-phantom-cli-verbs-excluding-archives`;
this item closed only the one instance it tripped over, by the spec's non-goal.

## Notes

Two process lessons, both already recorded in `outcome.md` and worth repeating
because they are the reusable part:

1. A plan that both edits code and writes citations into other documents must
   re-verify those citations *after* the code task. Task 1 added 12 lines to
   `cli.py` and silently invalidated line numbers tasks 2-4 had already written.
2. Verifying a finding against the code but not against the item it is destined
   for reproduces, in miniature, the failure this item existed to clean up — the
   spec's "bonus finding" was already the target item's first bullet.
