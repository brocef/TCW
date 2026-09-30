# Outcome — See a blocker cycle that runs through an item whose state.yaml cannot be read

## What changed

- `tcw/store/base.py`:
  - `_reaches` never raises and now collects `(label, reason)` for every item
    on the path whose blockers are unknown: a slug more than one folder holds
    (`MultipleMatch`), or an item with no blockers whose store gives an
    `unreadable_reason`.
  - `_refuse_blocker_walks` decides once after every walk: a cycle wins,
    otherwise the unknown items refuse the edit, otherwise it is accepted.
  - `_check_new_blockers` checks every blocker one call adds together; it is
    used by `add_blocker`, both `--blocked-by` and `--blocks` in
    `check_blocker_edits`, `update_work` and `create_work`.
  - The remedy in the message is worded per reason.
  - New hooks: `unreadable_reason(slug)` and `_item_label(store, slug)`.
- `tcw/store/fs.py`: `unreadable_reason` (duplicate slug, or `_state_damage`);
  `_item_label` names another project's item `<project-id>/<slug>`, looking
  through every project in the graph so a sibling is named too.

## Commits

- e5d6da49 tests (failing cases `xfail(strict=True)`)
- a5bc6667 the hooks, the walk and the decision
- 0bbfc115 documentation
- 73853df2 review fixes

## Evidence

- `tests/test_blocker_cycles_through_unreadable_items.py`, 14 tests:
  - local and cross-project damaged items;
  - a cycle winning over a damaged path, in a single walk, across two blockers
    added in one call, and across `--blocks`;
  - `update_work` and `create_work`;
  - a duplicate slug, with its own remedy;
  - `--blocks` refused for a damaged path alone, with no write;
  - five cases that must not be refused.
- Mutation checks, each turning tests red:
  - no damage collected (4 failures);
  - no duplicate-slug collected (1);
  - no refusal (5);
  - deciding per walk (4);
  - deciding per blocker instead of per call (1);
  - no duplicate remedy (1);
  - the `--blocks` half unchecked (1).
- The existing blocker, cycle and edit-refusal tests pass (84 in the targeted
  set); doc-surface tests 1043 passed. Full suite (bare `pytest`, `venv` first on PATH): 5015 passed, 3 skipped at 73853df2 (25 minutes).
- Hands-on, in a scratch two-project graph:
  - a damaged local item is named;
  - a damaged item in the other project is named `pb/<slug>`;
  - `tcw validate` lists the file the message points at;
  - after the file is fixed, the same edit is refused as a real cycle.
- Not run: `tcw serve` end to end. `PATCH` goes through `update_work`, which is
  tested, and the web layer maps its `ValueError` to 422, as checked by hand
  for the previous item.

## What the plan or spec got wrong

- `unreadable_open_items` was not rewritten over `unreadable_reason`. That
  calls `_find` once per item, which would make the listing quadratic.
- `_item_label` could not use `registered_project_id`: it knows only
  ancestors and descendants, so a sibling's item would be unqualified.
- Goal 2 was narrowed. An edit combining `--blocked-by` with `--blocks`
  decides the added blockers first. All of the above is recorded in the spec.
- Risks understated the cost. It is one extra scan of the store's folders,
  plus a parse, per visited item with no blockers.

## Autonomous decisions

- **Spec: refuse, or only warn, when the walk cannot see through an item?**
  - Both advisors (Opus; Sonnet in place of Codex, at its usage limit until
    2026-10-03) said refuse, let a cycle win, collect across walks and decide
    once, and keep interrupted claims silent.
  - They split on duplicate slugs. I counted them as unreadable, on Opus's
    argument that `MultipleMatch` is raised only after five re-scans rule out
    a move in flight.
- **Review, a duplicate slug was told to fix its state.yaml and pointed at
  `tcw validate`, which crashes on duplicates.** Accepted: the remedy is now
  worded per reason. The `validate` crash is filed to the inbox.
- **Review, several blockers added in one call were checked one at a time,
  so a damaged path could hide a cycle.** Accepted and fixed
  (`_check_new_blockers`), rather than narrowing the goal. The one remaining
  narrowing, an add combined with `--blocks`, is written into the spec:
  nothing is written either way.
- **Review, the test of editing the damaged item itself asserted only an
  absence.** Accepted: it now asserts the strict read's message and that
  nothing changed.
- **Review, no test of `--blocks` refused for a damaged path alone.**
  Accepted and added, with a second change in the same edit, so that a
  refusal arriving only at write time would fail it.
- **Review, the guide line mentioned neither `--blocks` nor duplicate slugs.**
  Accepted.
- **Review, re-adding an existing blocker whose path now runs through a
  damaged item is refused.** Not changed. The cycle rule already behaves this
  way, and `update_work` (the web app) skips existing blockers.
- **Review, a bare YAML message when editing a damaged item.** An older
  defect, filed to the inbox.
